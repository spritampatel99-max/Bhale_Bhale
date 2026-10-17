from io import StringIO

from django.core.management import CommandError, call_command
from django.test import override_settings
from django.urls import reverse

from accounts.demo_users import DEMO_ADMIN, DEMO_CUSTOMERS
from accounts.models import Address, User
from unittest import mock

from tests.helpers import PASSWORD, NovaTestCase, fast_render, make_address, make_admin, make_customer


class LoginTests(NovaTestCase):
    def setUp(self):
        self.customer = make_customer()
        self.admin = make_admin()

    def test_login_page_renders(self):
        r = self.client.get(reverse("accounts:login"))
        self.assertContains(r, "Welcome back")

    def test_valid_customer_login_goes_to_storefront(self):
        r = self.client.post(reverse("accounts:login"), {"username": "alice", "password": PASSWORD})
        self.assertRedirects(r, reverse("catalog:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.customer.pk)

    def test_valid_admin_login_goes_to_dashboard(self):
        r = self.client.post(reverse("accounts:login"), {"username": "boss", "password": PASSWORD})
        self.assertRedirects(r, reverse("dashboard:home"))

    def test_invalid_login_shows_error_and_does_not_authenticate(self):
        r = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "wrong"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Please enter a correct username and password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_login(self):
        self.customer.is_active = False
        self.customer.save()
        r = self.client.post(reverse("accounts:login"), {"username": "alice", "password": PASSWORD})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(r.status_code, 200)

    def test_remember_me_controls_session_expiry(self):
        self.client.post(reverse("accounts:login"), {"username": "alice", "password": PASSWORD})
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        self.client.logout()
        self.client.post(reverse("accounts:login"), {"username": "alice", "password": PASSWORD, "remember_me": "on"})
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_safe_next_redirect_is_followed(self):
        r = self.client.post(reverse("accounts:login") + "?next=/orders/", {"username": "alice", "password": PASSWORD})
        self.assertRedirects(r, "/orders/", fetch_redirect_response=False)

    def test_external_next_redirect_is_ignored(self):
        r = self.client.post(reverse("accounts:login") + "?next=https://evil.example/", {"username": "alice", "password": PASSWORD})
        self.assertRedirects(r, reverse("catalog:home"))

    def test_customer_next_to_dashboard_goes_home_instead(self):
        r = self.client.post(reverse("accounts:login") + "?next=/dashboard/", {"username": "alice", "password": PASSWORD})
        self.assertRedirects(r, reverse("catalog:home"))

    def test_logout_ends_session(self):
        self.client.login(username="alice", password=PASSWORD)
        r = self.client.post(reverse("accounts:logout"))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get(reverse("orders:history")).status_code, 302)

    def test_logout_requires_post(self):
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)

    def test_authenticated_user_visiting_login_is_redirected_by_role(self):
        self.client.login(username="boss", password=PASSWORD)
        self.assertRedirects(self.client.get(reverse("accounts:login")), reverse("dashboard:home"))


class RoleModelTests(NovaTestCase):
    def test_admin_role_forces_staff(self):
        u = User.objects.create_user("a1", password="x", role=User.Role.ADMIN)
        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_admin_role)

    def test_customer_role_cannot_be_staff(self):
        u = User.objects.create_user("c1", password="x", role=User.Role.CUSTOMER, is_staff=True)
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_admin_role)

    def test_superuser_gets_admin_role(self):
        u = User.objects.create_superuser("root", "r@example.com", "x")
        self.assertEqual(u.role, User.Role.ADMIN)
        self.assertTrue(u.is_admin_role)

    def test_passwords_are_hashed(self):
        u = make_customer("hashy")
        self.assertNotEqual(u.password, PASSWORD)
        self.assertIn("$", u.password)  # "<algorithm>$<salt>$<hash>", never the raw password


