"""Populate the local prototype with demonstration data.

    python manage.py seed_demo_data --with-demo-users

Safe to run repeatedly: nothing is duplicated. Demo accounts (which use public,
weak passwords) are only created when settings.ALLOW_DEMO_ACCOUNTS is True,
which defaults to DJANGO_DEBUG.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.demo_users import DEMO_ADMIN, DEMO_CUSTOMERS
from accounts.models import Address, User
from cart.pricing import calculate_totals
from catalog import demo_images
from catalog.models import Category, Product
from orders.models import Order, OrderItem
from orders.services import generate_order_number

PALETTES = {
    "blue":   ("#E8EEF9", "#C9D6F0", "#2F6BFF", "#FFB81C", "#0B1B33", "#FFFFFF"),
    "coral":  ("#FDEDEA", "#F8CFC8", "#E5484D", "#0B1B33", "#3B1D2A", "#FFFFFF"),
    "mint":   ("#E6F6EF", "#C4E8D8", "#14935F", "#FFB81C", "#0F3B2E", "#FFFFFF"),
    "sun":    ("#FFF6DD", "#FFE6A3", "#FFB81C", "#0B1B33", "#0B1B33", "#FFFFFF"),
    "violet": ("#F0EBFB", "#D9CEF4", "#6D4AE0", "#FFB81C", "#231544", "#FFFFFF"),
    "slate":  ("#EEF0F4", "#D5DAE3", "#3A4A63", "#FF8A3D", "#0B1B33", "#FFFFFF"),
    "teal":   ("#E3F5F6", "#BCE6EA", "#0E8A9A", "#FFB81C", "#0A3640", "#FFFFFF"),
    "rose":   ("#FCEBF1", "#F6C9DA", "#D6336C", "#FFE066", "#4A1230", "#FFFFFF"),
    "sand":   ("#F7F1E6", "#EADBC0", "#B07A3E", "#0B1B33", "#3A2A14", "#FFFFFF"),
}

CATEGORIES = [
    ("Electronics", "Headphones, wearables, speakers and everyday tech.", "headphones", "blue"),
    ("Fashion", "Wardrobe staples, footwear and accessories.", "tshirt", "coral"),
    ("Home & Living", "Lighting, decor and small comforts for your space.", "lamp", "sun"),
    ("Beauty & Personal Care", "Skin care, colour and daily rituals.", "jar", "rose"),
    ("Sports & Fitness", "Gear for training, yoga and play.", "dumbbell", "mint"),
    ("Books & Stationery", "Stories, notebooks and writing tools.", "book", "violet"),
]

# name, category, price, original price, stock, shape, palette, featured, rating, ratings, description
PRODUCTS = [
    ("Aura Wireless Headphones", "Electronics", 3499, 4999, 40, "headphones", "blue", True, 4.5, 218, "Over-ear Bluetooth headphones with soft ear cushions, deep bass and a foldable design for daily commutes."),
    ("Pulse Smartwatch", "Electronics", 4999, 6999, 25, "watch", "slate", True, 4.3, 164, "Fitness-ready smartwatch with a bright round display, step counter, sleep tracking and a comfortable silicone strap."),
    ("Orbit Bluetooth Speaker", "Electronics", 2299, None, 3, "speaker", "teal", False, 4.4, 97, "Compact speaker with a full-range driver and tweeter. Pairs quickly and fits easily on a desk or shelf."),
    ("Lumen 14 Laptop", "Electronics", 54999, 62999, 12, "laptop", "slate", True, 4.6, 73, "Slim 14-inch laptop for study and work, with a crisp display, fast storage and an all-day battery."),
    ("Snapshot Mirrorless Camera", "Electronics", 38999, None, 8, "camera", "sun", False, 4.7, 41, "Entry-level mirrorless camera with an interchangeable lens, great for travel and portraits."),
    ("Nova S Smartphone", "Electronics", 17999, 19999, 30, "phone", "violet", False, 4.2, 305, "Everyday smartphone with a vivid display, dual cameras and a battery that lasts the full day."),
    ("Everyday Cotton Tee", "Fashion", 599, 899, 120, "tshirt", "blue", True, 4.1, 412, "Soft, breathable 100% cotton crew-neck tee with a relaxed fit. Easy to layer in any season."),
    ("Stride Running Sneakers", "Fashion", 2499, 3499, 60, "shoe", "coral", True, 4.4, 189, "Lightweight sneakers with a cushioned sole and a breathable upper, built for daily miles."),
    ("Metro Tote Bag", "Fashion", 1799, None, 22, "bag", "sand", False, 4.3, 88, "Structured everyday tote with a roomy interior, secure clasp and sturdy top handle."),
    ("Sunset Round Sunglasses", "Fashion", 999, 1499, 4, "glasses", "sun", False, 4.0, 126, "Round-frame sunglasses with tinted lenses and lightweight temples for all-day comfort."),
    ("Halo Desk Lamp", "Home & Living", 1499, 1999, 35, "lamp", "sun", True, 4.5, 143, "Warm-light desk lamp with a tilting shade and a stable weighted base."),
    ("Stoneware Coffee Mug", "Home & Living", 399, None, 90, "mug", "teal", False, 4.6, 260, "Hand-glazed style stoneware mug with a comfortable handle. Holds about 330 ml."),
    ("Fern Planter Set", "Home & Living", 849, 1099, 28, "plant", "mint", False, 4.2, 74, "Terracotta-look planter with a leafy decorative plant. A fresh accent for any shelf."),
    ("Haven Wall Clock", "Home & Living", 1199, None, 18, "clock", "slate", False, 4.3, 59, "Minimal silent wall clock with a clean dial that suits living rooms and offices."),
    ("Cloud Cushion", "Home & Living", 699, 999, 50, "cushion", "violet", False, 4.4, 102, "Plush square cushion with a removable cover and a soft polyester fill."),
    ("Glow Face Cream", "Beauty & Personal Care", 549, 699, 70, "jar", "rose", True, 4.2, 331, "Lightweight daily moisturiser that absorbs quickly and leaves skin feeling soft."),
    ("Velvet Matte Lipstick", "Beauty & Personal Care", 449, None, 85, "lipstick", "coral", False, 4.1, 207, "Comfortable matte colour with a smooth finish that lasts through the day."),
    ("Dew Hydrating Serum", "Beauty & Personal Care", 799, 999, 2, "bottle", "teal", False, 4.5, 156, "Fragrance-free hydrating serum in a pocket-friendly bottle with a simple dropper-style cap."),
    ("Rosewater Body Lotion", "Beauty & Personal Care", 349, None, 110, "jar", "sand", False, 4.0, 90, "Light body lotion with a gentle rose scent for everyday hydration."),
    ("Iron Grip Dumbbell Pair", "Sports & Fitness", 1999, 2599, 26, "dumbbell", "slate", True, 4.5, 118, "Pair of rubber-coated hex-style dumbbells for strength training at home."),
    ("Flex Yoga Mat", "Sports & Fitness", 899, 1299, 45, "mat", "mint", False, 4.3, 232, "6 mm non-slip yoga mat with a carry strap. Cushioned for joints, grippy for poses."),
    ("Arena Basketball", "Sports & Fitness", 1099, None, 33, "ball", "coral", False, 4.2, 67, "Size 7 composite-leather basketball with deep channels for a confident grip."),
    ("Hydra Steel Bottle", "Sports & Fitness", 649, 799, 75, "bottle", "blue", False, 4.4, 301, "Insulated stainless-steel bottle that keeps drinks cold or hot for hours."),
    ("The Quiet Compass (Novel)", "Books & Stationery", 349, None, 60, "book", "violet", False, 4.4, 51, "A reflective, easy-to-read fictional journey about finding direction. A sample title for the demo store."),
    ("Dotted Spiral Notebook", "Books & Stationery", 199, 249, 150, "notebook", "sun", True, 4.3, 275, "A5 spiral notebook with dotted pages for notes, plans and sketches."),
    ("Glide Gel Pen (Pack of 5)", "Books & Stationery", 149, None, 200, "pen", "blue", False, 4.5, 388, "Smooth-writing 0.5 mm gel pens in assorted colours. Quick-dry ink that resists smudging."),
    ("Atlas Hardcover Journal", "Books & Stationery", 499, 649, 0, "book", "sand", False, 4.6, 36, "Hardcover journal with thick, lined pages. Currently sold out, so it shows how out-of-stock items look."),
]

CITY_PIN = {
    "New Delhi": "110001", "Mumbai": "400001", "Jaipur": "302001", "Chandigarh": "160017", "Kochi": "682001",
    "Chennai": "600001", "Ahmedabad": "380001", "Bengaluru": "560001", "Lucknow": "226001", "Kolkata": "700001",
}


class Command(BaseCommand):
    help = "Seed categories, products (with images), demo users and sample orders. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--with-demo-users", action="store_true",
                            help="Also create/refresh the 10 demo customers and the demo admin (development only).")
        parser.add_argument("--skip-orders", action="store_true", help="Do not create demo order history.")
        parser.add_argument("--reset-orders", action="store_true", help="Delete and regenerate demo orders (is_demo=True only).")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["with_demo_users"]:
            if not settings.ALLOW_DEMO_ACCOUNTS:
                raise CommandError(
                    "Refusing to create demo accounts: NOVAMART_ALLOW_DEMO_ACCOUNTS/DJANGO_DEBUG is False. "
                    "Demo accounts use public passwords and must never exist in production."
                )
            self.seed_users()
        self.seed_catalog()
        if not opts["skip_orders"]:
            self.seed_orders(opts["reset_orders"])
        self.stdout.write(self.style.SUCCESS("Done. Start the site with: python manage.py runserver"))

    # ------------------------------------------------------------------ users
    def seed_users(self):
        created = 0
        for username, password, first, last, email, phone, city, state in DEMO_CUSTOMERS:
            user, was_created = User.objects.get_or_create(username=username, defaults={
                "first_name": first, "last_name": last, "email": email, "phone": phone, "role": User.Role.CUSTOMER})
            user.role, user.is_staff, user.is_superuser, user.is_active = User.Role.CUSTOMER, False, False, True
            user.set_password(password)  # hashed by Django; resets the demo password each run
            user.save()
            created += was_created
            if not user.addresses.exists():
                Address.objects.create(
                    user=user, label="Home", full_name=f"{first} {last}", phone=phone, line1=f"{10 + len(username)}, Demo Street",
                    city=city, state=state, postal_code=CITY_PIN.get(city, "110001"), is_default=True)

        username, password, first, last, email = DEMO_ADMIN
        admin, was_created = User.objects.get_or_create(username=username, defaults={
            "first_name": first, "last_name": last, "email": email})
        admin.role, admin.is_staff, admin.is_superuser, admin.is_active = User.Role.ADMIN, True, True, True
        admin.set_password(password)
        admin.save()
        self.stdout.write(f"Demo users ready: {len(DEMO_CUSTOMERS)} customers ({created} new) + admin '{username}'.")

    # ---------------------------------------------------------------- catalog
    def seed_catalog(self):
        cat_objs = {}
        for name, desc, shape, pal in CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name, defaults={"description": desc})
            if not cat.image or not cat.image.storage.exists(cat.image.name):
                cat.image.save(f"{cat.slug}.jpg", ContentFile(demo_images.render(shape, PALETTES[pal], size=640)), save=True)
            cat_objs[name] = cat

        new = 0
        for (name, cat, price, mrp, stock, shape, pal, featured, rating, n, desc) in PRODUCTS:
            product, created = Product.objects.get_or_create(name=name, defaults={
                "category": cat_objs[cat], "price": Decimal(price), "original_price": Decimal(mrp) if mrp else None,
                "stock": stock, "is_featured": featured, "rating": Decimal(str(rating)), "rating_count": n,
                "description": desc,
            })
            new += created
            if not product.image or not product.image.storage.exists(product.image.name):
                product.image.save(f"{product.slug}.jpg", ContentFile(demo_images.render(shape, PALETTES[pal])), save=True)
        self.stdout.write(f"Catalog ready: {len(cat_objs)} categories, {len(PRODUCTS)} products ({new} new).")

    # ----------------------------------------------------------------- orders
    def seed_orders(self, reset):
        existing = Order.objects.filter(is_demo=True)
        if existing.exists() and not reset:
            self.stdout.write(f"Demo orders already present ({existing.count()}); use --reset-orders to regenerate.")
            return
        if reset:
            existing.delete()
        customers = list(User.objects.filter(username__in=[c[0] for c in DEMO_CUSTOMERS], role=User.Role.CUSTOMER))
        products = list(Product.objects.select_related("category").filter(is_active=True))
        if not customers or not products:
            self.stdout.write(self.style.WARNING("No demo customers found; skipping demo orders (run with --with-demo-users)."))
            return

        rng = random.Random(2026)  # deterministic demo data
        statuses = (["delivered"] * 45 + ["shipped"] * 12 + ["processing"] * 10 + ["confirmed"] * 13
                    + ["pending"] * 8 + ["cancelled"] * 12)
        weights = [3 if p.is_featured else 1 for p in products]
        now = timezone.now()
        created = 0
        for _ in range(84):
            customer = rng.choice(customers)
            status = rng.choice(statuses)
            method = rng.choice([Order.PaymentMethod.COD, Order.PaymentMethod.SIMULATED])
            picked = {}
            for _p in range(rng.randint(1, 4)):
                prod = rng.choices(products, weights)[0]
                picked[prod] = picked.get(prod, 0) + rng.randint(1, 2)
            totals = calculate_totals((p.price, p.original_price, q) for p, q in picked.items())
            address = customer.addresses.first()
            paid = (method == Order.PaymentMethod.SIMULATED and status != "pending") or status == "delivered"
            if status == "cancelled":
                payment = Order.PaymentStatus.REFUNDED if method == Order.PaymentMethod.SIMULATED else Order.PaymentStatus.PENDING
            else:
                payment = Order.PaymentStatus.PAID if paid else Order.PaymentStatus.PENDING
            order = Order.objects.create(
                order_number=generate_order_number(), customer=customer, status=status, payment_method=method,
                payment_status=payment, ship_full_name=address.full_name, ship_phone=address.phone,
                ship_email=customer.email, ship_line1=address.line1, ship_city=address.city, ship_state=address.state,
                ship_postal_code=address.postal_code, subtotal=totals["subtotal"], delivery_charge=totals["delivery"],
                discount=totals["savings"], total=totals["total"], is_demo=True,
                stock_restored=(status == "cancelled"),  # demo stock is seeded "net"; cancelled = already returned
            )
            OrderItem.objects.bulk_create([
                OrderItem(order=order, product=p, product_name=p.name, sku=p.sku, category_name=p.category.name,
                          unit_price=p.price, quantity=q, line_total=p.price * q) for p, q in picked.items()])
            when = now - timedelta(days=rng.randint(0, 89), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
            Order.objects.filter(pk=order.pk).update(created_at=when, updated_at=when)
            created += 1
        self.stdout.write(f"Demo order history ready: {created} sample orders over the last 90 days (flagged is_demo).")
