from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from content.models import StoreSettings
from panel.forms import OrderStatusForm
from store.invoices import build_pdf, invoice_data
from store.models import Category, Order, OrderItem, Product, ProductReview, ProductVariant

PW = "Tr0ub4dor&3-xyz"
GUEST = {"name": "Guest Gus", "email": "gus@x.com", "phone": "0700111222", "address": "Mombasa Rd", "payment_method": "cod"}


class ShopBase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Shoes")
        self.simple = Product.objects.create(category=self.cat, name="Cap", price="200.00", stock=4)
        self.shoe = Product.objects.create(category=self.cat, name="Shoe", price="1000.00", stock=0)
        self.v42 = ProductVariant.objects.create(product=self.shoe, name="Size 42", stock=3)
        self.v43 = ProductVariant.objects.create(product=self.shoe, name="Size 43", stock=2, price="1200.00")
        self.sold_out = ProductVariant.objects.create(product=self.shoe, name="Size 44", stock=0)
        self.cust = User.objects.create_user("cust", "cust@x.com", PW, first_name="Cust")

    def add(self, product, qty=1, **extra):
        return self.client.post(reverse("cart_add", args=[product.pk]), {"quantity": qty, **extra})

    def checkout(self, **extra):
        return self.client.post(reverse("checkout"), {**GUEST, **extra})


class VariantTests(ShopBase):
    def test_variant_products_need_an_option(self):
        r = self.client.post(reverse("cart_add", args=[self.shoe.pk]), {"quantity": 1}, follow=True)
        self.assertContains(r, "choose an option")
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_option_price_stock_and_totals(self):
        shoe = Product.objects.prefetch_related("variants").get(pk=self.shoe.pk)
        self.assertEqual((shoe.total_stock, shoe.lowest_price, shoe.price_varies), (5, 1000, True))
        self.add(self.shoe, 2, variant=self.v43.pk)
        page = self.client.get(reverse("cart")).content.decode()
        self.assertIn("Size 43", page)
        self.assertIn("2400", page)  # 2 x 1200 override price

    def test_cannot_add_sold_out_or_foreign_option(self):
        self.add(self.shoe, variant=self.sold_out.pk)
        other = ProductVariant.objects.create(product=self.simple, name="Hidden", stock=9)
        self.add(self.shoe, variant=other.pk)
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_quantity_is_capped_at_option_stock(self):
        self.add(self.shoe, 50, variant=self.v42.pk)
        self.assertEqual(list(self.client.session["cart"].values()), [3])

    def test_checkout_and_cancel_move_the_options_stock_not_the_products(self):
        self.add(self.shoe, 2, variant=self.v42.pk)
        self.checkout()
        self.v42.refresh_from_db()
        self.shoe.refresh_from_db()
        self.assertEqual((self.v42.stock, self.shoe.stock), (1, 0))
        order = Order.objects.get()
        item = order.items.get()
        self.assertEqual((item.variant, item.variant_name, item.product_name), (self.v42, "Size 42", "Shoe"))
        admin = User.objects.create_superuser("boss", "b@x.com", PW)
        form = OrderStatusForm({"status": "cancelled"}, instance=order, actor=admin)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.v42.refresh_from_db()
        self.assertEqual(self.v42.stock, 3)

    def test_list_shows_choose_options_and_from_price(self):
        html = self.client.get(reverse("product_list")).content.decode()
        self.assertIn("Choose options", html)
        self.assertIn("From", html)

    def test_legacy_session_cart_keys_still_work(self):
        s = self.client.session
        s["cart"] = {str(self.simple.pk): 2}
        s.save()
        self.assertContains(self.client.get(reverse("cart")), "Cap")

    def test_invoice_names_survive_renaming_the_product(self):
        self.add(self.shoe, variant=self.v42.pk)
        self.checkout()
        Product.objects.filter(pk=self.shoe.pk).update(name="Totally different")
        order = Order.objects.get()
        self.assertEqual(order.items.get().display_name, "Shoe (Size 42)")


