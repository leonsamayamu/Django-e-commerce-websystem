import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Category, Order, Product, ProductImage

TMP_MEDIA = tempfile.mkdtemp()


def image_file(name="a.jpg", size=(1000, 800), fmt="JPEG", color="red"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ProductPhotoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.cat = Category.objects.create(name="Shoes")
        self.staff = User.objects.create_user("staff", "s@x.com", "pw-Staff-123", is_staff=True)
        self.customer = User.objects.create_user("cust", "c@x.com", "pw-Cust-123")

    def payload(self, **extra):
        data = {"category": self.cat.pk, "name": "Shoe", "description": "d", "price": "10.00", "stock": 5,
                "available": "on", "image_url": ""}
        data.update(extra)
        return data

    def test_staff_uploads_multiple_photos_and_they_are_optimised(self):
        self.client.force_login(self.staff)
        r = self.client.post(reverse("staff_product_new"),
                             self.payload(new_images=[image_file("a.jpg", (3000, 2000)), image_file("b.jpg")]))
        self.assertEqual(r.status_code, 302)
        product = Product.objects.get()
        photos = list(product.images.all())
        self.assertEqual([p.position for p in photos], [0, 1])
        with Image.open(photos[0].image.path) as im:
            self.assertLessEqual(max(im.size), 1600)  # downscaled
        self.assertEqual(len(product.image_urls()), 2)

    def test_rejects_non_image_wrong_extension_and_too_many(self):
        self.client.force_login(self.staff)
        bad = SimpleUploadedFile("evil.jpg", b"<?php echo 1; ?>", content_type="image/jpeg")
        r = self.client.post(reverse("staff_product_new"), self.payload(new_images=[bad]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ProductImage.objects.count(), 0)
        gif = image_file("a.gif", fmt="GIF")
        r = self.client.post(reverse("staff_product_new"), self.payload(new_images=[gif]))
        self.assertEqual(Product.objects.count(), 0)
        many = [image_file(f"{i}.jpg", (50, 50)) for i in range(9)]
        r = self.client.post(reverse("staff_product_new"), self.payload(new_images=many))
        self.assertEqual(Product.objects.count(), 0)

    def test_cover_selection_and_delete(self):
        p = Product.objects.create(category=self.cat, name="X", price=1, stock=1)
        a = ProductImage.objects.create(product=p, image=image_file(), position=0)
        b = ProductImage.objects.create(product=p, image=image_file(), position=1)
        self.client.force_login(self.staff)
        self.client.post(reverse("staff_product_edit", args=[p.pk]), self.payload(name="X", cover=b.pk))
        self.assertEqual(list(p.images.values_list("pk", flat=True)), [b.pk, a.pk])
        self.client.post(reverse("staff_product_edit", args=[p.pk]), self.payload(name="X", delete_images=[a.pk]))
        self.assertEqual(p.images.count(), 1)

    def test_cannot_delete_other_products_photos(self):
        p1 = Product.objects.create(category=self.cat, name="One", price=1, stock=1)
        p2 = Product.objects.create(category=self.cat, name="Two", price=1, stock=1)
        other = ProductImage.objects.create(product=p2, image=image_file())
        self.client.force_login(self.staff)
        self.client.post(reverse("staff_product_edit", args=[p1.pk]), self.payload(name="One", delete_images=[other.pk]))
        self.assertTrue(ProductImage.objects.filter(pk=other.pk).exists())

    def test_landing_page_exposes_all_photos_for_slider(self):
        p = Product.objects.create(category=self.cat, name="Slide", price=1, stock=1)
        for i in range(3):
            ProductImage.objects.create(product=p, image=image_file(), position=i)
        r = self.client.get(reverse("product_list"))
        self.assertContains(r, 'class="slide-btn next"')
        self.assertContains(self.client.get(reverse("product_detail", args=[p.pk])), 'data-src=', count=3)

    def test_placeholder_when_no_photo(self):
        p = Product.objects.create(category=self.cat, name="Bare", price=1, stock=1)
        self.assertIn("placeholder.svg", p.cover_url)


class AccessControlTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user("cust", "c@x.com", "pw-Cust-123")
        self.staff = User.objects.create_user("staff", "s@x.com", "pw-Staff-123", is_staff=True)

    def test_staff_area_permissions(self):
        urls = ["staff_dashboard", "staff_orders", "staff_products", "staff_messages", "staff_contacts",
                "staff_subscribers", "staff_newsletter"]
        for name in urls:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302, name)  # anonymous -> login
        self.client.force_login(self.customer)
        for name in urls:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        self.client.force_login(self.staff)
        for name in urls:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_checkout_works_for_customers_and_decrements_stock(self):
        cat = Category.objects.create(name="C")
        p = Product.objects.create(category=cat, name="P", price="5.00", stock=3)
        self.client.force_login(self.customer)
        self.client.post(reverse("cart_add", args=[p.pk]), {"quantity": 2})
        r = self.client.post(reverse("checkout"), {"name": "C", "email": "c@x.com", "phone": "0712345678",
                                                   "address": "Nairobi", "payment_method": "cod"})
        p.refresh_from_db()
        self.assertEqual(p.stock, 1)
        order = Order.objects.get()
        self.assertEqual(order.user, self.customer)
        self.assertEqual(r["Location"], order.get_absolute_url() + "?placed=1")


class TemplateWiringTests(TestCase):
    """Regression: Django admin ships its own registration/* templates; ours must win."""

    def test_auth_pages_use_shop_design(self):
        for name in ["login", "register", "password_reset", "password_reset_done", "password_reset_complete"]:
            self.assertContains(self.client.get(reverse(name)), "store/tailwind.css", msg_prefix=name)

    def test_admin_uses_unfold_theme_and_dashboard(self):
        admin = User.objects.create_superuser("root", "r@x.com", "pw-Root-12345")
        self.client.force_login(admin)
        r = self.client.get("/admin/")
        self.assertContains(r, "unfold")  # theme assets
        self.assertContains(r, "Active subscribers")  # dashboard cards from config.dashboard
        self.assertContains(r, "Sales, last 7 days")

    def test_every_admin_changelist_renders(self):
        admin = User.objects.create_superuser("root", "r@x.com", "pw-Root-12345")
        self.client.force_login(admin)
        for model in ["store/product", "store/category", "store/order", "store/productviewdaily", "auth/user", "auth/group",
                      "accounts/profile", "support/thread", "support/contactmessage", "support/subscriber", "support/newsletter",
                      "store/productreview", "payments/payment", "payments/paymentgateway", "assistant/assistantsettings",
                      "assistant/assistantcommand", "content/aboutsection", "content/aboutphoto", "content/aboutpage",
                      "content/storesettings"]:
            self.assertEqual(self.client.get(f"/admin/{model}/").status_code, 200, model)
        self.assertEqual(self.client.get("/admin/store/product/add/").status_code, 200)
        self.assertEqual(self.client.get(f"/admin/auth/user/{admin.pk}/change/").status_code, 200)
