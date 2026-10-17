from django import template

from catalog.utils import format_inr

register = template.Library()


@register.filter
def inr(value):
    """{{ product.price|inr }} -> ₹1,299.00"""
    return format_inr(value) if value not in (None, "") else ""


@register.filter
def inr0(value):
    """Whole-rupee format for compact displays."""
    return format_inr(value, decimals=0) if value not in (None, "") else ""


@register.filter
def times(value, arg):
    try:
        return value * arg
    except TypeError:
        return ""


@register.simple_tag(takes_context=True)
def qs_replace(context, **kwargs):
    """Rebuild the current query string, replacing/removing the given keys."""
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"


@register.simple_tag
def status_class(status):
    return {
        "pending": "warn", "confirmed": "info", "processing": "info",
        "shipped": "violet", "delivered": "ok", "cancelled": "bad",
        "paid": "ok", "refunded": "bad", "failed": "bad",
    }.get(status, "muted")
