import json
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from panel.forms import GatewayForm
from payments import payhero, services
from payments.models import Payment, PaymentGateway
from store.models import Category, Order, OrderItem, Product

PW = "Tr0ub4dor&3-xyz"
CHECKOUT = {"name": "Grace", "email": "grace@x.com", "phone": "0712345678", "address": "Nairobi", "payment_method": "payhero"}


def make_gateway(**kw):
    g = PaymentGateway(name=kw.pop("name", "M-Pesa"), channel_id=kw.pop("channel_id", 911), **kw)
    g.set_credentials("api-user", "api-secret-pass")
    g.save()
    return g


class PayHeroBase(TestCase):
    def setUp(self):
        self.gateway = make_gateway()
        cat = Category.objects.create(name="C")
        self.product = Product.objects.create(category=cat, name="Lamp", price="1500.00", stock=5)
        self.calls = []

    def api(self, *responses):
        """Patch the HTTP layer; each call returns the next response (or raises it if it is an exception)."""
        queue = list(responses)

        def fake(method, url, *, headers, body=None):
            self.calls.append({"method": method, "url": url, "headers": headers, "body": body})
            item = queue.pop(0) if len(queue) > 1 else queue[0]
            if isinstance(item, Exception):
                raise item
            return item
        return mock.patch("payments.payhero.http_json", side_effect=fake)

    def buy(self, **extra):
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 1})
        return self.client.post(reverse("checkout"), {**CHECKOUT, "gateway": self.gateway.pk, **extra})

    QUEUED = {"success": True, "status": "QUEUED", "reference": "PH-REF-1", "CheckoutRequestID": "ws_CO_1"}


class PhoneAndCredentialTests(PayHeroBase):
    def test_normalize_phone(self):
        for raw in ("0712345678", "+254 712 345 678", "254712345678", "712345678", "0112345678"):
            self.assertIn(payhero.normalize_phone(raw), ("254712345678", "254112345678"), raw)
        for bad in ("", "12345", "0612345678", "abc", "+1 555 123 4567"):
            self.assertIsNone(payhero.normalize_phone(bad), bad)

    def test_credentials_are_encrypted_and_write_only(self):
        g = PaymentGateway.objects.get(pk=self.gateway.pk)
        self.assertNotIn("api-secret-pass", g.password_enc)
        self.assertNotIn("api-user", g.username_enc)
        self.assertEqual((g.api_username, g.api_password), ("api-user", "api-secret-pass"))
        self.assertEqual(g.masked_username, "api*****")

    def test_edit_without_new_secret_keeps_existing_one(self):
        form = GatewayForm({"name": "Renamed", "provider": "payhero_mpesa", "channel_id": 911, "enabled": "on", "position": 0},
                           instance=self.gateway)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.gateway.refresh_from_db()
        self.assertEqual((self.gateway.name, self.gateway.api_password), ("Renamed", "api-secret-pass"))
        new = GatewayForm({"name": "New", "provider": "payhero_mpesa", "channel_id": 5, "enabled": "on", "position": 0})
        self.assertFalse(new.is_valid())  # credentials are required when creating

    def test_secrets_never_appear_in_the_panel_pages(self):
        admin = User.objects.create_superuser("boss", "b@x.com", PW)
        self.client.force_login(admin)
        for url in (reverse("staff_gateways"), reverse("staff_gateway_edit", args=[self.gateway.pk])):
            body = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest").content.decode()
            self.assertNotIn("api-secret-pass", body)
            self.assertNotIn("api-user", body)
            self.assertNotIn(self.gateway.password_enc, body)
        self.assertContains(self.client.get("/admin/payments/paymentgateway/%d/change/" % self.gateway.pk), "Channel id")
        self.assertNotContains(self.client.get("/admin/payments/paymentgateway/%d/change/" % self.gateway.pk), self.gateway.password_enc)


class StkPushTests(PayHeroBase):
    def test_checkout_sends_a_correct_stk_push_request(self):
        with self.api(self.QUEUED):
            r = self.buy()
        order = Order.objects.get()
        self.assertEqual(r["Location"], reverse("order_pay_wait", args=[order.token]))
        call = self.calls[0]
        self.assertEqual((call["method"], call["url"]), ("POST", "https://backend.payhero.co.ke/api/v2/payments"))
        import base64
        self.assertEqual(call["headers"]["Authorization"], "Basic " + base64.b64encode(b"api-user:api-secret-pass").decode())
        body = call["body"]
        self.assertEqual((body["amount"], body["phone_number"], body["channel_id"], body["provider"]), (1500, "254712345678", 911, "m-pesa"))
        self.assertTrue(body["external_reference"].startswith(f"{order.pk}-"))
        self.assertIn(f"/payments/payhero/callback/{self.gateway.callback_token}/", body["callback_url"])
        p = Payment.objects.get()
        self.assertEqual((p.status, p.provider_reference, p.phone), ("pending", "PH-REF-1", "254712345678"))
        self.assertFalse(order.paid)

    def test_wallet_gateway_sends_sasapay_provider(self):
        wallet = make_gateway(name="Wallet", channel_id=77, provider="payhero_wallet")
        with self.api(self.QUEUED):
            self.buy(gateway=wallet.pk)
        self.assertEqual(self.calls[0]["body"]["provider"], "sasapay")
        self.assertEqual(self.calls[0]["body"]["network_code"], "63902")

    def test_api_failure_keeps_the_order_and_records_the_error(self):
        with self.api(payhero.PayHeroError("Could not reach PayHero: timeout")):
            self.buy()
        order, payment = Order.objects.get(), Payment.objects.get()
        self.assertEqual(payment.status, "failed")
        self.assertIn("Could not reach PayHero", payment.message)
        self.assertEqual(order.items.count(), 1)  # nothing lost; customer can retry from the order page
        page = self.client.get(order.get_absolute_url())
        self.assertContains(page, "Complete your payment")

    def test_invalid_mpesa_number_blocks_checkout(self):
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 1})
        r = self.client.post(reverse("checkout"), {**CHECKOUT, "phone": "0712345678", "mpesa_phone": "12345", "gateway": self.gateway.pk}, follow=True)
        self.assertContains(r, "valid M-Pesa number")
        self.assertEqual(Order.objects.count(), 0)

    def test_gateway_without_credentials_or_disabled_is_not_offered(self):
        self.gateway.enabled = False
        self.gateway.save()
        make_gateway(name="Broken").__class__.objects.filter(name="Broken").update(password_enc="")
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"quantity": 1})
        page = self.client.get(reverse("checkout"))
        self.assertNotContains(page, "Pay now with M-Pesa")
        self.assertContains(page, "Pay on delivery")


