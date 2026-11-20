"""Panel pages for payments, reviews, About content, store settings and the AI assistant."""
from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import capability_required
from assistant.models import AssistantCommand, AssistantSettings
from content.models import AboutPage, AboutPhoto, AboutSection, StoreSettings
from payments import services
from payments.models import Payment, PaymentGateway
from store.models import ProductReview
from support.emails import absolute_url

from .forms import (AboutPageForm, AboutPhotoForm, AboutPhotosUploadForm, AboutSectionForm, AssistantCommandForm,
                    AssistantSettingsForm, GatewayForm, StoreSettingsForm)
from .utils import ConfirmForm, confirm_delete, done, form_args, modal_form, paginate

GENERIC = "panel/forms/generic.html"


def _simple_form(request, form, *, title, back, subtitle="", submit="Save", ctx=None, msg="Saved.", save=None):
    """Create/edit pop-up for a plain ModelForm. `save` lets a form with extra logic do its own saving."""
    if request.method == "POST" and form.is_valid():
        (save or form.save)()
        return done(request, msg, to=reverse(back))
    return modal_form(request, form, title=title, subtitle=subtitle, partial=GENERIC, submit=submit,
                      cancel_url=reverse(back), ctx=ctx)


# ------------------------------------------------------------------ payment gateways (shop admins)
@capability_required("admin")
def gateways(request):
    rows = list(PaymentGateway.objects.annotate(n=Count("payments")))
    for g in rows:
        g.callback = absolute_url(request, reverse("payhero_callback", args=[g.callback_token]))
    return render(request, "panel/gateways.html", {"gateways": rows, "public_url_set": bool(settings.PUBLIC_BASE_URL)})


@capability_required("admin")
def gateway_new(request):
    return _simple_form(request, GatewayForm(*form_args(request)), title="Add payment gateway", back="staff_gateways",
                        subtitle="Connect a PayHero payment channel.", msg="Gateway added.")


@capability_required("admin")
def gateway_edit(request, pk):
    g = get_object_or_404(PaymentGateway, pk=pk)
    return _simple_form(request, GatewayForm(*form_args(request), instance=g), title="Edit payment gateway",
                        back="staff_gateways", subtitle=g.name, msg="Gateway updated.")


@capability_required("admin")
def gateway_delete(request, pk):
    g = get_object_or_404(PaymentGateway, pk=pk)
    return confirm_delete(request, g, title="Delete gateway?", back="staff_gateways", ok=f"Gateway '{g.name}' deleted.",
                          message=f"Delete '{g.name}'? Customers will no longer be able to pay with it. Past payment records are kept.")


# ------------------------------------------------------------------ transactions
@capability_required("payments_view")
def payments(request):
    qs = Payment.objects.select_related("order", "gateway")
    status, q = request.GET.get("status", ""), request.GET.get("q", "").strip()
    if status in dict(Payment.STATUS):
        qs = qs.filter(status=status)
    if q:
        cond = Q(reference__icontains=q) | Q(receipt__icontains=q) | Q(phone__icontains=q) | Q(order__name__icontains=q)
        qs = qs.filter(cond | Q(order_id=q)) if q.isdigit() else qs.filter(cond)
    page, query_string = paginate(request, qs, 25)
    return render(request, "panel/payments.html", {"page": page, "query_string": query_string, "status": status, "q": q,
                                                   "statuses": Payment.STATUS})


@capability_required("payments_view")
@require_POST
def payment_recheck(request, pk):
    from django.contrib import messages
    from django.shortcuts import redirect
    payment = get_object_or_404(Payment.objects.select_related("order", "gateway"), pk=pk)
    before = payment.status
    payment = services.refresh_payment(payment, order_url=absolute_url(request, payment.order.get_absolute_url()))
    messages.info(request, f"Payment {payment.reference}: {payment.get_status_display()}" +
                  ("" if payment.status != before else " (no change from PayHero yet)."))
    return redirect(request.POST.get("next") or "staff_payments")


# ------------------------------------------------------------------ reviews
@capability_required("reviews")
def reviews(request):
    state = request.GET.get("state", "")
    qs = ProductReview.objects.select_related("product", "user")
    if state == "hidden":
        qs = qs.filter(visible=False)
    elif state == "low":
        qs = qs.filter(rating__lte=2)
    page, query_string = paginate(request, qs, 20)
    return render(request, "panel/reviews.html", {"page": page, "query_string": query_string, "state": state})


