"""Shared factories for the NovaMart test-suite."""
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from accounts.models import Address, User
from cart.models import Cart, CartItem
from catalog.models import Category, Product
from orders.models import Order, OrderItem

PASSWORD = "Str0ng-Pass!42"
_TMP_MEDIA = tempfile.mkdtemp(prefix="novamart-test-media-")


def make_category(name="Gadgets", **kw):
    return Category.objects.get_or_create(name=name, defaults=kw)[0]


def make_product(name="Widget", price="100.00", stock=10, category=None, **kw):
    category = category or make_category()
    return Product.objects.create(name=name, price=Decimal(price), stock=stock, category=category, **kw)


def make_customer(username="alice", password=PASSWORD, **kw):
    kw.setdefault("email", f"{username}@example.com")
    return User.objects.create_user(username=username, password=password, role=User.Role.CUSTOMER, **kw)


def make_admin(username="boss", password=PASSWORD):
    return User.objects.create_user(username=username, password=password, role=User.Role.ADMIN)


def add_to_cart(user, product, qty=1):
    cart, _ = Cart.objects.get_or_create(user=user)
    return CartItem.objects.create(cart=cart, product=product, quantity=qty)


def make_address(user, **kw):
    data = dict(label="Home", full_name="Alice A", phone="9876543210", line1="1 Test Road", city="Delhi",
                state="Delhi", postal_code="110001", is_default=True)
    data.update(kw)
    return Address.objects.create(user=user, **data)


def make_order(customer, lines, status=Order.Status.DELIVERED, days_ago=0, **kw):
    """lines = [(product, qty, unit_price_or_None)]; builds an order directly."""
    subtotal = sum((Decimal(str(p.price if price is None else price)) * q for p, q, price in lines), Decimal("0"))
    order = Order.objects.create(
        order_number=f"NM-TEST-{Order.objects.count() + 1:05d}", customer=customer, status=status,
        ship_full_name="Test", ship_phone="9876543210", ship_line1="1 Road", ship_city="Delhi",
        ship_state="Delhi", ship_postal_code="110001", subtotal=subtotal, total=subtotal, **kw)
    for p, q, price in lines:
        unit = Decimal(str(p.price if price is None else price))
        OrderItem.objects.create(order=order, product=p, product_name=p.name, sku=p.sku,
                                 category_name=p.category.name, unit_price=unit, quantity=q, line_total=unit * q)
    when = timezone.now() - timedelta(days=days_ago, hours=1)
    Order.objects.filter(pk=order.pk).update(created_at=when)
    order.refresh_from_db()
    return order


def png_upload(name="photo.png", size=(40, 40), color=(200, 30, 30)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def checkout_payload(**overrides):
    data = {
        "ship_full_name": "Alice Anderson", "ship_phone": "9876543210", "ship_email": "alice@example.com",
        "ship_line1": "12 Park Street", "ship_line2": "", "ship_city": "Mumbai", "ship_state": "Maharashtra",
        "ship_postal_code": "400001", "payment_method": "cod", "save_address": "on",
    }
    data.update(overrides)
    return data


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class NovaTestCase(TestCase):
    """Base class: uploads go to a throw-away temp directory."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for child in __import__("pathlib").Path(_TMP_MEDIA).glob("*"):
            shutil.rmtree(child, ignore_errors=True)


def fast_render(shape, palette, size=800):
    """Stand-in for catalog.demo_images.render so seed-command tests stay quick."""
    buf = BytesIO()
    Image.new("RGB", (16, 16), (120, 140, 220)).save(buf, "JPEG")
    return buf.getvalue()
