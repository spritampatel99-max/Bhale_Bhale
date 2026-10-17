from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Address
from cart.models import CartItem
from cart.pricing import cart_totals

from .forms import CheckoutForm
from .models import Order
from .services import CheckoutError, change_order_status, place_order


def _initial_for(user):
    address = user.addresses.filter(is_default=True).first() or user.addresses.first()
    initial = {"ship_full_name": user.get_full_name(), "ship_phone": user.phone, "ship_email": user.email}
    if address:
        initial.update({
            "ship_full_name": address.full_name, "ship_phone": address.phone,
            "ship_line1": address.line1, "ship_line2": address.line2, "ship_city": address.city,
            "ship_state": address.state, "ship_postal_code": address.postal_code,
        })
    return initial


@login_required
def checkout(request):
    items = list(CartItem.objects.filter(cart__user=request.user).select_related("product"))
    if not items:
        messages.info(request, "Your cart is empty. Add something first!")
        return redirect("cart:detail")

    form = CheckoutForm(request.POST or None, initial=_initial_for(request.user))
    if request.method == "POST" and form.is_valid():
        try:
            order = place_order(request.user, form.shipping_data(), form.cleaned_data["payment_method"])
        except CheckoutError as exc:
            messages.error(request, str(exc))
            return redirect("cart:detail")
        if form.cleaned_data["save_address"] and not request.user.addresses.filter(
            line1=order.ship_line1, postal_code=order.ship_postal_code
        ).exists():
            Address.objects.create(
                user=request.user, label="Checkout", full_name=order.ship_full_name, phone=order.ship_phone,
                line1=order.ship_line1, line2=order.ship_line2, city=order.ship_city, state=order.ship_state,
                postal_code=order.ship_postal_code, is_default=not request.user.addresses.exists(),
            )
        return redirect("orders:confirmation", order_number=order.order_number)

    return render(request, "checkout/checkout.html", {
        "form": form, "items": items, "totals": cart_totals(items),
        "saved_addresses": request.user.addresses.all(),
    })


def _own_order(request, order_number):
    # Filtering by customer means another user's order is a plain 404 (no data leak).
    return get_object_or_404(Order.objects.prefetch_related("items"), order_number=order_number, customer=request.user)


@login_required
def confirmation(request, order_number):
    return render(request, "checkout/confirmation.html", {"order": _own_order(request, order_number)})


@login_required
def order_history(request):
    page = Paginator(request.user.orders.prefetch_related("items"), 8).get_page(request.GET.get("page"))
    return render(request, "orders/order_list.html", {"page": page})


@login_required
def order_detail(request, order_number):
    return render(request, "orders/order_detail.html", {"order": _own_order(request, order_number)})


@login_required
@require_POST
def order_cancel(request, order_number):
    order = _own_order(request, order_number)
    if not order.can_customer_cancel:
        messages.error(request, "This order can no longer be cancelled online.")
    else:
        try:
            change_order_status(order.pk, Order.Status.CANCELLED)
            messages.success(request, f"Order {order.order_number} was cancelled.")
        except CheckoutError as exc:
            messages.error(request, str(exc))
    return redirect("orders:detail", order_number=order.order_number)
