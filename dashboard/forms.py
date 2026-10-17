from django import forms

from accounts.forms import StyledFormMixin
from orders.models import Order


class OrderStatusForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(choices=Order.Status.choices)
