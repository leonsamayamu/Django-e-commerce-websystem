import secrets
from decimal import ROUND_UP, Decimal

from django.db import transaction
from django.urls import reverse

from support.emails import absolute_url, send_safely

from . import payhero
from .models import Payment


class PaymentError(Exception):
    """A problem the customer can fix (bad phone number...)."""


def start_payment(request, order, gateway, phone):
    """Create a Payment and send the M-Pesa prompt to the customer's phone."""
    number = payhero.normalize_phone(phone)
    if not number:
        raise PaymentError("Enter a valid Safaricom number, e.g. 0712 345 678.")
    if not gateway.enabled or not gateway.has_credentials:
        raise PaymentError("This payment method is not available right now.")
    payment = Payment.objects.create(
        order=order, gateway=gateway, amount=order.total(), phone=number,
        reference=f"{order.pk}-{secrets.token_hex(4).upper()}")
    callback = absolute_url(request, reverse("payhero_callback", args=[gateway.callback_token]))
    try:
        data = payhero.initiate_stk(gateway, amount=payment.amount, phone=number, reference=payment.reference,
                                    customer_name=order.name, callback_url=callback)
    except payhero.PayHeroError as exc:
        payment.status, payment.message = "failed", str(exc)[:250]
        payment.save(update_fields=["status", "message", "updated"])
        return payment
    payment.provider_reference = str(data.get("reference", ""))
    payment.checkout_request_id = str(data.get("CheckoutRequestID", ""))
    payment.raw = data
    payment.message = "Prompt sent. Enter your M-Pesa PIN on your phone."
    payment.save()
    return payment


def mark_success(payment, receipt="", raw=None, order_url=""):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("order").get(pk=payment.pk)
        if payment.status == "success":
            return payment
        payment.status, payment.receipt = "success", (receipt or payment.receipt)[:40]
        payment.message = "Payment received."
        if raw:
            payment.raw = raw
        payment.save()
        order = payment.order
        order.paid = True
        if order.status == "pending":
            order.status = "processing"
        order.save(update_fields=["paid", "status"])
        transaction.on_commit(lambda: send_safely(
            f"Payment received for order #{order.pk}",
            f"Hello {order.name},\n\nWe received your payment of KES {payment.amount} for order #{order.pk}"
            f"{' (M-Pesa receipt ' + payment.receipt + ')' if payment.receipt else ''}.\n"
            f"Track your order and download your invoice: {order_url or order.get_absolute_url()}\n\nThank you!",
            [order.email]))
    return payment


def mark_failed(payment, message="Payment was not completed."):
    if payment.status == "pending":
        payment.status, payment.message = "failed", message[:250]
        payment.save(update_fields=["status", "message", "updated"])
    return payment


def refresh_payment(payment, receipt_hint="", order_url=""):
    """Ask PayHero for the real status. We never mark an order paid from an unverified callback alone."""
    if payment.status != "pending" or not payment.provider_reference or not payment.gateway:
        return payment
    try:
        data = payhero.transaction_status(payment.gateway, payment.provider_reference)
    except payhero.PayHeroError:
        return payment  # try again on the next poll
    state = str(data.get("status", "")).upper()
    if state == "SUCCESS":
        return mark_success(payment, receipt=receipt_hint, raw={**payment.raw, "status_check": data}, order_url=order_url)
    if state == "FAILED":
        return mark_failed(payment, "The payment was cancelled or failed.")
    return payment


def whole_shillings(amount):
    return int(Decimal(amount).quantize(Decimal("1"), rounding=ROUND_UP))
