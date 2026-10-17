from decimal import Decimal

from django.urls import reverse

from cart.models import Cart, CartItem
from cart.pricing import calculate_totals
from tests.helpers import PASSWORD, NovaTestCase, add_to_cart, make_category, make_customer, make_product

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class CartTests(NovaTestCase):
    def setUp(self):
        self.user = make_customer()
        self.other = make_customer("bob")
        self.cat = make_category("C")
        self.p = make_product("Thing", "300.00", 5, self.cat, original_price=Decimal("400"))
        self.client.login(username="alice", password=PASSWORD)

    def add(self, qty=1, product=None, **kw):
        return self.client.post(reverse("cart:add", args=[(product or self.p).pk]), {"quantity": qty}, **kw)

    def test_anonymous_cannot_add(self):
        self.client.logout()
        r = self.add()
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])
        self.assertFalse(CartItem.objects.exists())

    def test_add_item_creates_db_cart(self):
        self.add(2)
        item = CartItem.objects.get(cart__user=self.user)
        self.assertEqual((item.product, item.quantity), (self.p, 2))

    def test_adding_again_increments(self):
        self.add(1)
        self.add(2)
        self.assertEqual(CartItem.objects.get().quantity, 3)

    def test_cannot_exceed_stock(self):
        self.add(5)
        r = self.add(1, **AJAX)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["ok"])
        self.assertEqual(CartItem.objects.get().quantity, 5)
        r = self.add(99, product=make_product("Other", "10", 2, self.cat), **AJAX)
        self.assertEqual(r.status_code, 400)

    def test_invalid_quantities_rejected(self):
        for bad in ("0", "-3", "abc", "", "1.5"):
            r = self.add(bad, **AJAX)
            self.assertEqual(r.status_code, 400, bad)
        self.assertFalse(CartItem.objects.exists())

    def test_out_of_stock_and_inactive_cannot_be_added(self):
        self.assertEqual(self.add(1, product=make_product("Zero", "10", 0, self.cat), **AJAX).status_code, 400)
        inactive = make_product("Off", "10", 5, self.cat, is_active=False)
        self.assertEqual(self.add(1, product=inactive).status_code, 404)

    def test_add_requires_post(self):
        self.assertEqual(self.client.get(reverse("cart:add", args=[self.p.pk])).status_code, 405)

    def test_client_cannot_set_price(self):
        self.client.post(reverse("cart:add", args=[self.p.pk]), {"quantity": 1, "price": "1", "unit_price": "1", "total": "1"})
        r = self.client.get(reverse("cart:detail"))
        self.assertEqual(r.context["totals"]["subtotal"], Decimal("300.00"))

    def test_update_increment_decrement_and_set(self):
        item = add_to_cart(self.user, self.p, 2)
        url = reverse("cart:update", args=[item.pk])
        self.client.post(url, {"action": "inc"})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        self.client.post(url, {"action": "dec"})
        self.client.post(url, {"quantity": "4"})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)

    def test_update_above_stock_rejected(self):
        item = add_to_cart(self.user, self.p, 5)
        r = self.client.post(reverse("cart:update", args=[item.pk]), {"action": "inc"}, **AJAX)
        self.assertEqual(r.status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

    def test_update_garbage_and_negative_rejected(self):
        item = add_to_cart(self.user, self.p, 2)
        for bad in ("-1", "x"):
            self.assertEqual(self.client.post(reverse("cart:update", args=[item.pk]), {"quantity": bad}, **AJAX).status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)

    def test_decrement_to_zero_removes_item(self):
        item = add_to_cart(self.user, self.p, 1)
        r = self.client.post(reverse("cart:update", args=[item.pk]), {"action": "dec"}, **AJAX)
        self.assertTrue(r.json()["empty"])
        self.assertFalse(CartItem.objects.exists())

    def test_remove_item(self):
        item = add_to_cart(self.user, self.p, 2)
        self.client.post(reverse("cart:remove", args=[item.pk]))
        self.assertFalse(CartItem.objects.exists())

    def test_cannot_modify_someone_elses_cart(self):
        theirs = add_to_cart(self.other, self.p, 2)
        self.assertEqual(self.client.post(reverse("cart:update", args=[theirs.pk]), {"action": "inc"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("cart:remove", args=[theirs.pk])).status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.quantity, 2)

    def test_cart_page_only_shows_own_items(self):
        add_to_cart(self.other, make_product("Secret", "10", 3, self.cat), 1)
        self.assertNotContains(self.client.get(reverse("cart:detail")), "Secret")

    def test_empty_cart_state(self):
        r = self.client.get(reverse("cart:detail"))
        self.assertContains(r, "Your cart is empty")
        self.assertEqual(r.context["totals"]["total"], Decimal("0.00"))

    def test_totals_discount_delivery_and_json(self):
        r = self.add(2, **AJAX)  # 600 subtotal, saves 200, delivery 49
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["cart_count"], 2)
        self.assertEqual(data["subtotal"], "\u20b9600.00")
        self.assertEqual(data["savings"], "\u20b9200.00")
        self.assertEqual(data["total"], "\u20b9649.00")

    def test_navbar_badge_counts_items(self):
        add_to_cart(self.user, self.p, 3)
        self.assertContains(self.client.get(reverse("catalog:home")), 'data-cart-count>3<')

    def test_csrf_enforced_on_cart_posts(self):
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        strict.login(username="alice", password=PASSWORD)
        self.assertEqual(strict.post(reverse("cart:add", args=[self.p.pk]), {"quantity": 1}).status_code, 403)


class PricingTests(NovaTestCase):
    def test_free_delivery_threshold(self):
        t = calculate_totals([(Decimal("998.99"), None, 1)])
        self.assertEqual((t["delivery"], t["total"]), (Decimal("49.00"), Decimal("1047.99")))
        t = calculate_totals([(Decimal("999.00"), None, 1)])
        self.assertEqual((t["delivery"], t["total"]), (Decimal("0.00"), Decimal("999.00")))

    def test_empty_has_no_delivery_fee(self):
        self.assertEqual(calculate_totals([])["total"], Decimal("0.00"))

    def test_decimal_precision_no_float_errors(self):
        t = calculate_totals([(Decimal("0.10"), None, 3)])
        self.assertEqual(t["subtotal"], Decimal("0.30"))
