"""Project-wide checks: URLs, templates, static assets, migrations, fresh database."""
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import override_settings
from django.urls import NoReverseMatch, reverse

from unittest import mock

from tests.helpers import PASSWORD, NovaTestCase, fast_render, make_admin, make_category, make_customer, make_order, make_product

PUBLIC = ["catalog:home", "catalog:list", "catalog:categories", "accounts:login", "accounts:register"]


class PublicPageTests(NovaTestCase):
    def setUp(self):
        cat = make_category("Books")
        self.p = make_product("Book", "10", 5, cat)

    def test_public_pages_return_200(self):
        for name in PUBLIC:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(self.p.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.p.category.get_absolute_url()).status_code, 200)

    def test_home_has_expected_sections(self):
        r = self.client.get(reverse("catalog:home"))
        for text in ("Shop by category", "Trending now", "Best sellers", "New arrivals", "Find the good stuff"):
            self.assertContains(r, text)

    def test_all_named_urls_resolve(self):
        for name in ["catalog:home", "catalog:list", "cart:detail", "orders:checkout", "orders:history", "accounts:account",
                     "accounts:login", "accounts:register", "dashboard:home", "dashboard:analytics", "dashboard:sales"]:
            try:
                reverse(name)
            except NoReverseMatch:
                self.fail(name)
        self.assertEqual(reverse("catalog:home"), "/")
        self.assertEqual(reverse("dashboard:home"), "/dashboard/")
        self.assertEqual(reverse("cart:detail"), "/cart/")
        self.assertEqual(reverse("orders:checkout"), "/checkout/")

    def test_custom_404_page(self):
        r = self.client.get("/definitely-not-here/")
        self.assertContains(r, "Page not found", status_code=404)

    def test_login_redirect_for_anonymous_cart(self):
        self.assertRedirects(self.client.get("/cart/"), "/login/?next=/cart/")

    def test_storefront_links_in_navbar_work(self):
        make_customer()
        self.client.login(username="alice", password=PASSWORD)
        for name in ("cart:detail", "orders:history", "accounts:account", "accounts:addresses"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_template_has_no_unresolved_variables(self):
        # Django renders missing variables as "" -> look for leaked template syntax instead.
        make_admin()
        self.client.login(username="boss", password=PASSWORD)
        for url in ["/", "/products/", "/dashboard/", "/dashboard/analytics/", "/dashboard/products/add/"]:
            body = self.client.get(url).content.decode()
            self.assertNotIn("{{", body, url)
            self.assertNotIn("{%", body, url)


class StaticAssetTests(NovaTestCase):
    FILES = ["css/main.css", "css/components.css", "css/store.css", "css/auth.css", "css/dashboard.css",
             "js/main.js", "js/cart.js", "js/product.js", "js/dashboard.js", "vendor/chart.umd.js",
             "images/logo.svg", "images/hero.svg", "images/favicon.svg", "images/placeholders/product.svg",
             "images/placeholders/category.svg"]

    def test_static_files_exist(self):
        for f in self.FILES:
            self.assertIsNotNone(finders.find(f), f)

    def test_static_urls_in_pages_resolve(self):
        import re
        body = self.client.get("/").content.decode()
        refs = re.findall(r'(?:href|src)="/static/([^"]+)"', body)
        self.assertTrue(refs)
        for ref in refs:
            self.assertIsNotNone(finders.find(ref), ref)


class FreshDatabaseTests(NovaTestCase):
    def test_migrations_are_complete(self):
        out = StringIO()
        call_command("makemigrations", "--check", "--dry-run", stdout=out)  # raises SystemExit if model changes lack a migration

    def test_system_check_passes(self):
        call_command("check")

    def test_custom_user_model_in_use(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_sqlite_is_default_and_timezone_is_kolkata(self):
        self.assertEqual(settings.TIME_ZONE, "Asia/Kolkata")
        self.assertIn("sqlite3", settings.DATABASES["default"]["ENGINE"])


@mock.patch("catalog.demo_images.render", fast_render)
class EndToEndJourneyTest(NovaTestCase):
    """Seed -> login -> shop -> checkout -> admin sees it."""

    def test_full_journey_with_seed_data(self):
        call_command("seed_demo_data", "--with-demo-users", stdout=StringIO())
        from catalog.models import Product
        from orders.models import Order
        self.assertTrue(self.client.login(username="niraj_dalal", password="1234"))
        product = Product.objects.filter(stock__gt=3, price__gte=100).first()
        self.client.post(reverse("cart:add", args=[product.pk]), {"quantity": 2})
        before = product.stock
        r = self.client.post(reverse("orders:checkout"), {
            "ship_full_name": "Niraj Dalal", "ship_phone": "9810000001", "ship_email": "n@example.com", "ship_line1": "1 Test",
            "ship_city": "Delhi", "ship_state": "Delhi", "ship_postal_code": "110001", "payment_method": "simulated"})
        order = Order.objects.filter(customer__username="niraj_dalal", is_demo=False).get()
        self.assertRedirects(r, reverse("orders:confirmation", args=[order.order_number]))
        product.refresh_from_db()
        self.assertEqual(product.stock, before - 2)
        self.client.logout()
        self.client.login(username="novamart_admin", password="NovaAdmin@2026!")
        self.assertContains(self.client.get(reverse("dashboard:orders")), order.order_number)
        self.assertEqual(self.client.get(reverse("dashboard:analytics")).status_code, 200)
