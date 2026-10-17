"""Single source of truth for cart/order totals. Always computed on the server
from database prices -- never from anything the browser submits."""
from decimal import Decimal

from django.conf import settings

from catalog.utils import money


def calculate_totals(lines):
    """`lines` is an iterable of (unit_price, original_price_or_None, quantity)."""
    subtotal = Decimal("0")
    savings = Decimal("0")
    count = 0
    for unit_price, original_price, quantity in lines:
        subtotal += unit_price * quantity
        if original_price and original_price > unit_price:
            savings += (original_price - unit_price) * quantity
        count += quantity
    delivery = Decimal("0")
    if count and subtotal < settings.FREE_DELIVERY_THRESHOLD:
        delivery = settings.DELIVERY_FEE
    subtotal, savings, delivery = money(subtotal), money(savings), money(delivery)
    return {
        "count": count,
        "subtotal": subtotal,
        "savings": savings,
        "delivery": delivery,
        "total": money(subtotal + delivery),
        "free_delivery_gap": max(Decimal("0"), money(settings.FREE_DELIVERY_THRESHOLD - subtotal)) if count else Decimal("0"),
    }


def cart_totals(items):
    return calculate_totals((i.product.price, i.product.original_price, i.quantity) for i in items)
