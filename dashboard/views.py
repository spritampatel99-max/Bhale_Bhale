import csv
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.permissions import admin_required
from catalog.forms import CategoryForm, ProductForm
from catalog.models import Category, Product, ProductImage
from orders.models import REVENUE_STATUSES, Order, OrderItem
from orders.services import CheckoutError, change_order_status

from . import analytics
from .forms import OrderStatusForm

PAGE_SIZE = 15
MAX_EXTRA_IMAGES = 8


def _page(request, qs, size=PAGE_SIZE):
    return Paginator(qs, size).get_page(request.GET.get("page"))


# ------------------------------------------------------------------ overview
@admin_required
def home(request):
    all_time = analytics.summary()
    today = timezone.localdate()
    week = analytics.sales_series(today - timedelta(days=13), today, "daily")
    pending_value = Order.objects.filter(status=Order.Status.PENDING).aggregate(v=Coalesce(Sum("total"), Decimal("0")))["v"]
    context = {
        "revenue": all_time["revenue"],
        "orders_total": Order.objects.count(),
        "orders_cancelled": Order.objects.filter(status=Order.Status.CANCELLED).count(),
        "orders_pending": Order.objects.filter(status=Order.Status.PENDING).count(),
        "pending_value": pending_value,
        "aov": all_time["aov"],
        "customers": User.objects.filter(role=User.Role.CUSTOMER).count(),
        "products_active": Product.objects.filter(is_active=True).count(),
        "low_stock": analytics.low_stock_products()[:6],
        "low_stock_count": analytics.low_stock_products().count(),
        "recent_orders": Order.objects.select_related("customer")[:8],
        "best_sellers": analytics.top_products(limit=5),
        "activity": {
            "labels": [r["label"] for r in week],
            "revenue": [float(r["revenue"]) for r in week],
            "orders": [r["orders"] for r in week],
            "currency": settings.CURRENCY_SYMBOL,
        },
        "last14_revenue": sum((r["revenue"] for r in week), Decimal("0")),
    }
    return render(request, "dashboard/home.html", context)


# ------------------------------------------------------------------ products
@admin_required
def product_list(request):
    qs = Product.objects.select_related("category")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    category = request.GET.get("category")
    if category and category.isdigit():
        qs = qs.filter(category_id=category)
    state = request.GET.get("state", "")
    if state == "active":
        qs = qs.filter(is_active=True)
    elif state == "inactive":
        qs = qs.filter(is_active=False)
    elif state == "low":
        qs = qs.filter(is_active=True, stock__lte=settings.LOW_STOCK_THRESHOLD)
    return render(request, "dashboard/product_list.html", {
        "page": _page(request, qs.order_by("-updated_at")), "q": q, "state": state,
        "category": category or "", "categories": Category.objects.all(),
    })


@admin_required
def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        existing = product.extra_images.count() if product else 0
        extras = form.cleaned_data.get("extra_images") or []
        if existing + len(extras) > MAX_EXTRA_IMAGES:
            form.add_error("extra_images", f"A product can have at most {MAX_EXTRA_IMAGES} additional photos.")
        else:
            saved = form.save()
            for i, image in enumerate(extras, start=existing):
                ProductImage.objects.create(product=saved, image=image, alt_text=saved.name, position=i)
            messages.success(request, f"Product '{saved.name}' saved.")
            return redirect("dashboard:products")
    return render(request, "dashboard/product_form.html", {"form": form, "product": product})


@admin_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.order_items.exists():
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        messages.warning(request, f"'{product.name}' has order history, so it was deactivated instead of deleted.")
    else:
        name = product.name
        product.delete()
        messages.success(request, f"Product '{name}' deleted.")
    return redirect("dashboard:products")


@admin_required
@require_POST
def product_image_delete(request, pk, image_id):
    image = get_object_or_404(ProductImage, pk=image_id, product_id=pk)
    image.delete()
    messages.info(request, "Photo removed.")
    return redirect("dashboard:product_edit", pk=pk)


# --------------------------------------------------------------- categories
@admin_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products")).order_by("name")
    return render(request, "dashboard/category_list.html", {"categories": categories})


@admin_required
def category_edit(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"Category '{saved.name}' saved.")
        return redirect("dashboard:categories")
    return render(request, "dashboard/category_form.html", {"form": form, "category": category})


@admin_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    count = category.products.count()
    if count:
        messages.error(
            request,
            f"'{category.name}' still has {count} product(s). Move or delete them first, or deactivate the category instead.",
        )
    else:
        category.delete()
        messages.success(request, "Category deleted.")
    return redirect("dashboard:categories")


# ------------------------------------------------------------------- orders
@admin_required
def order_list(request):
    qs = Order.objects.select_related("customer").annotate(item_count=Sum("items__quantity")).order_by("-created_at", "-id")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(order_number__icontains=q) | Q(customer__username__icontains=q))
    status = request.GET.get("status", "")
    if status in Order.Status.values:
        qs = qs.filter(status=status)
    start, end = parse_date(request.GET.get("from") or ""), parse_date(request.GET.get("to") or "")
    if start:
        qs = qs.filter(created_at__gte=analytics._bounds(start, start)[0])
    if end:
        qs = qs.filter(created_at__lt=analytics._bounds(end, end)[1])
    return render(request, "dashboard/order_list.html", {
        "page": _page(request, qs), "q": q, "status": status,
        "date_from": request.GET.get("from", ""), "date_to": request.GET.get("to", ""),
        "statuses": Order.Status.choices,
    })


