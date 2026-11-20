import io
import json
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from store.models import Category, Order, OrderItem, Product, ProductImage
from support.models import ContactMessage, Subscriber

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
TMP_MEDIA = tempfile.mkdtemp()
PW = "Tr0ub4dor&3-xyz"


def photo(name="p.jpg"):
    buf = io.BytesIO()
    Image.new("RGB", (600, 400), "teal").save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


class PanelBase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Shoes")
        self.super = User.objects.create_superuser("root", "root@x.com", PW)
        self.staff = User.objects.create_user("staff", "staff@x.com", PW, is_staff=True)
        self.staff2 = User.objects.create_user("staff2", "staff2@x.com", PW, is_staff=True)
        self.cust = User.objects.create_user("cust", "cust@x.com", PW)

    def login(self, user):
        self.client.force_login(user)

    def product(self, **kw):
        data = dict(category=self.cat, name="Shoe", price="10.00", stock=5)
        data.update(kw)
        return Product.objects.create(**data)


class PanelAccessTests(PanelBase):
    NAMES = ["staff_dashboard", "staff_orders", "staff_products", "staff_categories", "staff_users",
             "staff_product_new", "staff_category_new", "staff_user_new"]

    def test_anonymous_redirected_and_customers_forbidden(self):
        for n in self.NAMES:
            self.assertEqual(self.client.get(reverse(n)).status_code, 302, n)
        self.login(self.cust)
        for n in self.NAMES:
            self.assertEqual(self.client.get(reverse(n), **AJAX).status_code, 403, n)

    def test_staff_can_open_everything(self):
        self.login(self.staff)
        p = self.product()
        order = Order.objects.create(name="N", email="n@x.com", address="a")
        urls = [reverse(n) for n in self.NAMES] + [
            reverse("staff_product_edit", args=[p.pk]), reverse("staff_product_delete", args=[p.pk]),
            reverse("staff_order_detail", args=[order.pk]), reverse("staff_order_status", args=[order.pk])]
        for u in urls:
            self.assertEqual(self.client.get(u).status_code, 200, u)

    def test_sidebar_and_dashboard_render(self):
        self.login(self.staff)
        html = self.client.get(reverse("staff_dashboard")).content.decode()
        for label in ["Products", "Categories", "Orders", "Users", "Subscribers"]:
            self.assertIn(label, html)
        self.assertIn('id="modal"', html)


class ModalMechanicsTests(PanelBase):
    def test_ajax_get_returns_fragment_not_full_page(self):
        self.login(self.staff)
        r = self.client.get(reverse("staff_product_new"), **AJAX)
        self.assertContains(r, "data-modal-form")
        self.assertNotContains(r, "<html")
        full = self.client.get(reverse("staff_product_new"))
        self.assertContains(full, "<html")  # same URL works without JavaScript

    def test_invalid_post_rerenders_with_422_and_valid_returns_json(self):
        self.login(self.staff)
        bad = self.client.post(reverse("staff_product_new"), {"name": ""}, **AJAX)
        self.assertEqual(bad.status_code, 422)
        self.assertContains(bad, "This field is required", status_code=422)
        ok = self.client.post(reverse("staff_product_new"), {
            "category": self.cat.pk, "name": "Boot", "price": "12.50", "stock": 3, "available": "on",
            "new_images": [photo("a.jpg"), photo("b.jpg")]}, **AJAX)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(json.loads(ok.content), {"ok": True})
        self.assertEqual(Product.objects.get(name="Boot").images.count(), 2)

    def tearDown(self):
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)


ModalMechanicsTests = override_settings(MEDIA_ROOT=TMP_MEDIA)(ModalMechanicsTests)


