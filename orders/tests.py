from decimal import Decimal
from unittest import mock

from django.urls import reverse

from accounts.models import Address
from cart.models import CartItem
from orders.models import Order, OrderItem
from orders.services import CheckoutError, change_order_status, place_order
from tests.helpers import (PASSWORD, NovaTestCase, add_to_cart, checkout_payload, make_category, make_customer,
                           make_order, make_product)


class CheckoutTests(NovaTestCase):
    def setUp(self):
        self.user = make_customer()
        self.other = make_customer("bob")
        self.cat = make_category("C")
        self.p1 = make_product("Alpha", "300.00", 10, self.cat, original_price=Decimal("400"))
        self.p2 = make_product("Beta", "150.50", 4, self.cat)
        self.client.login(username="alice", password=PASSWORD)

    def checkout(self, **kw):
        return self.client.post(reverse("orders:checkout"), checkout_payload(**kw))

    def test_checkout_page_requires_items(self):
        r = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(r, reverse("cart:detail"))

    def test_checkout_page_renders_summary(self):
        add_to_cart(self.user, self.p1, 2)
        r = self.client.get(reverse("orders:checkout"))
        self.assertContains(r, "Order summary")
        self.assertContains(r, "Place order")

    def test_valid_checkout_creates_order_items_and_clears_cart(self):
        add_to_cart(self.user, self.p1, 2)  # 600
        add_to_cart(self.user, self.p2, 1)  # 150.50 -> 750.50 + 49 delivery
        r = self.checkout()
        order = Order.objects.get()
        self.assertRedirects(r, reverse("orders:confirmation", args=[order.order_number]))
        self.assertTrue(order.order_number.startswith("NM-"))
        self.assertEqual(order.customer, self.user)
        self.assertEqual((order.subtotal, order.delivery_charge, order.total), (Decimal("750.50"), Decimal("49.00"), Decimal("799.50")))
        self.assertEqual(order.discount, Decimal("200.00"))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.ship_city, "Mumbai")
        self.assertFalse(CartItem.objects.exists())

    def test_inventory_reduced(self):
        add_to_cart(self.user, self.p1, 3)
        self.checkout()
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 7)

    def test_order_item_snapshots_survive_price_change(self):
        add_to_cart(self.user, self.p1, 1)
        self.checkout()
        self.p1.price = Decimal("999.00")
        self.p1.name = "Renamed"
        self.p1.save()
        item = OrderItem.objects.get()
        self.assertEqual((item.product_name, item.unit_price), ("Alpha", Decimal("300.00")))

    def test_simulated_payment_marks_paid_and_confirmed(self):
        add_to_cart(self.user, self.p1, 1)
        self.checkout(payment_method="simulated")
        o = Order.objects.get()
        self.assertEqual((o.status, o.payment_status), (Order.Status.CONFIRMED, Order.PaymentStatus.PAID))

    def test_free_delivery_over_threshold(self):
        add_to_cart(self.user, self.p1, 4)  # 1200
        self.checkout()
        o = Order.objects.get()
        self.assertEqual((o.delivery_charge, o.total), (Decimal("0.00"), Decimal("1200.00")))

    def test_price_is_taken_from_database_not_request(self):
        add_to_cart(self.user, self.p1, 1)
        self.checkout(total="1.00", subtotal="1.00", unit_price="1.00", delivery_charge="0")
        o = Order.objects.get()
        self.assertEqual(o.total, Decimal("349.00"))  # 300 + 49 delivery
        self.assertEqual(o.items.get().unit_price, Decimal("300.00"))

    def test_price_change_after_adding_to_cart_uses_current_price(self):
        add_to_cart(self.user, self.p1, 1)
        self.p1.price = Decimal("500.00")
        self.p1.save()
        self.checkout()
        self.assertEqual(Order.objects.get().subtotal, Decimal("500.00"))

    def test_invalid_form_creates_nothing(self):
        add_to_cart(self.user, self.p1, 1)
        r = self.checkout(ship_postal_code="12", ship_phone="abc")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "valid 6-digit PIN")
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.exists())
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)

    def test_invalid_payment_method_rejected(self):
        add_to_cart(self.user, self.p1, 1)
        self.checkout(payment_method="bitcoin")
        self.assertFalse(Order.objects.exists())

    def test_stock_dropped_after_adding_to_cart_blocks_checkout(self):
        add_to_cart(self.user, self.p2, 4)
        self.p2.stock = 2
        self.p2.save()
        r = self.checkout()
        self.assertRedirects(r, reverse("cart:detail"))
        self.assertFalse(Order.objects.exists())
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.stock, 2)
        self.assertTrue(CartItem.objects.exists())

    def test_quantity_manipulated_in_database_is_rejected(self):
        item = add_to_cart(self.user, self.p2, 1)
        CartItem.objects.filter(pk=item.pk).update(quantity=999)
        self.checkout()
        self.assertFalse(Order.objects.exists())

    def test_product_deactivated_after_adding_blocks_checkout(self):
        add_to_cart(self.user, self.p1, 1)
        self.p1.is_active = False
        self.p1.save()
        self.checkout()
        self.assertFalse(Order.objects.exists())

    def test_failure_midway_rolls_back_everything(self):
        add_to_cart(self.user, self.p1, 2)
        add_to_cart(self.user, self.p2, 1)
        shipping = {k: v for k, v in checkout_payload().items() if k.startswith("ship_")}
        with mock.patch("orders.services.OrderItem.objects.bulk_create", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                place_order(self.user, shipping, "cod")
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual((self.p1.stock, self.p2.stock), (10, 4))
        self.assertEqual(CartItem.objects.count(), 2)

    def test_sellout_during_checkout_rolls_back_earlier_decrements(self):
        add_to_cart(self.user, self.p1, 2)
        add_to_cart(self.user, self.p2, 2)
        shipping = {k: v for k, v in checkout_payload().items() if k.startswith("ship_")}
        real_update = type(self.p2.__class__.objects.filter(pk=1)).update
        calls = {"n": 0}

        def flaky(qs, **kw):
            calls["n"] += 1
            if calls["n"] == 2:  # second product "just sold out"
                return 0
            return real_update(qs, **kw)

        with mock.patch("django.db.models.query.QuerySet.update", flaky):
            with self.assertRaises(CheckoutError):
                place_order(self.user, shipping, "cod")
        self.assertFalse(Order.objects.exists())
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 10)

    def test_address_saved_on_checkout(self):
        add_to_cart(self.user, self.p1, 1)
        self.checkout()
        self.assertEqual(Address.objects.filter(user=self.user, city="Mumbai").count(), 1)

    def test_checkout_requires_login_and_post_has_csrf(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("orders:checkout")).status_code, 302)
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        strict.login(username="alice", password=PASSWORD)
        self.assertEqual(strict.post(reverse("orders:checkout"), checkout_payload()).status_code, 403)

    def test_order_numbers_unique(self):
        numbers = set()
        for _ in range(5):
            add_to_cart(self.user, self.p1, 1)
            self.checkout()
        numbers = set(Order.objects.values_list("order_number", flat=True))
        self.assertEqual(len(numbers), 5)


