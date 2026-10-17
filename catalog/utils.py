from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

TWO_PLACES = Decimal("0.01")


def money(value):
    """Quantize to 2 decimal places using Decimal (never floats)."""
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def format_inr(value, decimals=2):
    """Format a Decimal using Indian digit grouping: 1,23,456.00"""
    if value is None:
        return ""
    value = money(value)
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    out = f"{sign}{settings.CURRENCY_SYMBOL}{whole}"
    return f"{out}.{frac}" if decimals else out
