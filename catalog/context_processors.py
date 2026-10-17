from django.db.models import Sum

from .models import Category


def storefront(request):
    """Data needed on every storefront page: nav categories and cart badge."""
    cart_count = 0
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from cart.models import CartItem

        cart_count = CartItem.objects.filter(cart__user=user).aggregate(n=Sum("quantity"))["n"] or 0
    return {
        "nav_categories": Category.objects.filter(is_active=True),
        "cart_count": cart_count,
    }