class OrderAccessTests(NovaTestCase):
    def setUp(self):
        self.alice, self.bob = make_customer(), make_customer("bob")
        self.p = make_product("Thing", "100", 10)
        self.mine = make_order(self.alice, [(self.p, 1, None)])
        self.theirs = make_order(self.bob, [(self.p, 2, None)])
        self.client.login(username="alice", password=PASSWORD)

    def test_history_shows_only_own_orders(self):
        r = self.client.get(reverse("orders:history"))
        self.assertContains(r, self.mine.order_number)
        self.assertNotContains(r, self.theirs.order_number)

    def test_cannot_view_confirm_or_cancel_other_customers_order(self):
        for name in ("detail", "confirmation"):
            self.assertEqual(self.client.get(reverse(f"orders:{name}", args=[self.theirs.order_number])).status_code, 404)
        self.assertEqual(self.client.post(reverse("orders:cancel", args=[self.theirs.order_number])).status_code, 404)
        self.theirs.refresh_from_db()
        self.assertNotEqual(self.theirs.status, Order.Status.CANCELLED)

    def test_own_order_detail_renders(self):
        r = self.client.get(self.mine.get_absolute_url())
        self.assertContains(r, self.mine.order_number)
        self.assertContains(r, "Thing")

    def test_empty_history_state(self):
        self.client.logout()
        make_customer("carol")
        self.client.login(username="carol", password=PASSWORD)
        self.assertContains(self.client.get(reverse("orders:history")), "No orders yet")


