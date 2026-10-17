from django import forms

from accounts.forms import StyledFormMixin
from accounts.models import phone_validator, pincode_validator

from .models import Order


class CheckoutForm(StyledFormMixin, forms.Form):
    ship_full_name = forms.CharField(label="Full name", max_length=120)
    ship_phone = forms.CharField(label="Phone", max_length=20, validators=[phone_validator])
    ship_email = forms.EmailField(label="Email", required=False)
    ship_line1 = forms.CharField(label="Address line 1", max_length=200)
    ship_line2 = forms.CharField(label="Address line 2 (optional)", max_length=200, required=False)
    ship_city = forms.CharField(label="City", max_length=80)
    ship_state = forms.CharField(label="State", max_length=80)
    ship_postal_code = forms.CharField(label="PIN code", max_length=6, validators=[pincode_validator])
    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices, widget=forms.RadioSelect, initial=Order.PaymentMethod.COD,
    )
    save_address = forms.BooleanField(required=False, initial=True, label="Save this address to my account")

    def shipping_data(self):
        return {k: v for k, v in self.cleaned_data.items() if k.startswith("ship_")}