class ProductAndCategoryCrudTests(PanelBase):
    def test_edit_product(self):
        self.login(self.staff)
        p = self.product()
        self.client.post(reverse("staff_product_edit", args=[p.pk]), {
            "category": self.cat.pk, "name": "Renamed", "price": "99.00", "stock": 1, "available": "on"}, **AJAX)
        p.refresh_from_db()
        self.assertEqual((p.name, str(p.price)), ("Renamed", "99.00"))

    def test_delete_product_without_orders(self):
        self.login(self.staff)
        p = self.product()
        r = self.client.post(reverse("staff_product_delete", args=[p.pk]), {}, **AJAX)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Product.objects.filter(pk=p.pk).exists())

    def test_product_in_past_order_is_hidden_not_deleted(self):
        self.login(self.staff)
        p = self.product()
        o = Order.objects.create(name="N", email="n@x.com", address="a")
        OrderItem.objects.create(order=o, product=p, price=p.price, quantity=1)
        self.client.post(reverse("staff_product_delete", args=[p.pk]), {}, **AJAX)
        p.refresh_from_db()
        self.assertFalse(p.available)

    def test_category_crud_and_protection(self):
        self.login(self.staff)
        self.client.post(reverse("staff_category_new"), {"name": "Bags"}, **AJAX)
        bags = Category.objects.get(name="Bags")
        self.client.post(reverse("staff_category_edit", args=[bags.pk]), {"name": "Backpacks"}, **AJAX)
        bags.refresh_from_db()
        self.assertEqual(bags.name, "Backpacks")
        dup = self.client.post(reverse("staff_category_new"), {"name": "Shoes"}, **AJAX)
        self.assertEqual(dup.status_code, 422)  # unique name enforced
        self.product()
        self.client.post(reverse("staff_category_delete", args=[self.cat.pk]), {}, **AJAX)
        self.assertTrue(Category.objects.filter(pk=self.cat.pk).exists())  # still has products
        self.client.post(reverse("staff_category_delete", args=[bags.pk]), {}, **AJAX)
        self.assertFalse(Category.objects.filter(pk=bags.pk).exists())


class UserCrudTests(PanelBase):
    def new_user(self, **extra):
        data = {"username": "newbie", "first_name": "New", "last_name": "B", "email": "newbie@x.com",
                "role": "customer", "password1": PW, "password2": PW, "is_active": "on"}
        data.update(extra)
        return self.client.post(reverse("staff_user_new"), data, **AJAX)

    def test_staff_creates_customer_but_not_staff(self):
        self.login(self.staff)
        self.assertEqual(self.new_user().status_code, 200)
        u = User.objects.get(username="newbie")
        self.assertFalse(u.is_staff)
        self.assertTrue(hasattr(u, "profile"))
        r = self.new_user(username="sneaky", email="s@x.com", role="staff")
        self.assertEqual(r.status_code, 422)  # staff role is not even an allowed choice
        self.assertFalse(User.objects.filter(username="sneaky").exists())

    def test_superuser_can_create_staff_with_role_but_never_superuser(self):
        self.login(self.super)
        self.assertEqual(self.new_user(role="staff", is_superuser="on").status_code, 422)  # a staff role is required
        self.new_user(role="staff", staff_role="warehouse", is_superuser="on")
        u = User.objects.get(username="newbie")
        self.assertTrue(u.is_staff)
        self.assertFalse(u.is_superuser)
        self.assertEqual(u.profile.staff_role, "warehouse")

    def test_weak_password_and_duplicate_email_rejected(self):
        self.login(self.staff)
        self.assertEqual(self.new_user(password1="12345", password2="12345").status_code, 422)
        self.assertEqual(self.new_user(email="CUST@x.com").status_code, 422)

    def test_staff_cannot_touch_other_staff_or_superusers(self):
        self.login(self.staff)
        for target in (self.staff2, self.super):
            for name in ("staff_user_edit", "staff_user_password", "staff_user_toggle"):
                self.assertEqual(self.client.get(reverse(name, args=[target.pk]), **AJAX).status_code, 403, name)

    def test_edit_customer_and_set_password(self):
        self.login(self.staff)
        self.client.post(reverse("staff_user_edit", args=[self.cust.pk]), {
            "first_name": "Changed", "last_name": "Name", "email": "cust@x.com", "role": "customer", "is_active": "on"}, **AJAX)
        self.cust.refresh_from_db()
        self.assertEqual(self.cust.first_name, "Changed")
        new = "Another-Str0ng-Pass!"
        self.client.post(reverse("staff_user_password", args=[self.cust.pk]), {"new_password1": new, "new_password2": new}, **AJAX)
        self.cust.refresh_from_db()
        self.assertTrue(self.cust.check_password(new))

    def test_cannot_deactivate_or_delete_yourself(self):
        self.login(self.super)
        self.assertEqual(self.client.get(reverse("staff_user_toggle", args=[self.super.pk]), **AJAX).status_code, 403)
        self.assertEqual(self.client.get(reverse("staff_user_delete", args=[self.super.pk]), **AJAX).status_code, 403)
        self.client.post(reverse("staff_user_edit", args=[self.super.pk]), {
            "first_name": "", "last_name": "", "email": "root@x.com", "role": "customer"}, **AJAX)
        self.super.refresh_from_db()
        self.assertTrue(self.super.is_superuser and self.super.is_active)

    def test_toggle_and_delete(self):
        self.login(self.staff)
        self.client.post(reverse("staff_user_toggle", args=[self.cust.pk]), {}, **AJAX)
        self.cust.refresh_from_db()
        self.assertFalse(self.cust.is_active)
        self.assertEqual(self.client.post(reverse("staff_user_delete", args=[self.cust.pk]), {}, **AJAX).status_code, 403)  # staff cannot delete
        self.login(self.super)
        self.client.post(reverse("staff_user_delete", args=[self.cust.pk]), {}, **AJAX)
        self.assertFalse(User.objects.filter(pk=self.cust.pk).exists())

    def test_user_list_search_and_filter(self):
        self.login(self.staff)
        self.assertContains(self.client.get(reverse("staff_users"), {"q": "cust"}), "cust@x.com")
        self.assertNotContains(self.client.get(reverse("staff_users"), {"role": "customers"}), "staff2@x.com")