class StatusAndInventoryTests(NovaTestCase):
    def setUp(self):
        self.user = make_customer()
        self.p = make_product("Thing", "100", 10)

    def pending_order(self, qty=3, payment="cod"):
        add_to_cart(self.user, self.p, qty)
        shipping = {k: v for k, v in checkout_payload().items() if k.startswith("ship_")}
        return place_order(self.user, shipping, payment)

    def stock(self):
        self.p.refresh_from_db()
        return self.p.stock

    def test_cancel_restores_stock_once(self):
        o = self.pending_order(3)
        self.assertEqual(self.stock(), 7)
        change_order_status(o.pk, Order.Status.CANCELLED)
        self.assertEqual(self.stock(), 10)
        change_order_status(o.pk, Order.Status.CANCELLED)  # idempotent
        self.assertEqual(self.stock(), 10)

    def test_reopen_cancelled_order_takes_stock_again(self):
        o = self.pending_order(3)
        change_order_status(o.pk, Order.Status.CANCELLED)
        change_order_status(o.pk, Order.Status.PROCESSING)
        self.assertEqual(self.stock(), 7)
        change_order_status(o.pk, Order.Status.CANCELLED)
        self.assertEqual(self.stock(), 10)

    def test_reopen_fails_when_stock_gone(self):
        o = self.pending_order(3)
        change_order_status(o.pk, Order.Status.CANCELLED)
        self.p.stock = 1
        self.p.save()
        with self.assertRaises(CheckoutError):
            change_order_status(o.pk, Order.Status.SHIPPED)
        o.refresh_from_db()
        self.assertEqual(o.status, Order.Status.CANCELLED)
        self.assertEqual(self.stock(), 1)

    def test_normal_progression_does_not_touch_stock(self):
        o = self.pending_order(3)
        for s in (Order.Status.CONFIRMED, Order.Status.PROCESSING, Order.Status.SHIPPED, Order.Status.DELIVERED):
            change_order_status(o.pk, s)
            self.assertEqual(self.stock(), 7)

    def test_cod_delivery_marks_paid(self):
        o = self.pending_order(1)
        change_order_status(o.pk, Order.Status.DELIVERED)
        o.refresh_from_db()
        self.assertEqual(o.payment_status, Order.PaymentStatus.PAID)

    def test_cancelling_paid_order_marks_refunded_and_reopen_restores_paid(self):
        o = self.pending_order(1, payment="simulated")
        change_order_status(o.pk, Order.Status.CANCELLED)
        o.refresh_from_db()
        self.assertEqual(o.payment_status, Order.PaymentStatus.REFUNDED)
        change_order_status(o.pk, Order.Status.CONFIRMED)
        o.refresh_from_db()
        self.assertEqual(o.payment_status, Order.PaymentStatus.PAID)

    def test_unknown_status_rejected(self):
        o = self.pending_order(1)
        with self.assertRaises(CheckoutError):
            change_order_status(o.pk, "teleported")

    def test_deleted_product_does_not_break_cancellation(self):
        o = self.pending_order(2)
        self.p.delete()
        change_order_status(o.pk, Order.Status.CANCELLED)  # no crash
        self.assertEqual(OrderItem.objects.get().product_name, "Thing")

    def test_customer_can_cancel_pending_but_not_shipped(self):
        self.client.login(username="alice", password=PASSWORD)
        o = self.pending_order(2)
        self.client.post(reverse("orders:cancel", args=[o.order_number]))
        o.refresh_from_db()
        self.assertEqual(o.status, Order.Status.CANCELLED)
        self.assertEqual(self.stock(), 10)
        o2 = self.pending_order(1)
        change_order_status(o2.pk, Order.Status.SHIPPED)
        self.client.post(reverse("orders:cancel", args=[o2.order_number]))
        o2.refresh_from_db()
        self.assertEqual(o2.status, Order.Status.SHIPPED)