@admin_required
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.select_related("customer").prefetch_related("items"), order_number=order_number)
    form = OrderStatusForm(request.POST or None, initial={"status": order.status})
    if request.method == "POST" and form.is_valid():
        try:
            updated = change_order_status(order.pk, form.cleaned_data["status"])
            messages.success(request, f"Order {updated.order_number} is now {updated.get_status_display()}.")
        except CheckoutError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:order_detail", order_number=order.order_number)
    return render(request, "dashboard/order_detail.html", {"order": order, "form": form})


# ---------------------------------------------------------------- customers
@admin_required
def customer_list(request):
    qs = User.objects.filter(role=User.Role.CUSTOMER).annotate(
        order_count=Count("orders", distinct=True),
        spent=Coalesce(Sum("orders__total", filter=Q(orders__status__in=REVENUE_STATUSES)), Decimal("0")),
    )
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    state = request.GET.get("state", "")
    if state == "active":
        qs = qs.filter(is_active=True)
    elif state == "inactive":
        qs = qs.filter(is_active=False)
    return render(request, "dashboard/customer_list.html", {"page": _page(request, qs.order_by("-date_joined")), "q": q, "state": state})


@admin_required
def customer_detail(request, pk):
    customer = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER)
    orders = customer.orders.prefetch_related("items")
    spent = orders.filter(status__in=REVENUE_STATUSES).aggregate(v=Coalesce(Sum("total"), Decimal("0")))["v"]
    return render(request, "dashboard/customer_detail.html", {
        "customer": customer, "orders": orders, "spent": spent, "addresses": customer.addresses.all(),
    })


@admin_required
@require_POST
def customer_toggle(request, pk):
    customer = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER)
    customer.is_active = not customer.is_active
    customer.save(update_fields=["is_active"])
    messages.success(request, f"{customer.username} is now {'active' if customer.is_active else 'deactivated'}.")
    return redirect("dashboard:customer_detail", pk=pk)


# ---------------------------------------------------------------- analytics
@admin_required
def analytics_page(request):
    start, end = analytics.parse_range(request.GET)
    summary = analytics.summary(start, end)
    series = {p: analytics.sales_series(start, end, p) for p in ("daily", "weekly", "monthly")}
    products = analytics.top_products(start, end)
    categories = analytics.category_sales(start, end)
    chart = {
        "series": {
            p: {
                "labels": [r["label"] for r in rows],
                "revenue": [float(r["revenue"]) for r in rows],
                "orders": [r["orders"] for r in rows],
            } for p, rows in series.items()
        },
        "products": {"labels": [p["product_name"] for p in products], "units": [p["units"] for p in products]},
        "categories": {"labels": [c["category_name"] for c in categories], "revenue": [float(c["revenue"]) for c in categories]},
        "statuses": {"labels": [s[1] for s in analytics.status_breakdown(start, end)],
                     "counts": [s[2] for s in analytics.status_breakdown(start, end)]},
        "currency": settings.CURRENCY_SYMBOL,
    }
    return render(request, "dashboard/analytics.html", {
        "start": start, "end": end, "summary": summary, "chart": chart, "products": products,
        "categories": categories, "low_stock": analytics.low_stock_products()[:10],
        "low_stock_count": analytics.low_stock_products().count(),
        "has_data": summary["orders"] > 0,
        "status_rows": analytics.status_breakdown(start, end),
        "top_category": categories[0] if categories else None,
    })


def _sales_lines(request):
    start, end = analytics.parse_range(request.GET, default_days=30)
    lines = analytics.revenue_items(start, end).select_related("order", "order__customer").order_by("-order__created_at", "-id")
    return start, end, lines


@admin_required
def sales_page(request):
    start, end, lines = _sales_lines(request)
    totals = analytics.summary(start, end)
    return render(request, "dashboard/sales.html", {
        "start": start, "end": end, "page": _page(request, lines, 20), "totals": totals,
        "daily": [r for r in reversed(analytics.sales_series(start, end, "daily")) if r["orders"]][:14],
    })


def _csv_safe(value):
    """Neutralise spreadsheet formula injection in exported cells."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@admin_required
def sales_export(request):
    start, end, lines = _sales_lines(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="novamart-sales-{start}-to-{end}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Order", "Date", "Status", "Customer", "Product", "SKU", "Category", "Qty", "Unit price", "Line total"])
    for item in lines.iterator():
        o = item.order
        writer.writerow([
            o.order_number, timezone.localtime(o.created_at).strftime("%Y-%m-%d %H:%M"), o.get_status_display(),
            _csv_safe(o.customer.username), _csv_safe(item.product_name), item.sku, _csv_safe(item.category_name),
            item.quantity, item.unit_price, item.line_total,
        ])
    return response
