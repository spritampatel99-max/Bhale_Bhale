from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    r"^[0-9+\-\s()]{7,20}$", "Enter a valid phone number (digits, spaces, + - ( ) only)."
)
pincode_validator = RegexValidator(r"^[1-9][0-9]{5}$", "Enter a valid 6-digit PIN code.")


class User(AbstractUser):
    """Custom user created before the first migration (Django best practice).

    `role` is the single source of truth for what a user may do. The save()
    method keeps Django's `is_staff` flag consistent with the role so that the
    built-in /admin/ site and our custom dashboard agree.
    """

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER, db_index=True)
    phone = models.CharField(max_length=20, blank=True, validators=[phone_validator])

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)

    @property
    def is_admin_role(self):
        return self.is_active and self.role == self.Role.ADMIN and self.is_staff

    @property
    def is_customer_role(self):
        return self.role == self.Role.CUSTOMER

    @property
    def display_name(self):
        return self.get_full_name() or self.username


class Address(models.Model):
    """A saved shipping address belonging to exactly one customer."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=40, default="Home")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    line1 = models.CharField("Address line 1", max_length=200)
    line2 = models.CharField("Address line 2", max_length=200, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    postal_code = models.CharField("PIN code", max_length=6, validators=[pincode_validator])
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.label}: {self.line1}, {self.city}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
