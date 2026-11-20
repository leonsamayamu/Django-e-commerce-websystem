import csv
from functools import reduce
from operator import or_

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.core.mail import EmailMessage, get_connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from django.urls import reverse

from accounts.decorators import capability_required
from panel.utils import ConfirmForm, done, form_args, modal_form, paginate

from .emails import unsubscribe_url
from .forms import NewsletterForm
from .models import ContactMessage, Newsletter, Subscriber, Thread
from .views import thread_response, unread_annotation


@capability_required("messages")
def messages_list(request):
    threads = Thread.objects.select_related("customer").annotate(unread=unread_annotation(True))
    if request.GET.get("unread"):
        threads = threads.filter(unread__gt=0)
    return render(request, "support/messages_staff.html", {"threads": threads, "only_unread": bool(request.GET.get("unread"))})


@capability_required("messages")
def thread_staff(request, pk):
    return thread_response(request, get_object_or_404(Thread, pk=pk), staff_mode=True)


@capability_required("inquiries")
def contacts(request):
    if request.method == "POST":
        obj = get_object_or_404(ContactMessage, pk=request.POST.get("id"))
        obj.handled = not obj.handled
        obj.save(update_fields=["handled"])
        return redirect("staff_contacts")
    return render(request, "support/contacts_staff.html", {"items": ContactMessage.objects.all()[:200]})


@capability_required("marketing")
def subscribers(request):
    qs = Subscriber.objects.all()
    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="subscribers.csv"'
        w = csv.writer(resp)
        w.writerow(["email", "active", "subscribed"])
        for s in qs:
            w.writerow([s.email, s.active, s.created.isoformat()])
        return resp
    status, q = request.GET.get("status", "active"), request.GET.get("q", "").strip()
    counts = {"active": qs.filter(active=True).count(), "inactive": qs.filter(active=False).count(), "all": qs.count()}
    if status == "active":
        qs = qs.filter(active=True)
    elif status == "inactive":
        qs = qs.filter(active=False)
    if q:
        qs = qs.filter(email__icontains=q)
    page, query_string = paginate(request, qs, 25)
    rows = list(page.object_list)
    accounts = {}
    if rows:  # match subscribers to customer accounts by email (case-insensitive)
        cond = reduce(or_, [Q(email__iexact=r.email) for r in rows])
        accounts = {u.email.lower(): u for u in User.objects.filter(cond)}
    for r in rows:
        r.account = accounts.get(r.email.lower())
    return render(request, "support/subscribers_staff.html", {
        "page": page, "rows": rows, "query_string": query_string, "status": status, "q": q, "counts": counts})


@capability_required("marketing")
def newsletter(request):
    form = NewsletterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        subject, body = form.cleaned_data["subject"], form.cleaned_data["body"]
        connection = get_connection()
        subs = list(Subscriber.objects.filter(active=True))
        mails = []
        for s in subs:
            url = unsubscribe_url(request, s)
            mails.append(EmailMessage(subject, f"{body}\n\n--\nUnsubscribe: {url}", settings.DEFAULT_FROM_EMAIL,
                                      [s.email], connection=connection, headers={"List-Unsubscribe": f"<{url}>"}))
        sent = connection.send_messages(mails) if mails else 0  # fine for small lists; use a task queue for large ones
        Newsletter.objects.create(subject=subject, body=body, sent_by=request.user, recipients=sent or 0)
        messages.success(request, f"Newsletter sent to {sent or 0} subscriber(s).")
        return redirect("staff_newsletter")
    return render(request, "support/newsletter_staff.html", {
        "form": form, "history": Newsletter.objects.all()[:10],
        "active_count": Subscriber.objects.filter(active=True).count()})


def _delete_view(request, model, pk, *, title, message, back, ok):
    obj = get_object_or_404(model, pk=pk)
    form = ConfirmForm(*form_args(request)[:1])
    if request.method == "POST" and form.is_valid():
        obj.delete()
        return done(request, ok, to=reverse(back))
    return modal_form(request, form, title=title, partial="panel/forms/confirm.html", submit="Delete", danger=True,
                      cancel_url=reverse(back), ctx={"message": message(obj)})


@capability_required("inquiries")
def contact_delete(request, pk):
    return _delete_view(request, ContactMessage, pk, title="Delete inquiry?", back="staff_contacts", ok="Inquiry deleted.",
                        message=lambda o: f"Permanently delete the inquiry '{o.subject}' from {o.name}?")


@capability_required("marketing")
def subscriber_delete(request, pk):
    return _delete_view(request, Subscriber, pk, title="Delete subscriber?", back="staff_subscribers", ok="Subscriber deleted.",
                        message=lambda o: f"Permanently remove {o.email} from the list? Use this for data-removal requests.")
