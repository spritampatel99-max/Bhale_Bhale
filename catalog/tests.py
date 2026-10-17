from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from catalog.forms import ProductForm
from catalog.models import Category, Product
from catalog.utils import format_inr
from tests.helpers import NovaTestCase, make_category, make_product, png_upload
from decimal import Decimal


class ListingTests(NovaTestCase):
    def setUp(self):
        self.elec = make_category("Electronics")
        self.fash = make_category("Fashion")
        self.a = make_product("Blue Headphones", "3000", 5, self.elec, description="wireless audio")
        self.b = make_product("Red Shirt", "500", 5, self.fash)
        self.c = make_product("Green Speaker", "1500", 0, self.elec)

    def names(self, response):
        return [p.name for p in response.context["page"]]

    def test_home_and_list_render(self):
        self.assertEqual(self.client.get(reverse("catalog:home")).status_code, 200)
        r = self.client.get(reverse("catalog:list"))
        self.assertEqual(set(self.names(r)), {"Blue Headphones", "Red Shirt", "Green Speaker"})

    def test_search_matches_name_and_description(self):
        self.assertEqual(self.names(self.client.get(reverse("catalog:list"), {"q": "shirt"})), ["Red Shirt"])
        self.assertEqual(self.names(self.client.get(reverse("catalog:list"), {"q": "wireless"})), ["Blue Headphones"])
        self.assertEqual(self.names(self.client.get(reverse("catalog:list"), {"q": "zzzz"})), [])

    def test_search_input_is_escaped(self):
        r = self.client.get(reverse("catalog:list"), {"q": "<script>alert(1)</script>"})
        self.assertNotContains(r, "<script>alert(1)</script>")

    def test_category_page_and_query_filter(self):
        r = self.client.get(reverse("catalog:category", args=[self.elec.slug]))
        self.assertEqual(set(self.names(r)), {"Blue Headphones", "Green Speaker"})
        r = self.client.get(reverse("catalog:list"), {"category": "fashion"})
        self.assertEqual(self.names(r), ["Red Shirt"])

    def test_price_filter(self):
        r = self.client.get(reverse("catalog:list"), {"min_price": "1000", "max_price": "2000"})
        self.assertEqual(self.names(r), ["Green Speaker"])
        r = self.client.get(reverse("catalog:list"), {"min_price": "abc", "max_price": "-5"})  # ignored safely
        self.assertEqual(len(self.names(r)), 3)

    def test_in_stock_filter(self):
        r = self.client.get(reverse("catalog:list"), {"in_stock": "1"})
        self.assertNotIn("Green Speaker", self.names(r))

    def test_sorting(self):
        self.assertEqual(self.names(self.client.get(reverse("catalog:list"), {"sort": "price_asc"})), ["Red Shirt", "Green Speaker", "Blue Headphones"])
        self.assertEqual(self.names(self.client.get(reverse("catalog:list"), {"sort": "price_desc"}))[0], "Blue Headphones")
        self.assertEqual(self.names(self.client.get(reverse("catalog:list"), {"sort": "bogus"}))[0], "Green Speaker")  # falls back to newest

    def test_sort_by_popularity_uses_orders(self):
        from tests.helpers import make_customer, make_order
        make_order(make_customer(), [(self.b, 5, None)])
        self.assertEqual(self.names(self.client.get(reverse("catalog:list"), {"sort": "popular"}))[0], "Red Shirt")

    def test_pagination(self):
        for i in range(14):
            make_product(f"Extra {i}", "10", 1, self.fash)
        r = self.client.get(reverse("catalog:list"))
        self.assertEqual(len(r.context["page"]), 12)
        self.assertTrue(r.context["page"].has_next())
        r2 = self.client.get(reverse("catalog:list"), {"page": 2})
        self.assertEqual(len(r2.context["page"]), 5)
        self.assertEqual(self.client.get(reverse("catalog:list"), {"page": "junk"}).status_code, 200)

    def test_inactive_products_and_categories_hidden(self):
        self.a.is_active = False
        self.a.save()
        self.assertNotIn("Blue Headphones", self.names(self.client.get(reverse("catalog:list"))))
        self.assertEqual(self.client.get(self.a.get_absolute_url()).status_code, 404)
        self.fash.is_active = False
        self.fash.save()
        self.assertEqual(self.client.get(reverse("catalog:category", args=[self.fash.slug])).status_code, 404)
        self.assertNotIn("Red Shirt", self.names(self.client.get(reverse("catalog:list"))))

    def test_empty_results_show_empty_state(self):
        self.assertContains(self.client.get(reverse("catalog:list"), {"q": "nothing-here"}), "Nothing matched")


