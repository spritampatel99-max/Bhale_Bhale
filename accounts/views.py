from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AddressForm, LoginForm, ProfileForm, RegisterForm
from .models import Address


def role_home(user):
    """Where a user lands after login."""
    return reverse("dashboard:home") if user.is_admin_role else reverse("catalog:home")


class RoleLoginView(LoginView):
    """One login page for customers and administrators."""

    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return role_home(self.request.user)

    def get_success_url(self):
        user = self.request.user
        requested = self.get_redirect_url()  # already validated as a safe URL
        if requested and requested.startswith("/dashboard/") and not user.is_admin_role:
            requested = ""
        return requested or role_home(user)

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)  # expires when the browser closes
        else:
            self.request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        messages.success(self.request, f"Welcome back, {form.get_user().display_name}!")
        return response


def register(request):
    if request.user.is_authenticated:
        return redirect(role_home(request.user))
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your NovaMart account is ready. Happy shopping!")
        return redirect("catalog:home")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def account(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:account")
    recent_orders = request.user.orders.order_by("-created_at")[:3]
    return render(request, "accounts/account.html", {
        "form": form,
        "recent_orders": recent_orders,
        "address_count": request.user.addresses.count(),
    })


@login_required
def address_list(request):
    return render(request, "accounts/addresses.html", {"addresses": request.user.addresses.all()})


@login_required
def address_edit(request, pk=None):
    # Ownership is enforced by filtering on request.user.
    instance = get_object_or_404(Address, pk=pk, user=request.user) if pk else None
    form = AddressForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        if not request.user.addresses.exclude(pk=address.pk).exists():
            address.is_default = True
        address.save()
        messages.success(request, "Address saved.")
        return redirect("accounts:addresses")
    return render(request, "accounts/address_form.html", {"form": form, "editing": bool(pk)})


@login_required
@require_POST
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    address.delete()
    messages.info(request, "Address removed.")
    return redirect("accounts:addresses")
