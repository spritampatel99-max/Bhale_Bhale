from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from orders.models import REVENUE_STATUSES

from .models import Category, Product

SORTS = {
    "newest": ("Newest", ["-created_at", "-id"]),
    "popular": ("Most popular", ["-sold", "-id"]),
    "price_asc": ("Price: low to high", ["price", "id"]),
    "price_desc": ("Price: high to low", ["-price", "-id"]),
}
PAGE_SIZE = 12


def visible_products():
    """Active products in active categories, annotated with units sold."""
    return (
        Product.objects.filter(is_active=True, category__is_active=True)
        .select_related("category")
        .annotate(sold=Coalesce(Sum(
            "order_items__quantity",
            filter=Q(order_items__order__status__in=REVENUE_STATUSES),
        ), 0))
    )


def _decimal_or_none(raw):
    try:
        value = Decimal((raw or "").strip())
    except (InvalidOperation, AttributeError):
        return None
    return value if value >= 0 else None


def home(request):
    products = visible_products()
    recent_cutoff = timezone.now() - timedelta(days=30)
    trending = (
        products.annotate(recent=Coalesce(Sum(
            "order_items__quantity",
            filter=Q(order_items__order__status__in=REVENUE_STATUSES,
                     order_items__order__created_at__gte=recent_cutoff),
        ), 0)).order_by("-recent", "-id")[:8]
    )
    hero_products = list(products.filter(is_featured=True, stock__gt=0).order_by("id")[:3])
    context = {
        "hero_products": hero_products,
        "categories": Category.objects.filter(is_active=True),
        "trending": trending,
        "best_sellers": products.order_by("-sold", "-id")[:4],
        "new_arrivals": products.order_by("-created_at", "-id")[:4],
        "offers": products.filter(original_price__gt=F("price"), stock__gt=0).order_by("-id")[:4],
        "featured": products.filter(is_featured=True)[:4],
    }
    return render(request, "store/home.html", context)


def product_list(request, category_slug=None):
    category = None
    qs = visible_products()
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        qs = qs.filter(category=category)
    elif request.GET.get("category"):
        qs = qs.filter(category__slug=request.GET["category"])

    q = (request.GET.get("q") or "").strip()[:100]
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q))

    min_price = _decimal_or_none(request.GET.get("min_price"))
    max_price = _decimal_or_none(request.GET.get("max_price"))
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    if request.GET.get("in_stock") == "1":
        qs = qs.filter(stock__gt=0)

    sort = request.GET.get("sort", "newest")
    if sort not in SORTS:
        sort = "newest"
    qs = qs.order_by(*SORTS[sort][1])

    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    selected_slug = category.slug if category else request.GET.get("category", "")
    return render(request, "store/product_list.html", {
        "page": page,
        "category": category,
        "categories": Category.objects.filter(is_active=True),
        "selected_category": selected_slug,
        "q": q,
        "min_price": request.GET.get("min_price", ""),
        "max_price": request.GET.get("max_price", ""),
        "in_stock": request.GET.get("in_stock") == "1",
        "sort": sort,
        "sorts": [(key, label) for key, (label, _) in SORTS.items()],
        "total": page.paginator.count,
    })


def product_detail(request, slug):
    product = get_object_or_404(visible_products(), slug=slug)
    gallery = [{"url": product.image_url, "alt": product.name}]
    gallery += [{"url": i.image_url, "alt": i.alt_text or product.name} for i in product.extra_images.all()]
    related = visible_products().filter(category=product.category).exclude(pk=product.pk).order_by("-sold", "-id")[:4]
    max_qty = min(product.stock, 20)
    return render(request, "store/product_detail.html", {
        "product": product,
        "gallery": gallery,
        "related": related,
        "qty_options": range(1, max_qty + 1),
        "max_qty": max_qty,
    })


def category_list(request):
    return render(request, "store/category_list.html", {"categories": Category.objects.filter(is_active=True)})
