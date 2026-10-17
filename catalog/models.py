from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.conf import settings

from .validators import (
    category_image_path,
    product_image_path,
    validate_image_extension,
    validate_image_size,
)

IMAGE_VALIDATORS = [validate_image_extension, validate_image_size]
PLACEHOLDER = "images/placeholders/product.svg"


def unique_slug(model, value, instance_pk=None, max_length=170):
    base = slugify(value)[: max_length - 8] or "item"
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=instance_pk).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def safe_image_url(field_file, fallback=PLACEHOLDER):
    """Return the uploaded image URL, or a static fallback if missing/unreadable."""
    try:
        if field_file and field_file.name and field_file.storage.exists(field_file.name):
            return field_file.url
    except Exception:  # noqa: BLE001 - a broken file must never crash a page
        pass
    return static(fallback)


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=category_image_path, blank=True, validators=IMAGE_VALIDATORS)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Category, self.name, self.pk, 100)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category", args=[self.slug])

    @property
    def image_url(self):
        return safe_image_url(self.image, "images/placeholders/category.svg")


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    sku = models.CharField("SKU", max_length=32, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    original_price = models.DecimalField(
        "list price (MRP)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Optional. If higher than the price, a discount badge is shown.",
    )
    image = models.ImageField(upload_to=product_image_path, blank=True, validators=IMAGE_VALIDATORS)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    # Demonstration-only rating data (clearly labelled as such in the UI).
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("5"))],
    )
    rating_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["price"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name="product_price_positive"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.original_price is not None and self.price is not None and self.original_price < self.price:
            raise ValidationError({"original_price": "List price cannot be lower than the selling price."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Product, self.name, self.pk, 180)
        if not self.sku:
            while True:
                candidate = f"NM-{get_random_string(6, 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789')}"
                if not Product.objects.filter(sku=candidate).exists():
                    self.sku = candidate
                    break
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:detail", args=[self.slug])

    @property
    def image_url(self):
        return safe_image_url(self.image)

    @property
    def has_discount(self):
        return bool(self.original_price and self.original_price > self.price)

    @property
    def discount_percent(self):
        if not self.has_discount:
            return 0
        return int(((self.original_price - self.price) / self.original_price) * 100)

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock <= settings.LOW_STOCK_THRESHOLD

    @property
    def rating_percent(self):
        return int((self.rating or 0) / 5 * 100)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="extra_images")
    image = models.ImageField(upload_to=product_image_path, validators=IMAGE_VALIDATORS)
    alt_text = models.CharField(max_length=160, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return f"Image for {self.product}"

    @property
    def image_url(self):
        return safe_image_url(self.image)
