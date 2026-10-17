"""Order business logic. Everything that touches money or stock lives here and
runs inside database transactions so a failure never leaves partial data."""
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import get_random_string

from cart.models import CartItem
from cart.pricing import calculate_totals
from catalog.models import Product

from .models import Order, OrderItem


class CheckoutError(Exception):
    """A user-presentable problem (empty cart, out of stock, bad status...)."""


def generate_order_number():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        number = f"NM-{timezone.localdate():%y%m%d}-{get_random_string(5, alphabet)}"
        if not Order.objects.filter(order_number=number).exists():
            return number


@transaction.atomic
def place_order(user, shipping, payment_method):
    """Create an order from the user's cart. Raises CheckoutError on any problem."""
    if payment_method not in Order.PaymentMethod.values:
        raise CheckoutError("Please choose a valid payment method.")

    cart_items = list(CartItem.objects.filter(cart__user=user).order_by("product_id"))
    if not cart_items:
        raise CheckoutError("Your cart is empty.")

    # Lock the product rows (no-op on SQLite, row locks on PostgreSQL/MySQL) and
    # re-read the CURRENT price and stock; the cart is never trusted for either.
    products = {
        p.pk: p
        for p in Product.objects.select_for_update().select_related("category")
        .filter(pk__in=[i.product_id for i in cart_items])
    }
    lines = []
    for item in cart_items:
        product = products.get(item.product_id)
        if product is None or not product.is_active or not product.category.is_active:
            raise CheckoutError("A product in your cart is no longer available. Please review your cart.")
        if item.quantity < 1:
            raise CheckoutError("Invalid quantity in cart.")
        if item.quantity > product.stock:
            raise CheckoutError(f"Only {product.stock} unit(s) of '{product.name}' are in stock.")
        lines.append((product, item.quantity))

    totals = calculate_totals((p.price, p.original_price, q) for p, q in lines)
    simulated = payment_method == Order.PaymentMethod.SIMULATED
    order = Order.objects.create(
        order_number=generate_order_number(),
        customer=user,
        status=Order.Status.CONFIRMED if simulated else Order.Status.PENDING,
        payment_method=payment_method,
        payment_status=Order.PaymentStatus.PAID if simulated else Order.PaymentStatus.PENDING,
        subtotal=totals["subtotal"],
        delivery_charge=totals["delivery"],
        discount=totals["savings"],
        total=totals["total"],
        **shipping,
    )

    order_items = []
    for product, qty in lines:
        # Guarded atomic decrement: also protects against concurrent checkouts.
        updated = Product.objects.filter(pk=product.pk, stock__gte=qty).update(stock=F("stock") - qty)
        if updated != 1:
            raise CheckoutError(f"'{product.name}' just sold out. Please update your cart.")
        order_items.append(OrderItem(
            order=order, product=product, product_name=product.name, sku=product.sku,
            category_name=product.category.name, unit_price=product.price, quantity=qty,
            line_total=product.price * qty,
        ))
    OrderItem.objects.bulk_create(order_items)
    CartItem.objects.filter(cart__user=user).delete()
    return order


@transaction.atomic
def change_order_status(order_id, new_status):
    """Change an order's status and keep inventory + payment state consistent.

    Rules (documented in README):
      * -> Cancelled: units return to stock exactly once; paid orders become Refunded.
      * Cancelled -> anything else: units are taken from stock again; fails if
        there is not enough stock. Refunded orders return to Paid.
      * -> Delivered on a Cash-on-Delivery order marks payment as Paid.
    """
    if new_status not in Order.Status.values:
        raise CheckoutError("Unknown order status.")
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == new_status:
        return order

    items = list(order.items.select_related("product"))
    if new_status == Order.Status.CANCELLED:
        if not order.stock_restored:
            for item in items:
                if item.product_id:
                    Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
            order.stock_restored = True
        if order.payment_status == Order.PaymentStatus.PAID:
            order.payment_status = Order.PaymentStatus.REFUNDED
    elif order.status == Order.Status.CANCELLED:
        if order.stock_restored:
            for item in items:
                if item.product_id:
                    ok = Product.objects.filter(pk=item.product_id, stock__gte=item.quantity).update(
                        stock=F("stock") - item.quantity)
                    if not ok:
                        raise CheckoutError(f"Cannot reopen: not enough stock for '{item.product_name}'.")
            order.stock_restored = False
        if order.payment_status == Order.PaymentStatus.REFUNDED:
            order.payment_status = Order.PaymentStatus.PAID

    if new_status == Order.Status.DELIVERED and order.payment_status == Order.PaymentStatus.PENDING:
        order.payment_status = Order.PaymentStatus.PAID

    order.status = new_status
    order.save()
    return order