class AccessControlTests(NovaTestCase):
    def test_anonymous_redirected_from_protected_pages(self):
        for name in ("cart:detail", "orders:checkout", "orders:history", "accounts:account", "dashboard:home"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn(reverse("accounts:login"), r["Location"])

    def test_customer_gets_403_on_every_dashboard_page(self):
        make_customer()
        self.client.login(username="alice", password=PASSWORD)
        for name in ("home", "products", "product_add", "categories", "category_add", "orders", "customers", "analytics", "sales", "sales_export"):
            self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 403, name)

    def test_customer_cannot_post_admin_actions(self):
        make_customer()
        self.client.login(username="alice", password=PASSWORD)
        r = self.client.post(reverse("dashboard:category_add"), {"name": "Hack"})
        self.assertEqual(r.status_code, 403)

    def test_admin_can_open_storefront(self):
        make_admin()
        self.client.login(username="boss", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("catalog:home")).status_code, 200)

    def test_customer_cannot_use_django_admin(self):
        make_customer()
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_403_page_is_friendly(self):
        make_customer()
        self.client.login(username="alice", password=PASSWORD)
        r = self.client.get(reverse("dashboard:home"))
        self.assertContains(r, "Access denied", status_code=403)


class RegistrationTests(NovaTestCase):
    def data(self, **kw):
        d = {"username": "newbie", "first_name": "New", "last_name": "Bie", "email": "n@example.com",
             "phone": "9999999999", "password1": "Tr1cky-Pass#77", "password2": "Tr1cky-Pass#77"}
        d.update(kw)
        return d

    def test_register_creates_customer_and_logs_in(self):
        r = self.client.post(reverse("accounts:register"), self.data())
        self.assertRedirects(r, reverse("catalog:home"))
        u = User.objects.get(username="newbie")
        self.assertEqual(u.role, User.Role.CUSTOMER)
        self.assertFalse(u.is_staff)

    def test_cannot_register_as_admin_by_tampering(self):
        self.client.post(reverse("accounts:register"), self.data(role="admin", is_staff="on", is_superuser="on"))
        u = User.objects.get(username="newbie")
        self.assertEqual(u.role, User.Role.CUSTOMER)
        self.assertFalse(u.is_staff or u.is_superuser)

    def test_weak_password_rejected_with_message(self):
        r = self.client.post(reverse("accounts:register"), self.data(password1="1234", password2="1234"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newbie").exists())
        self.assertContains(r, "too short")

    def test_duplicate_username_rejected(self):
        make_customer("newbie")
        r = self.client.post(reverse("accounts:register"), self.data())
        self.assertContains(r, "already exists")


class AccountPageTests(NovaTestCase):
    def setUp(self):
        self.u = make_customer()
        self.other = make_customer("bob")
        self.client.login(username="alice", password=PASSWORD)

    def test_profile_update(self):
        r = self.client.post(reverse("accounts:account"), {"first_name": "Al", "last_name": "Ice", "email": "al@example.com", "phone": "9000000000"})
        self.assertRedirects(r, reverse("accounts:account"))
        self.u.refresh_from_db()
        self.assertEqual(self.u.first_name, "Al")

    def test_profile_cannot_change_role(self):
        self.client.post(reverse("accounts:account"), {"first_name": "A", "last_name": "B", "email": "a@b.co", "phone": "", "role": "admin"})
        self.u.refresh_from_db()
        self.assertEqual(self.u.role, User.Role.CUSTOMER)

    def test_add_edit_delete_address(self):
        payload = {"label": "Home", "full_name": "Alice", "phone": "9876543210", "line1": "1 Road", "line2": "", "city": "Pune", "state": "MH", "postal_code": "411001"}
        self.client.post(reverse("accounts:address_add"), payload)
        a = Address.objects.get(user=self.u)
        self.assertTrue(a.is_default)  # first address becomes default
        self.client.post(reverse("accounts:address_edit", args=[a.pk]), {**payload, "city": "Nagpur"})
        a.refresh_from_db()
        self.assertEqual(a.city, "Nagpur")
        self.client.post(reverse("accounts:address_delete", args=[a.pk]))
        self.assertFalse(Address.objects.filter(pk=a.pk).exists())

    def test_invalid_pin_code_rejected(self):
        payload = {"label": "H", "full_name": "A", "phone": "9876543210", "line1": "1", "city": "P", "state": "M", "postal_code": "12"}
        r = self.client.post(reverse("accounts:address_add"), payload)
        self.assertContains(r, "valid 6-digit PIN")

    def test_cannot_touch_another_users_address(self):
        theirs = make_address(self.other)
        self.assertEqual(self.client.get(reverse("accounts:address_edit", args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("accounts:address_delete", args=[theirs.pk])).status_code, 404)
        self.assertTrue(Address.objects.filter(pk=theirs.pk).exists())


@mock.patch("catalog.demo_images.render", fast_render)
class SeedCommandTests(NovaTestCase):
    def run_seed(self, *args):
        out = StringIO()
        call_command("seed_demo_data", *args, stdout=out)
        return out.getvalue()

    def test_all_ten_demo_customers_and_admin_can_log_in(self):
        self.run_seed("--with-demo-users", "--skip-orders")
        self.assertEqual(len(DEMO_CUSTOMERS), 10)
        for username, password, *_ in DEMO_CUSTOMERS:
            self.assertTrue(self.client.login(username=username, password=password), username)
            self.client.logout()
        self.assertTrue(self.client.login(username=DEMO_ADMIN[0], password=DEMO_ADMIN[1]))

    def test_niraj_dalal_with_1234_works_and_is_customer(self):
        self.run_seed("--with-demo-users", "--skip-orders")
        r = self.client.post(reverse("accounts:login"), {"username": "niraj_dalal", "password": "1234"})
        self.assertRedirects(r, reverse("catalog:home"))
        self.assertEqual(User.objects.get(username="niraj_dalal").role, User.Role.CUSTOMER)

    def test_admin_demo_account_reaches_dashboard(self):
        self.run_seed("--with-demo-users", "--skip-orders")
        r = self.client.post(reverse("accounts:login"), {"username": "novamart_admin", "password": "NovaAdmin@2026!"})
        self.assertRedirects(r, reverse("dashboard:home"))
        admin = User.objects.get(username="novamart_admin")
        self.assertTrue(admin.is_staff and admin.is_superuser)

    def test_passwords_never_stored_in_plaintext(self):
        self.run_seed("--with-demo-users", "--skip-orders")
        for u in User.objects.all():
            self.assertNotIn(u.password, [c[1] for c in DEMO_CUSTOMERS] + [DEMO_ADMIN[1]])
            self.assertIn("$", u.password)

    def test_seed_is_idempotent(self):
        from catalog.models import Category, Product
        from orders.models import Order
        self.run_seed("--with-demo-users")
        counts = (User.objects.count(), Category.objects.count(), Product.objects.count(), Order.objects.count())
        self.run_seed("--with-demo-users")
        self.assertEqual(counts, (User.objects.count(), Category.objects.count(), Product.objects.count(), Order.objects.count()))
        self.assertGreaterEqual(Product.objects.count(), 24)
        self.assertGreaterEqual(Category.objects.count(), 6)
        self.assertEqual(User.objects.filter(role=User.Role.CUSTOMER).count(), 10)

    def test_every_seeded_product_has_a_real_image_file(self):
        from catalog.models import Product
        self.run_seed("--skip-orders")
        for p in Product.objects.all():
            self.assertTrue(p.image and p.image.storage.exists(p.image.name), p.name)

    @override_settings(ALLOW_DEMO_ACCOUNTS=False)
    def test_refuses_to_create_demo_accounts_when_not_allowed(self):
        with self.assertRaises(CommandError):
            self.run_seed("--with-demo-users")
        self.assertFalse(User.objects.filter(username="niraj_dalal").exists())
