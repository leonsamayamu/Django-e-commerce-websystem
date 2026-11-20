import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

log = logging.getLogger(__name__)


def send_safely(subject, body, to):
    """Notifications are best-effort: a mail outage must never break the user's request."""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, to)
    except Exception:  # noqa: BLE001
        log.exception("Failed to send email %r to %s", subject, to)


def absolute_url(request, path):
    """Public link for emails. Set PUBLIC_BASE_URL when running behind a proxy or tunnel."""
    base = (settings.PUBLIC_BASE_URL or request.build_absolute_uri("/")).rstrip("/")
    return f"{base}{path}"


def notify_shop(subject, body):
    send_safely(f"[{settings.SHOP_NAME}] {subject}", body, [settings.SHOP_EMAIL])


def unsubscribe_url(request, subscriber):
    return absolute_url(request, reverse("unsubscribe", args=[subscriber.token]))


def send_welcome(request, subscriber):
    send_safely(
        f"Welcome to {settings.SHOP_NAME}",
        f"Thanks for subscribing to {settings.SHOP_NAME} updates.\n\n"
        f"You can unsubscribe at any time: {unsubscribe_url(request, subscriber)}",
        [subscriber.email],
    )
