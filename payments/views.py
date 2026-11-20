import json

from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from support.emails import absolute_url

from . import services
from .models import Payment, PaymentGateway


@csrf_exempt  # called by PayHero's servers; protected by the secret token in the URL AND by re-checking the status with PayHero
@require_POST
def payhero_callback(request, token):
    gateway = get_object_or_404(PaymentGateway, callback_token=token)
    try:
        payload = json.loads(request.body[:20000] or b"{}")
        resp = payload.get("response") or {}
    except (ValueError, AttributeError):
        return HttpResponseBadRequest("bad json")
    payment = Payment.objects.filter(reference=str(resp.get("ExternalReference", "")), gateway=gateway).select_related("order").first()
    if payment and payment.status == "pending":
        payment.raw = {**payment.raw, "callback": payload}
        payment.checkout_request_id = str(resp.get("CheckoutRequestID") or payment.checkout_request_id)
        paid_claim = str(resp.get("Status", "")).lower() == "success"
        try:
            amount_ok = services.whole_shillings(resp.get("Amount", 0)) >= services.whole_shillings(payment.amount)
        except Exception:  # noqa: BLE001
            amount_ok = False
        if paid_claim and not amount_ok:
            payment.message = "Callback amount does not match the order. Check this payment manually."
            payment.save(update_fields=["raw", "checkout_request_id", "message", "updated"])
        else:
            payment.save(update_fields=["raw", "checkout_request_id", "updated"])
            services.refresh_payment(payment, receipt_hint=str(resp.get("MpesaReceiptNumber", "")),
                                     order_url=absolute_url(request, payment.order.get_absolute_url()))
    return JsonResponse({"ok": True})