class VerificationTests(PayHeroBase):
    def place(self):
        with self.api(self.QUEUED):
            self.buy()
        return Order.objects.get(), Payment.objects.get()

    def test_polling_confirms_payment_with_payhero_and_marks_order_paid(self):
        order, payment = self.place()
        with self.api({"status": "SUCCESS", "reference": "PH-REF-1"}), self.captureOnCommitCallbacks(execute=True):
            data = self.client.get(reverse("order_pay_status", args=[order.token])).json()
        self.assertEqual((data["status"], data["paid"]), ("success", True))
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.status, "processing")  # paid orders move on automatically
        self.assertEqual(payment.status, "success")
        self.assertEqual(self.calls[-1]["url"], "https://backend.payhero.co.ke/api/v2/transaction-status?reference=PH-REF-1")
        self.assertTrue(any("Payment received" in m.subject for m in mail.outbox))

    def test_still_queued_stays_pending_and_failed_is_recorded(self):
        order, payment = self.place()
        with self.api({"status": "QUEUED"}):
            self.assertEqual(self.client.get(reverse("order_pay_status", args=[order.token])).json()["status"], "pending")
        with self.api({"status": "FAILED"}):
            self.assertEqual(self.client.get(reverse("order_pay_status", args=[order.token])).json()["status"], "failed")
        order.refresh_from_db()
        self.assertFalse(order.paid)

    def test_status_check_outage_does_not_change_anything(self):
        order, payment = self.place()
        with self.api(payhero.PayHeroError("down")):
            self.assertEqual(self.client.get(reverse("order_pay_status", args=[order.token])).json()["status"], "pending")

    def callback(self, token, payment, status="Success", amount=1500):
        payload = {"forward_url": "", "status": True, "response": {
            "Amount": amount, "CheckoutRequestID": "ws_CO_1", "ExternalReference": payment.reference,
            "MpesaReceiptNumber": "QKL9ABC123", "ResultCode": 0, "ResultDesc": "ok", "Status": status}}
        return self.client.post(reverse("payhero_callback", args=[token]), json.dumps(payload), content_type="application/json")

    def test_callback_alone_is_never_trusted(self):
        order, payment = self.place()
        with self.api({"status": "QUEUED"}):  # PayHero itself says not paid yet
            self.assertEqual(self.callback(self.gateway.callback_token, payment).status_code, 200)
        order.refresh_from_db()
        self.assertFalse(order.paid)

    def test_verified_callback_marks_paid_once_with_receipt(self):
        order, payment = self.place()
        for _ in range(2):  # PayHero may call twice: must be idempotent
            with self.api({"status": "SUCCESS"}), self.captureOnCommitCallbacks(execute=True):
                self.callback(self.gateway.callback_token, payment)
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(payment.receipt, "QKL9ABC123")
        self.assertEqual(len([m for m in mail.outbox if "Payment received" in m.subject]), 1)

    def test_callback_with_wrong_token_or_amount_or_bad_body(self):
        order, payment = self.place()
        self.assertEqual(self.callback("not-a-real-token", payment).status_code, 404)
        with self.api({"status": "SUCCESS"}):
            self.callback(self.gateway.callback_token, payment, amount=10)  # claims success for KES 10
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertFalse(order.paid)
        self.assertIn("does not match", payment.message)
        bad = self.client.post(reverse("payhero_callback", args=[self.gateway.callback_token]), "{{{", content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.client.get(reverse("payhero_callback", args=[self.gateway.callback_token])).status_code, 405)

    def test_retry_from_order_page_after_failure(self):
        with self.api(payhero.PayHeroError("rejected")):
            self.buy()
        order = Order.objects.get()
        with self.api(self.QUEUED):
            r = self.client.post(reverse("order_pay", args=[order.token]), {"gateway": self.gateway.pk, "mpesa_phone": "0722000111"})
        self.assertEqual(r["Location"], reverse("order_pay_wait", args=[order.token]))
        self.assertEqual(order.payments.count(), 2)
        self.assertEqual(order.payments.first().phone, "254722000111")

    def test_staff_can_recheck_a_pending_payment(self):
        order, payment = self.place()
        manager = User.objects.create_user("m", "m@x.com", PW, is_staff=True)
        self.client.force_login(manager)
        with self.api({"status": "SUCCESS"}):
            self.client.post(reverse("staff_payment_recheck", args=[payment.pk]))
        order.refresh_from_db()
        self.assertTrue(order.paid)
