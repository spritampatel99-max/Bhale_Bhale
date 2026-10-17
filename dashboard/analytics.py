"""Database-backed sales analytics.

Revenue definition (used everywhere): the `total` of orders whose status is
Confirmed, Processing, Shipped or Delivered (see orders.models.REVENUE_STATUSES).
Pending and Cancelled orders are NOT revenue. Category/product sales use the
order-item snapshots of those same orders, so nothing is counted twice.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Avg, Count, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from django.utils.dateparse import parse_date

from catalog.models import Product
from orders.models import REVENUE_STATUSES, Order, OrderItem

ZERO = Decimal("0.00")
DEFAULT_DAYS = 90


def parse_range(params, default_days=DEFAULT_DAYS):
    today = timezone.localdate()
    end = parse_date(params.get("to") or "") or today
    start = parse_date(params.get("from") or "") or (end - timedelta(days=default_days - 1))
    if start > end:
        start, end = end, start
    if (end - start).days > 730:
        start = end - timedelta(days=730)
    return start, end


def _bounds(start, end):
    tz = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(start, time.min), tz),
        timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz),
    )


def revenue_orders(start=None, end=None):
    qs = Order.objects.filter(status__in=REVENUE_STATUSES)
    if start and end:
        lo, hi = _bounds(start, end)
        qs = qs.filter(created_at__gte=lo, created_at__lt=hi)
    return qs


def revenue_items(start=None, end=None):
    qs = OrderItem.objects.filter(order__status__in=REVENUE_STATUSES)
    if start and end:
        lo, hi = _bounds(start, end)
        qs = qs.filter(order__created_at__gte=lo, order__created_at__lt=hi)
    return qs


def summary(start=None, end=None):
    agg = revenue_orders(start, end).aggregate(
        revenue=Coalesce(Sum("total"), ZERO), orders=Count("id"), aov=Avg("total"),
    )
    return {
        "revenue": agg["revenue"],
        "orders": agg["orders"],
        "aov": (agg["aov"] or ZERO).quantize(Decimal("0.01")),
    }


def sales_series(start, end, period="daily"):
    """Return [{label, key, revenue, orders}] for daily/weekly/monthly buckets."""
    trunc = {"daily": TruncDate, "weekly": TruncWeek, "monthly": TruncMonth}[period]("created_at")
    rows = (
        revenue_orders(start, end).annotate(bucket=trunc).values("bucket")
        .annotate(revenue=Sum("total"), orders=Count("id")).order_by("bucket")
    )
    data = {}
    for r in rows:
        key = r["bucket"].date() if isinstance(r["bucket"], datetime) else r["bucket"]
        data[key] = (r["revenue"], r["orders"])

    series = []
    if period == "daily":
        day = start
        while day <= end:
            rev, n = data.get(day, (ZERO, 0))
            series.append({"key": day.isoformat(), "label": day.strftime("%d %b"), "revenue": rev, "orders": n})
            day += timedelta(days=1)
    else:
        fmt = "%d %b" if period == "weekly" else "%b %Y"
        for key in sorted(data):
            rev, n = data[key]
            label = ("Wk of " if period == "weekly" else "") + key.strftime(fmt)
            series.append({"key": key.isoformat(), "label": label, "revenue": rev, "orders": n})
    return series


def top_products(start=None, end=None, limit=8):
    return list(
        revenue_items(start, end).values("product_name", "sku")
        .annotate(units=Sum("quantity"), revenue=Sum("line_total")).order_by("-units", "-revenue")[:limit]
    )


def category_sales(start=None, end=None):
    return list(
        revenue_items(start, end).exclude(category_name="").values("category_name")
        .annotate(units=Sum("quantity"), revenue=Sum("line_total")).order_by("-revenue")
    )


def low_stock_products():
    return Product.objects.filter(is_active=True, stock__lte=settings.LOW_STOCK_THRESHOLD).select_related("category").order_by("stock", "name")


def status_breakdown(start=None, end=None):
    qs = Order.objects.all()
    if start and end:
        lo, hi = _bounds(start, end)
        qs = qs.filter(created_at__gte=lo, created_at__lt=hi)
    counts = {r["status"]: r["n"] for r in qs.values("status").annotate(n=Count("id"))}
    return [(value, label, counts.get(value, 0)) for value, label in Order.Status.choices]
