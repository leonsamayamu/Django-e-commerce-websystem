from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .emails import notify_shop, send_safely, send_welcome
from .forms import ContactForm, NewThreadForm, ReplyForm, SubscribeForm
from .models import Message, Subscriber, Thread


# ---------- public pages
def contact(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {"name": request.user.get_full_name() or request.user.username, "email": request.user.email}
    form = ContactForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        if not form.cleaned_data["website"]:  # honeypot empty -> real person
            obj = form.save(commit=False)
            if request.user.is_authenticated:
                obj.user = request.user
            obj.save()
            notify_shop(f"Contact: {obj.subject}", f"From: {obj.name} <{obj.email}>\n\n{obj.message}")
        messages.success(request, "Thanks! We received your message and will reply by email.")
        return redirect("contact")
    return render(request, "support/contact.html", {"form": form})


@require_POST
def subscribe(request):
    form = SubscribeForm(request.POST)
    if form.is_valid():
        if not form.cleaned_data["website"]:
            email = form.cleaned_data["email"].lower()
            sub, created = Subscriber.objects.get_or_create(email=email)
            already = not created and sub.active
            if created or not sub.active:
                sub.active, sub.unsubscribed_at = True, None
                sub.save()
                send_welcome(request, sub)
            own = request.user.is_authenticated and request.user.email.lower() == email
            if already and own:  # safe to say so: it is the visitor's own account email
                messages.info(request, "You are already subscribed with your account email.")
                return redirect(_safe_next(request))
        # For any other address the reply is identical whether or not it was already subscribed (no email enumeration).
        messages.success(request, "Thanks for subscribing! Check your inbox for a welcome email.")
    else:
        messages.error(request, "Please enter a valid email address.")
    return redirect(_safe_next(request))


def _safe_next(request):
    nxt = request.POST.get("next", "/")
    return nxt if url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}) else "/"


@login_required
@require_POST
def newsletter_toggle(request):
    """Subscribe or unsubscribe the logged-in customer's account email from their profile page."""
    if not request.user.email:
        messages.error(request, "Add an email address to your profile first.")
        return redirect("profile")
    sub, created = Subscriber.objects.get_or_create(email=request.user.email.lower())
    if request.POST.get("action") == "unsubscribe":
        if sub.active:
            sub.active, sub.unsubscribed_at = False, timezone.now()
            sub.save()
        messages.success(request, "You are unsubscribed from the newsletter.")
    else:
        if created or not sub.active:
            sub.active, sub.unsubscribed_at = True, None
            sub.save()
            send_welcome(request, sub)
        messages.success(request, "You are subscribed to the newsletter.")
    return redirect("profile")


def unsubscribe(request, token):
    sub = get_object_or_404(Subscriber, token=token)
    if request.method == "POST":  # POST so email scanners that prefetch links cannot unsubscribe people
        sub.active, sub.unsubscribed_at = False, timezone.now()
        sub.save()
        return render(request, "support/unsubscribed.html")
    return render(request, "support/unsubscribe_confirm.html", {"sub": sub})


# ---------- messaging (shared by customer and staff views)
def thread_response(request, thread, staff_mode):
    """Show a thread and handle replies. `staff_mode` = viewed from the staff area."""
    thread.messages.filter(from_staff=not staff_mode, read=False).update(read=True)
    form = ReplyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        Message.objects.create(thread=thread, sender=request.user, from_staff=staff_mode, body=form.cleaned_data["body"])
        thread.save()  # bumps `updated`
        if staff_mode:
            send_safely(f"New reply: {thread.subject}", "Staff replied to your message. Log in to read it and respond.",
                        [thread.customer.email])
        else:
            notify_shop(f"Message from {thread.customer}: {thread.subject}", form.cleaned_data["body"])
        return redirect(request.path)
    template = "support/thread_staff.html" if staff_mode else "support/thread.html"
    return render(request, template, {"thread": thread, "form": form, "thread_messages": thread.messages.all()})


def unread_annotation(staff_mode):
    return Count("messages", filter=Q(messages__from_staff=not staff_mode, messages__read=False))


@login_required
def inbox(request):
    if request.user.is_staff:
        return redirect("staff_messages")
    threads = Thread.objects.filter(customer=request.user).annotate(unread=unread_annotation(False))
    return render(request, "support/inbox.html", {"threads": threads})


@login_required
def new_thread(request):
    form = NewThreadForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        thread = Thread.objects.create(customer=request.user, subject=form.cleaned_data["subject"])
        Message.objects.create(thread=thread, sender=request.user, from_staff=False, body=form.cleaned_data["body"])
        notify_shop(f"New message from {request.user}: {thread.subject}", form.cleaned_data["body"])
        return redirect("thread", pk=thread.pk)
    return render(request, "support/new_thread.html", {"form": form})


@login_required
def thread_detail(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    if thread.customer_id != request.user.id:
        raise Http404  # never reveal other customers' threads
    return thread_response(request, thread, staff_mode=False)
