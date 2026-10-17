from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Address, User


class StyledFormMixin:
    """Adds the CSS classes used by the design system to every widget."""

    def _style(self):
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, (forms.CheckboxInput, forms.RadioSelect)):
                w.attrs.setdefault("class", "check")
            elif isinstance(w, forms.Select):
                w.attrs.setdefault("class", "input select")
            else:
                w.attrs.setdefault("class", "input")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class LoginForm(StyledFormMixin, AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label="Keep me signed in for 14 days")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autofocus": True, "placeholder": "Username", "autocomplete": "username"}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "Password", "autocomplete": "current-password"}
        )


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CUSTOMER  # never trust a role from the browser
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")


class AddressForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Address
        fields = ("label", "full_name", "phone", "line1", "line2", "city", "state", "postal_code", "is_default")