class GuestCheckoutTests(ShopBase):
    def test_guest_can_buy_and_gets_a_private_order_link(self):
        self.add(self.simple, 2)
        r = self.checkout()
        order = Order.objects.get()
        self.assertIsNone(order.user)
        self.assertTrue(order.is_guest)
        self.assertEqual(r["Location"], order.get_absolute_url() + "?placed=1")
        self.assertEqual(len(order.token), 32)
        self.simple.refresh_from_db()
        self.assertEqual(self.simple.stock, 2)
        mails = [m for m in mail.outbox if m.to == ["gus@x.com"]]
        self.assertIn(order.token, mails[0].body)
        page = self.client.get(order.get_absolute_url())
        self.assertContains(page, "Guest Gus")
        self.assertEqual(self.client.get(reverse("order_view", args=["wrong-token"])).status_code, 404)

    def test_guest_checkout_can_be_switched_off(self):
        cfg = StoreSettings.load()
        cfg.guest_checkout = False
        cfg.save()
        self.add(self.simple)
        r = self.client.get(reverse("checkout"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_validation_messages(self):
        self.add(self.simple)
        r = self.checkout(email="not-an-email", phone="1", address="", payment_method="")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        self.assertContains(r, "valid email")
        self.assertContains(r, "phone number")
        self.assertContains(r, "delivery address")
        self.assertContains(r, "payment method")
        self.assertContains(r, "Guest Gus")  # entered values are kept

    def test_cash_on_delivery_can_be_disabled(self):
        cfg = StoreSettings.load()
        cfg.cod_enabled = False
        cfg.save()
        self.add(self.simple)
        r = self.checkout()
        self.assertEqual(Order.objects.count(), 0)
        self.assertContains(r, "not available")

    def test_cannot_oversell(self):
        self.add(self.simple, 4)
        Product.objects.filter(pk=self.simple.pk).update(stock=1)  # someone else bought it meanwhile
        self.checkout()
        self.assertEqual(Order.objects.count(), 0)

    def test_logged_in_customer_gets_order_in_my_orders(self):
        self.client.force_login(self.cust)
        self.add(self.simple)
        self.checkout()
        self.assertEqual(Order.objects.get().user, self.cust)
        self.assertContains(self.client.get(reverse("my_orders")), "Invoice PDF")


class InvoiceTests(ShopBase):
    def place(self, **cfg):
        c = StoreSettings.load()
        for k, v in cfg.items():
            setattr(c, k, v)
        c.save()
        self.add(self.simple, 2)
        self.checkout()
        return Order.objects.get()

    def test_html_invoice_by_private_link(self):
        order = self.place(business_name="Acme Ltd", tax_pin="P051234567Z", tax_rate="16.00", invoice_prefix="ACME-")
        page = self.client.get(reverse("invoice_view", args=[order.token]))
        self.assertContains(page, f"ACME-{order.pk:06d}")
        self.assertContains(page, "Acme Ltd")
        self.assertContains(page, "P051234567Z")
        self.assertContains(page, "UNPAID")
        data = invoice_data(order)
        self.assertEqual((data["total"], str(data["vat"]), str(data["net"])), (400, "55.17", "344.83"))  # 16% VAT included
        self.assertContains(page, "VAT 16")
        self.assertEqual(self.client.get(reverse("invoice_view", args=["nope"])).status_code, 404)

    def test_pdf_invoice(self):
        order = self.place(business_name="Acme Ltd")
        r = self.client.get(reverse("invoice_pdf", args=[order.token]))
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertIn(order.invoice_number, r["Content-Disposition"])
        self.assertGreater(len(build_pdf(order)), 1500)

    def test_pdf_handles_markup_characters_in_names(self):
        self.add(self.simple)
        self.checkout(name="<b>Bad & Co</b>", address="Line 1\nLine <2>")
        self.assertTrue(build_pdf(Order.objects.get()).startswith(b"%PDF"))

    def test_paid_invoice_shows_receipt(self):
        order = self.place()
        order.paid = True
        order.save()
        self.assertContains(self.client.get(reverse("invoice_view", args=[order.token])), "PAID")

    def test_staff_invoice_needs_invoice_capability(self):
        order = self.place()
        support = User.objects.create_user("s", "s@x.com", PW, is_staff=True)
        support.profile.staff_role = "support"
        support.profile.save()
        warehouse = User.objects.create_user("w", "w@x.com", PW, is_staff=True)
        warehouse.profile.staff_role = "warehouse"
        warehouse.profile.save()
        self.client.force_login(support)
        self.assertEqual(self.client.get(reverse("staff_order_invoice", args=[order.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("staff_order_invoice_pdf", args=[order.pk])).status_code, 200)
        self.client.force_login(warehouse)
        self.assertEqual(self.client.get(reverse("staff_order_invoice", args=[order.pk])).status_code, 403)


class ReviewTests(ShopBase):
    def review(self, product, **data):
        return self.client.post(reverse("review_submit", args=[product.pk]), data)

    def test_login_required(self):
        r = self.review(self.simple, rating=5)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])
        self.assertEqual(ProductReview.objects.count(), 0)

    def test_rating_is_validated_and_one_review_per_customer(self):
        self.client.force_login(self.cust)
        for bad in ("", "0", "6", "abc"):
            self.review(self.simple, rating=bad)
        self.assertEqual(ProductReview.objects.count(), 0)
        self.review(self.simple, rating=5, title="Great", comment="Loved it")
        self.review(self.simple, rating=3, title="Hmm", comment="Changed my mind")
        r = ProductReview.objects.get()
        self.assertEqual((r.rating, r.title), (3, "Hmm"))

    def test_average_verified_badge_and_escaping(self):
        other = User.objects.create_user("other", "o@x.com", PW)
        self.client.force_login(self.cust)
        self.add(self.simple)
        self.checkout()  # cust is now a verified buyer (order is linked to the account)
        self.review(self.simple, rating=5, comment="<script>alert(1)</script>")
        self.client.force_login(other)
        self.review(self.simple, rating=2)
        page = self.client.get(reverse("product_detail", args=[self.simple.pk])).content.decode()
        self.assertIn("3.5", page)
        self.assertIn("Verified purchase", page)
        self.assertEqual(page.count("Verified purchase"), 1)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("3.5", self.client.get(reverse("product_list")).content.decode())

    def test_hidden_reviews_disappear_and_staff_can_moderate(self):
        self.client.force_login(self.cust)
        self.review(self.simple, rating=1, comment="Terrible")
        r = ProductReview.objects.get()
        mod = User.objects.create_user("mod", "m@x.com", PW, is_staff=True)
        mod.profile.staff_role = "support"
        mod.profile.save()
        self.client.force_login(mod)
        self.client.post(reverse("staff_review_toggle", args=[r.pk]), {}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        r.refresh_from_db()
        self.assertFalse(r.visible)
        self.assertNotContains(self.client.get(reverse("product_detail", args=[self.simple.pk])), "Terrible")
        self.client.post(reverse("staff_review_delete", args=[r.pk]), {}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(ProductReview.objects.count(), 0)

    def test_customer_can_delete_own_review(self):
        self.client.force_login(self.cust)
        self.review(self.simple, rating=4)
        self.client.post(reverse("review_delete", args=[self.simple.pk]))
        self.assertEqual(ProductReview.objects.count(), 0)
