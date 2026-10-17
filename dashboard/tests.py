from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from catalog.models import Category, Product
from dashboard import analytics
from orders.models import Order
from tests.helpers import (PASSWORD, NovaTestCase, add_to_cart, make_admin, make_category, make_customer, make_order,
                           make_product, png_upload)


class AdminTestCase(NovaTestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.login(username="boss", password=PASSWORD)


class DashboardAccessTests(NovaTestCase):
    URLS = ["home", "products", "product_add", "categories", "category_add", "orders", "customers", "analytics", "sales", "sales_export"]

    def test_anonymous_redirected_customer_forbidden_admin_ok(self):
        make_customer()
        make_admin()
        for name in self.URLS:
            self.client.logout()
            self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 302, name)
            self.client.login(username="alice", password=PASSWORD)
            self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 403, name)
            self.client.logout()
            self.client.login(username="boss", password=PASSWORD)
            self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 200, name)

    def test_deactivated_admin_loses_access(self):
        a = make_admin()
        self.client.login(username="boss", password=PASSWORD)
        a.is_active = False
        a.save()
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 302)

    def test_customer_cannot_post_destructive_actions(self):
        c = make_customer()
        p = make_product("Keep", "10", 1)
        cat = p.category
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.post(reverse("dashboard:product_delete", args=[p.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("dashboard:category_delete", args=[cat.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("dashboard:customer_toggle", args=[c.pk])).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=p.pk).exists())


class ProductCrudTests(AdminTestCase):
    def payload(self, **kw):
        d = {"name": "New Gadget", "category": make_category("Tech").pk, "price": "1299.00", "original_price": "1599.00",
             "stock": "12", "sku": "", "description": "Nice", "is_active": "on", "is_featured": "on", "rating": "4.5", "rating_count": "10"}
        d.update(kw)
        return d

    def test_create_product_with_image_upload(self):
        r = self.client.post(reverse("dashboard:product_add"), {**self.payload(), "image": png_upload()})
        self.assertRedirects(r, reverse("dashboard:products"))
        p = Product.objects.get(name="New Gadget")
        self.assertEqual(p.price, Decimal("1299.00"))
        self.assertTrue(p.is_featured)
        self.assertTrue(p.image.storage.exists(p.image.name))
        self.assertTrue(p.sku.startswith("NM-"))

    def test_extra_images_saved(self):
        r = self.client.post(reverse("dashboard:product_add"), {**self.payload(), "image": png_upload("a.png"),
                                                                  "extra_images": [png_upload("b.png"), png_upload("c.png")]})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Product.objects.get().extra_images.count(), 2)

    def test_invalid_data_shows_errors_and_saves_nothing(self):
        r = self.client.post(reverse("dashboard:product_add"), self.payload(price="-5", stock="-1", original_price="1"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Product.objects.exists())
        self.assertContains(r, "errorlist")

    def test_bad_upload_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        r = self.client.post(reverse("dashboard:product_add"), {**self.payload(), "image": SimpleUploadedFile("x.png", b"nope", "image/png")})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Product.objects.exists())

    def test_duplicate_sku_rejected(self):
        make_product("A", "10", 1, sku="DUP-1")
        r = self.client.post(reverse("dashboard:product_add"), self.payload(sku="dup-1"))
        self.assertContains(r, "SKU already exists")

    def test_edit_price_stock_category_featured(self):
        p = make_product("Old", "100", 5)
        new_cat = make_category("Other")
        r = self.client.post(reverse("dashboard:product_edit", args=[p.pk]), self.payload(name="Old", price="150.00", stock="99", category=new_cat.pk, original_price="", is_featured=""))
        self.assertRedirects(r, reverse("dashboard:products"))
        p.refresh_from_db()
        self.assertEqual((p.price, p.stock, p.category, p.is_featured), (Decimal("150.00"), 99, new_cat, False))

    def test_delete_product_without_orders(self):
        p = make_product("Temp", "10", 1)
        self.client.post(reverse("dashboard:product_delete", args=[p.pk]))
        self.assertFalse(Product.objects.filter(pk=p.pk).exists())

    def test_delete_product_with_orders_deactivates_instead(self):
        p = make_product("Sold", "10", 1)
        make_order(make_customer(), [(p, 1, None)])
        self.client.post(reverse("dashboard:product_delete", args=[p.pk]))
        p.refresh_from_db()
        self.assertFalse(p.is_active)

    def test_product_delete_requires_post(self):
        p = make_product("Safe", "10", 1)
        self.assertEqual(self.client.get(reverse("dashboard:product_delete", args=[p.pk])).status_code, 405)

    def test_search_and_filters(self):
        make_product("Lamp", "10", 20, sku="LMP-1")
        make_product("Tiny", "10", 2)
        make_product("Hidden", "10", 5, is_active=False)
        names = lambda **q: [p.name for p in self.client.get(reverse("dashboard:products"), q).context["page"]]
        self.assertEqual(names(q="LMP"), ["Lamp"])
        self.assertEqual(names(state="low"), ["Tiny"])
        self.assertEqual(names(state="inactive"), ["Hidden"])

    def test_remove_extra_image(self):
        p = make_product("P", "10", 1)
        from catalog.models import ProductImage
        img = ProductImage.objects.create(product=p, image=png_upload("z.png"))
        self.client.post(reverse("dashboard:product_image_delete", args=[p.pk, img.pk]))
        self.assertFalse(ProductImage.objects.exists())


class CategoryCrudTests(AdminTestCase):
    def test_create_edit_with_image(self):
        r = self.client.post(reverse("dashboard:category_add"), {"name": "Toys", "slug": "", "description": "Fun", "is_active": "on", "image": png_upload()})
        self.assertRedirects(r, reverse("dashboard:categories"))
        c = Category.objects.get(name="Toys")
        self.assertEqual(c.slug, "toys")
        self.assertTrue(c.image.storage.exists(c.image.name))
        self.client.post(reverse("dashboard:category_edit", args=[c.pk]), {"name": "Toys & Games", "slug": "toys", "description": "", "is_active": ""})
        c.refresh_from_db()
        self.assertEqual(c.name, "Toys & Games")
        self.assertFalse(c.is_active)

    def test_duplicate_name_rejected(self):
        make_category("Toys")
        r = self.client.post(reverse("dashboard:category_add"), {"name": "Toys", "is_active": "on"})
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(r.status_code, 200)

    def test_cannot_delete_category_with_products(self):
        p = make_product("In use")
        r = self.client.post(reverse("dashboard:category_delete", args=[p.category.pk]), follow=True)
        self.assertTrue(Category.objects.filter(pk=p.category.pk).exists())
        self.assertTrue(Product.objects.filter(pk=p.pk).exists())
        self.assertContains(r, "still has 1 product")

    def test_delete_empty_category(self):
        c = make_category("Empty")
        self.client.post(reverse("dashboard:category_delete", args=[c.pk]))
        self.assertFalse(Category.objects.filter(pk=c.pk).exists())

    def test_deactivating_hides_category_from_store(self):
        c = make_category("Hide me")
        make_product("Invisible", "10", 1, c)
        c.is_active = False
        c.save()
        self.assertNotContains(self.client.get(reverse("catalog:list")), "Invisible")


class OrderManagementTests(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.cust = make_customer()
        self.p = make_product("Thing", "100", 10)

    def test_list_search_filter_and_date(self):
        a = make_order(self.cust, [(self.p, 1, None)], Order.Status.PENDING, days_ago=1)
        b = make_order(self.cust, [(self.p, 1, None)], Order.Status.SHIPPED, days_ago=40)
        names = lambda **q: {o.order_number for o in self.client.get(reverse("dashboard:orders"), q).context["page"]}
        self.assertEqual(names(), {a.order_number, b.order_number})
        self.assertEqual(names(q=a.order_number), {a.order_number})
        self.assertEqual(names(q="alice"), {a.order_number, b.order_number})
        self.assertEqual(names(status="shipped"), {b.order_number})
        d = (timezone.localdate() - timedelta(days=10)).isoformat()
        self.assertEqual(names(**{"from": d}), {a.order_number})
        self.assertEqual(names(to=d), {b.order_number})

    def test_detail_shows_shipping_and_items(self):
        o = make_order(self.cust, [(self.p, 3, None)])
        r = self.client.get(reverse("dashboard:order_detail", args=[o.order_number]))
        self.assertContains(r, "Thing")
        self.assertContains(r, "1 Road")

    def test_status_update_and_inventory_restoration(self):
        from orders.services import place_order
        add_to_cart(self.cust, self.p, 4)
        o = place_order(self.cust, dict(ship_full_name="A", ship_phone="9876543210", ship_email="", ship_line1="1", ship_line2="",
                                        ship_city="C", ship_state="S", ship_postal_code="110001"), "cod")
        url = reverse("dashboard:order_detail", args=[o.order_number])
        self.client.post(url, {"status": "shipped"})
        o.refresh_from_db()
        self.assertEqual(o.status, "shipped")
        self.client.post(url, {"status": "cancelled"})
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 10)

    def test_invalid_status_rejected(self):
        o = make_order(self.cust, [(self.p, 1, None)], Order.Status.PENDING)
        self.client.post(reverse("dashboard:order_detail", args=[o.order_number]), {"status": "bogus"})
        o.refresh_from_db()
        self.assertEqual(o.status, "pending")


class CustomerManagementTests(AdminTestCase):
    def test_list_search_detail_toggle(self):
        c = make_customer("zed", first_name="Zed")
        make_customer("amy")
        r = self.client.get(reverse("dashboard:customers"), {"q": "zed"})
        self.assertEqual([u.username for u in r.context["page"]], ["zed"])
        self.assertNotIn("boss", [u.username for u in self.client.get(reverse("dashboard:customers")).context["page"]])
        self.assertContains(self.client.get(reverse("dashboard:customer_detail", args=[c.pk])), "@zed")
        self.client.post(reverse("dashboard:customer_toggle", args=[c.pk]))
        c.refresh_from_db()
        self.assertFalse(c.is_active)

    def test_password_hash_never_displayed(self):
        c = make_customer("zed")
        for url in (reverse("dashboard:customers"), reverse("dashboard:customer_detail", args=[c.pk])):
            body = self.client.get(url).content.decode()
            self.assertNotIn("pbkdf2", body)
            self.assertNotIn(PASSWORD, body)

    def test_admins_cannot_be_managed_as_customers(self):
        self.assertEqual(self.client.get(reverse("dashboard:customer_detail", args=[self.admin.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("dashboard:customer_toggle", args=[self.admin.pk])).status_code, 404)

    def test_deactivated_customer_cannot_log_in(self):
        c = make_customer("zed")
        self.client.post(reverse("dashboard:customer_toggle", args=[c.pk]))
        self.client.logout()
        self.assertFalse(self.client.login(username="zed", password=PASSWORD))


class AnalyticsTests(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.cust = make_customer()
        self.elec = make_category("Electronics")
        self.book = make_category("Books")
        self.tv = make_product("TV", "100.00", 50, self.elec)
        self.novel = make_product("Novel", "50.00", 50, self.book)
        S = Order.Status
        # counted: confirmed 100 + delivered (2*100 + 50) = 350 in 2 orders... plus shipped below
        self.o1 = make_order(self.cust, [(self.tv, 1, None)], S.CONFIRMED, days_ago=2)
        self.o2 = make_order(self.cust, [(self.tv, 2, None), (self.novel, 1, None)], S.DELIVERED, days_ago=2)
        self.o3 = make_order(self.cust, [(self.novel, 4, None)], S.SHIPPED, days_ago=9)
        # NOT revenue
        make_order(self.cust, [(self.tv, 10, None)], S.PENDING, days_ago=1)
        make_order(self.cust, [(self.tv, 20, None)], S.CANCELLED, days_ago=1)

    def rng(self):
        today = timezone.localdate()
        return today - timedelta(days=30), today

    def test_summary_excludes_pending_and_cancelled(self):
        s = analytics.summary(*self.rng())
        self.assertEqual(s["orders"], 3)
        self.assertEqual(s["revenue"], Decimal("100") + Decimal("250") + Decimal("200"))
        self.assertEqual(s["aov"], (Decimal("550") / 3).quantize(Decimal("0.01")))

    def test_daily_weekly_monthly_do_not_double_count(self):
        start, end = self.rng()
        for period in ("daily", "weekly", "monthly"):
            series = analytics.sales_series(start, end, period)
            self.assertEqual(sum(r["revenue"] for r in series), Decimal("550"), period)
            self.assertEqual(sum(r["orders"] for r in series), 3, period)

    def test_daily_series_is_continuous(self):
        start, end = self.rng()
        series = analytics.sales_series(start, end, "daily")
        self.assertEqual(len(series), 31)

    def test_category_and_product_sales(self):
        start, end = self.rng()
        cats = {c["category_name"]: (c["units"], c["revenue"]) for c in analytics.category_sales(start, end)}
        self.assertEqual(cats["Electronics"], (3, Decimal("300")))
        self.assertEqual(cats["Books"], (5, Decimal("250")))
        top = analytics.top_products(start, end)
        self.assertEqual(top[0]["product_name"], "Novel")
        self.assertEqual(top[0]["units"], 5)

    def test_date_range_filtering(self):
        today = timezone.localdate()
        s = analytics.summary(today - timedelta(days=5), today)
        self.assertEqual(s["orders"], 2)  # the shipped order is 9 days old
        self.assertEqual(s["revenue"], Decimal("350"))

    def test_reversed_range_is_swapped(self):
        a, b = analytics.parse_range({"from": "2026-03-10", "to": "2026-03-01"})
        self.assertLess(a, b)

    def test_page_context_matches_calculations(self):
        today = timezone.localdate()
        r = self.client.get(reverse("dashboard:analytics"), {"from": (today - timedelta(days=30)).isoformat(), "to": today.isoformat()})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["summary"]["revenue"], Decimal("550"))
        self.assertTrue(r.context["has_data"])
        self.assertAlmostEqual(sum(r.context["chart"]["series"]["daily"]["revenue"]), 550.0)
        self.assertContains(r, "analytics-data")

    def test_empty_state_when_no_sales(self):
        Order.objects.all().delete()
        r = self.client.get(reverse("dashboard:analytics"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["has_data"])
        self.assertEqual(r.context["summary"]["revenue"], Decimal("0"))
        self.assertContains(r, "No sales in this range")

    def test_dashboard_home_metrics_are_database_driven(self):
        r = self.client.get(reverse("dashboard:home"))
        self.assertEqual(r.context["revenue"], Decimal("550"))
        self.assertEqual(r.context["orders_total"], 5)
        self.assertEqual(r.context["orders_cancelled"], 1)
        self.assertEqual(r.context["customers"], 1)
        self.assertEqual(r.context["products_active"], 2)
        make_product("Scarce", "5", 1)
        self.assertEqual(self.client.get(reverse("dashboard:home")).context["low_stock_count"], 1)

    def test_csv_export_and_formula_injection_guard(self):
        evil = make_customer("=cmd")
        make_order(evil, [(self.tv, 1, None)], Order.Status.DELIVERED, days_ago=1)
        r = self.client.get(reverse("dashboard:sales_export"))
        self.assertEqual(r["Content-Type"].split(";")[0], "text/csv")
        body = r.content.decode()
        self.assertIn("Order,Date,Status", body)
        self.assertIn("'=cmd", body)
        self.assertNotIn(",=cmd", body)

    def test_sales_page_lists_lines(self):
        r = self.client.get(reverse("dashboard:sales"), {"from": (timezone.localdate() - timedelta(days=30)).isoformat()})
        self.assertContains(r, "Novel")
        self.assertEqual(r.context["totals"]["orders"], 3)