class DetailTests(NovaTestCase):
    def test_detail_shows_stock_discount_related_breadcrumb(self):
        cat = make_category("Home")
        p = make_product("Lamp", "800", 3, cat, original_price=Decimal("1000"))
        make_product("Clock", "300", 3, cat)
        r = self.client.get(p.get_absolute_url())
        self.assertContains(r, "Lamp")
        self.assertContains(r, "20% off")
        self.assertContains(r, "Only 3 left")
        self.assertContains(r, "Breadcrumb")
        self.assertEqual([x.name for x in r.context["related"]], ["Clock"])

    def test_out_of_stock_detail_has_no_add_form(self):
        p = make_product("Gone", "10", 0)
        r = self.client.get(p.get_absolute_url())
        self.assertContains(r, "Out of stock")
        self.assertNotContains(r, "data-cart-add")

    def test_unknown_slug_is_404(self):
        self.assertEqual(self.client.get("/products/nope/").status_code, 404)


class ModelTests(NovaTestCase):
    def test_slug_and_sku_generated_and_unique(self):
        a = make_product("Same Name")
        b = make_product("Same Name")
        self.assertNotEqual(a.slug, b.slug)
        self.assertTrue(a.sku.startswith("NM-"))
        self.assertNotEqual(a.sku, b.sku)

    def test_discount_math(self):
        p = make_product("D", "750", 1, original_price=Decimal("1000"))
        self.assertTrue(p.has_discount)
        self.assertEqual(p.discount_percent, 25)
        self.assertFalse(make_product("E", "10", 1).has_discount)

    def test_original_price_below_price_invalid(self):
        from django.core.exceptions import ValidationError
        p = Product(category=make_category(), name="X", price=Decimal("100"), original_price=Decimal("50"))
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_money_uses_decimal_and_indian_grouping(self):
        self.assertEqual(format_inr(Decimal("1234567.5")), "\u20b912,34,567.50")
        self.assertEqual(format_inr(Decimal("999")), "\u20b9999.00")

    def test_negative_or_zero_price_rejected_by_database(self):
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(category=make_category(), name="Bad", price=Decimal("0"))


class ImageTests(NovaTestCase):
    def form(self, upload, **extra):
        data = {"name": "Img", "category": make_category().pk, "price": "10", "stock": "1", "is_active": "on"}
        data.update(extra)
        return ProductForm(data, {"image": upload} if upload else {})

    def test_valid_png_accepted_and_saved_with_safe_name(self):
        f = self.form(png_upload("../../evil name.png"))
        self.assertTrue(f.is_valid(), f.errors)
        p = f.save()
        self.assertTrue(p.image.name.startswith("products/"))
        self.assertNotIn("evil", p.image.name)
        self.assertTrue(p.image.storage.exists(p.image.name))

    def test_non_image_rejected(self):
        bad = SimpleUploadedFile("x.png", b"this is not an image", content_type="image/png")
        self.assertFalse(self.form(bad).is_valid())

    def test_executable_extension_rejected(self):
        up = png_upload("shell.php")
        f = self.form(up)
        self.assertFalse(f.is_valid())
        self.assertIn("image", f.errors)

    def test_oversize_rejected(self):
        with override_settings(MAX_IMAGE_UPLOAD_BYTES=100):
            f = self.form(png_upload(size=(200, 200)))
            self.assertFalse(f.is_valid())
            self.assertIn("too large", str(f.errors))

    def test_missing_image_uses_fallback(self):
        p = make_product("NoImg")
        self.assertIn("placeholders/product.svg", p.image_url)
        r = self.client.get(reverse("catalog:list"))
        self.assertContains(r, "placeholders/product.svg")

    def test_deleted_file_does_not_crash_page(self):
        f = self.form(png_upload())
        p = f.save()
        p.image.storage.delete(p.image.name)  # file vanishes from disk
        self.assertIn("placeholders/product.svg", p.image_url)
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 200)


class DemoImageGeneratorTests(NovaTestCase):
    def test_generator_returns_valid_jpegs_for_every_shape(self):
        import io
        from PIL import Image
        from catalog import demo_images
        palette = ("#E8EEF9", "#C9D6F0", "#2F6BFF", "#FFB81C", "#0B1B33", "#FFFFFF")
        for shape in demo_images.SHAPES:
            img = Image.open(io.BytesIO(demo_images.render(shape, palette, size=64)))
            self.assertEqual(img.format, "JPEG", shape)