class OrderStatusTests(PanelBase):
    def make_order(self):
        p = self.product(stock=5)
        o = Order.objects.create(name="N", email="n@x.com", address="a")
        OrderItem.objects.create(order=o, product=p, price=p.price, quantity=2)
        return p, o

    def test_cancel_restores_stock_and_reopen_takes_it_again(self):
        self.login(self.staff)
        p, o = self.make_order()
        url = reverse("staff_order_status", args=[o.pk])
        self.client.post(url, {"status": "cancelled"}, **AJAX)
        p.refresh_from_db()
        self.assertEqual(p.stock, 7)
        self.client.post(url, {"status": "processing"}, **AJAX)
        p.refresh_from_db()
        self.assertEqual(p.stock, 5)

    def test_cannot_reopen_without_stock(self):
        self.login(self.staff)
        p, o = self.make_order()
        url = reverse("staff_order_status", args=[o.pk])
        self.client.post(url, {"status": "cancelled"}, **AJAX)
        Product.objects.filter(pk=p.pk).update(stock=0)
        r = self.client.post(url, {"status": "pending"}, **AJAX)
        self.assertEqual(r.status_code, 422)
        o.refresh_from_db()
        self.assertEqual(o.status, "cancelled")

    def test_status_change_emails_customer(self):
        self.login(self.staff)
        _, o = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("staff_order_status", args=[o.pk]), {"status": "shipped", "paid": "on"}, **AJAX)
        self.assertEqual([m.to for m in mail.outbox], [["n@x.com"]])
        self.assertIn("shipped", mail.outbox[0].subject)


class SupportDeleteTests(PanelBase):
    def test_delete_inquiry_and_subscriber(self):
        self.login(self.staff)
        c = ContactMessage.objects.create(name="N", email="n@x.com", subject="S", message="M")
        s = Subscriber.objects.create(email="s@x.com")
        self.client.post(reverse("staff_contact_delete", args=[c.pk]), {}, **AJAX)
        self.client.post(reverse("staff_subscriber_delete", args=[s.pk]), {}, **AJAX)
        self.assertEqual((ContactMessage.objects.count(), Subscriber.objects.count()), (0, 0))
