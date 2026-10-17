from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from accounts.models import phone_validator, pincode_validator


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on Delivery"
        SIMULATED = "simulated", "Simulated online payment (demo)"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"

    order_number = models.CharField(max_length=24, unique=True, editable=False)
    # PROTECT: customers with orders cannot be deleted by accident (deactivate instead).
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    payment_method = models.CharField(max_length=12, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    # Shipping snapshot: copied at checkout so later profile edits never rewrite history.
    ship_full_name = models.CharField(max_length=120)
    ship_phone = models.CharField(max_length=20, validators=[phone_validator])
    ship_email = models.EmailField(blank=True)
    ship_line1 = models.CharField(max_length=200)
    ship_line2 = models.CharField(max_length=200, blank=True)
    ship_city = models.CharField(max_length=80)
    ship_state = models.CharField(max_length=80)
    ship_postal_code = models.CharField(max_length=6, validators=[pincode_validator])

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Informational: savings versus list price, already reflected in `subtotal`.
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    stock_restored = models.BooleanField(default=False, editable=False,
                                         help_text="True while the order's stock has been returned to inventory.")
    is_demo = models.BooleanField(default=False, help_text="Seeded demonstration order.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "-created_at"]), models.Index(fields=["created_at"])]

    def __str__(self):
        return self.order_number

    def get_absolute_url(self):
        return reverse("orders:detail", args=[self.order_number])

    @property
    def shipping_lines(self):
        parts = [self.ship_line1, self.ship_line2, f"{self.ship_city}, {self.ship_state} {self.ship_postal_code}"]
        return [p for p in parts if p]

    @property
    def can_customer_cancel(self):
        return self.status in {self.Status.PENDING, self.Status.CONFIRMED}


# Statuses that count as recognised revenue. Pending (e.g. unconfirmed COD) and
# cancelled orders are excluded so revenue is never double counted or overstated.
REVENUE_STATUSES = [
    Order.Status.CONFIRMED,
    Order.Status.PROCESSING,
    Order.Status.SHIPPED,
    Order.Status.DELIVERED,
]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    # Snapshots keep historical orders correct even if the product changes or is deleted.
    product_name = models.CharField(max_length=160)
    sku = models.CharField(max_length=32, blank=True)
    category_name = models.CharField(max_length=80, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gte=1), name="orderitem_quantity_gte_1")]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
