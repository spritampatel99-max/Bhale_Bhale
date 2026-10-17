from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog.models import Product
from catalog.utils import format_inr

from .models import Cart, CartItem
from .pricing import cart_totals


def _wants_json(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")


def _items(user):
    return list(
        CartItem.objects.filter(cart__user=user).select_related("product", "product__category")
    )


def _payload(user, ok=True, message="", item=None):
    items = _items(user)
    totals = cart_totals(items)
    data = {
        "ok": ok,
        "message": message,
        "cart_count": totals["count"],
        "subtotal": format_inr(totals["subtotal"]),
        "savings": format_inr(totals["savings"]),
        "delivery": format_inr(totals["delivery"]) if totals["delivery"] else "Free",
        "total": format_inr(totals["total"]),
        "has_savings": totals["savings"] > 0,
        "free_delivery_gap": format_inr(totals["free_delivery_gap"]),
        "empty": not items,
    }
    if item is not None:
        data["item"] = {"id": item.pk, "quantity": item.quantity, "line_total": format_inr(item.line_total)}
    return data


def _respond(request, user, ok, message, item=None, status=200, fallback="cart:detail"):
    if _wants_json(request):
        return JsonResponse(_payload(user, ok, message, item), status=status if not ok else 200)
    (messages.success if ok else messages.error)(request, message)
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return redirect(target)
    return redirect(fallback)


def _parse_qty(raw, default=1):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default, False
    return value, value >= 1


@login_required
def cart_detail(request):
    items = _items(request.user)
    return render(request, "cart/cart.html", {"items": items, "totals": cart_totals(items)})


@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(
        Product, pk=product_id, is_active=True, category__is_active=True
    )
    qty, valid = _parse_qty(request.POST.get("quantity", 1))
    if not valid:
        return _respond(request, request.user, False, "Quantity must be a positive whole number.", status=400, fallback="catalog:list")
    with transaction.atomic():
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item = CartItem.objects.select_for_update().filter(cart=cart, product=product).first()
        new_qty = (item.quantity if item else 0) + qty
        limit = min(product.stock, settings.MAX_CART_QUANTITY_PER_ITEM)
        if product.stock < 1:
            return _respond(request, request.user, False, f"Sorry, {product.name} is out of stock.", status=400, fallback="catalog:list")
        if new_qty > limit:
            return _respond(request, request.user, False, f"Only {limit} unit(s) of {product.name} can be added.", status=400, fallback="cart:detail")
        if item:
            item.quantity = new_qty
            item.save(update_fields=["quantity"])
        else:
            item = CartItem.objects.create(cart=cart, product=product, quantity=new_qty)
    return _respond(request, request.user, True, f"Added {product.name} to your cart.", item=item, fallback="cart:detail")


@login_required
@require_POST
def update_item(request, item_id):
    # Ownership check: the item must belong to the current user's cart.
    item = get_object_or_404(CartItem.objects.select_related("product"), pk=item_id, cart__user=request.user)
    action = request.POST.get("action")
    if action == "inc":
        new_qty = item.quantity + 1
    elif action == "dec":
        new_qty = item.quantity - 1
    else:
        try:
            new_qty = int(request.POST.get("quantity", ""))
        except (TypeError, ValueError):
            return _respond(request, request.user, False, "Quantity must be a whole number.", status=400)
        if new_qty < 0:
            return _respond(request, request.user, False, "Quantity cannot be negative.", status=400)
    if new_qty < 1:
        item.delete()
        return _respond(request, request.user, True, "Item removed from your cart.")
    limit = min(item.product.stock, settings.MAX_CART_QUANTITY_PER_ITEM)
    if new_qty > limit:
        return _respond(request, request.user, False, f"Only {limit} unit(s) available for {item.product.name}.", item=item, status=400)
    item.quantity = new_qty
    item.save(update_fields=["quantity"])
    return _respond(request, request.user, True, "Cart updated.", item=item)


@login_required
@require_POST
def remove_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    return _respond(request, request.user, True, "Item removed from your cart.")