@capability_required("reviews")
def review_toggle(request, pk):
    r = get_object_or_404(ProductReview, pk=pk)
    form = ConfirmForm(*form_args(request)[:1])
    action = "Hide" if r.visible else "Show"
    if request.method == "POST" and form.is_valid():
        r.visible = not r.visible
        r.save(update_fields=["visible"])
        return done(request, f"Review {'shown' if r.visible else 'hidden'}.", to=reverse("staff_reviews"))
    return modal_form(request, form, title=f"{action} review?", partial="panel/forms/confirm.html", submit=action,
                      cancel_url=reverse("staff_reviews"),
                      ctx={"message": f"{action} this review by {r.user.username} on '{r.product.name}'? "
                                      + ("Customers will no longer see it." if r.visible else "Customers will be able to see it again.")})


@capability_required("reviews")
def review_delete(request, pk):
    r = get_object_or_404(ProductReview, pk=pk)
    return confirm_delete(request, r, title="Delete review?", back="staff_reviews", ok="Review deleted.",
                          message=f"Permanently delete this review of '{r.product.name}'? Hiding it is usually enough.")


# ------------------------------------------------------------------ About page editor
@capability_required("content")
def about_admin(request):
    return render(request, "panel/about.html", {"page": AboutPage.load(), "sections": AboutSection.objects.all(),
                                                "photos": AboutPhoto.objects.all()})


@capability_required("content")
def about_edit(request):
    return _simple_form(request, AboutPageForm(*form_args(request), instance=AboutPage.load()), title="Edit About page text",
                        back="staff_about", msg="About page updated.")


@capability_required("content")
def section_new(request):
    return _simple_form(request, AboutSectionForm(*form_args(request)), title="Add section", back="staff_about", msg="Section added.")


@capability_required("content")
def section_edit(request, pk):
    s = get_object_or_404(AboutSection, pk=pk)
    return _simple_form(request, AboutSectionForm(*form_args(request), instance=s), title="Edit section", back="staff_about",
                        subtitle=s.heading, msg="Section updated.")


@capability_required("content")
def section_delete(request, pk):
    s = get_object_or_404(AboutSection, pk=pk)
    return confirm_delete(request, s, title="Delete section?", back="staff_about", ok="Section deleted.",
                          message=f"Delete the section '{s.heading}' from the About page?")


@capability_required("content")
def photo_upload(request):
    form = AboutPhotosUploadForm(*form_args(request))
    return _simple_form(request, form, title="Upload photos", back="staff_about", submit="Upload",
                        subtitle="Photos are stored in your database media and shown on the About page.", msg="Photos uploaded.")


@capability_required("content")
def photo_edit(request, pk):
    p = get_object_or_404(AboutPhoto, pk=pk)
    return _simple_form(request, AboutPhotoForm(*form_args(request), instance=p), title="Edit photo details", back="staff_about",
                        msg="Photo updated.", ctx={"preview": p})


@capability_required("content")
def photo_delete(request, pk):
    p = get_object_or_404(AboutPhoto, pk=pk)
    return confirm_delete(request, p, title="Delete photo?", back="staff_about", ok="Photo deleted.",
                          message="Remove this photo from the About page? The file is deleted too.")


# ------------------------------------------------------------------ store settings (invoice details, checkout switches)
@capability_required("admin")
def store_settings(request):
    return render(request, "panel/store_settings.html", {"cfg": StoreSettings.load()})


@capability_required("admin")
def store_settings_edit(request):
    return _simple_form(request, StoreSettingsForm(*form_args(request), instance=StoreSettings.load()), title="Store settings",
                        back="staff_settings", subtitle="Shown on invoices and used at checkout.", msg="Store settings saved.")


# ------------------------------------------------------------------ AI assistant (shop admins)
@capability_required("admin")
def assistant_admin(request):
    return render(request, "panel/assistant.html", {
        "cfg": AssistantSettings.load(), "commands": AssistantCommand.objects.all(),
        "key_set": bool(settings.ANTHROPIC_API_KEY), "model": settings.ASSISTANT_MODEL})


@capability_required("admin")
def assistant_edit(request):
    return _simple_form(request, AssistantSettingsForm(*form_args(request), instance=AssistantSettings.load()),
                        title="Assistant settings", back="staff_assistant", msg="Assistant settings saved.")


@capability_required("admin")
def command_new(request):
    return _simple_form(request, AssistantCommandForm(*form_args(request)), title="Add command", back="staff_assistant",
                        subtitle="Knowledge the assistant can use. It cannot see anything else.", msg="Command added.")


@capability_required("admin")
def command_edit(request, pk):
    c = get_object_or_404(AssistantCommand, pk=pk)
    return _simple_form(request, AssistantCommandForm(*form_args(request), instance=c), title="Edit command", back="staff_assistant",
                        subtitle=f"/{c.trigger}", msg="Command updated.")


@capability_required("admin")
def command_delete(request, pk):
    c = get_object_or_404(AssistantCommand, pk=pk)
    return confirm_delete(request, c, title="Delete command?", back="staff_assistant", ok=f"Command /{c.trigger} deleted.",
                          message=f"Delete /{c.trigger}? The assistant will stop knowing this information.")
