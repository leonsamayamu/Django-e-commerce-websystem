from django.utils.functional import SimpleLazyObject

from .models import ContactMessage, Message, Subscriber


def support(request):
    """Unread badges for sidebars. Lazy, so queries only run if a template prints them."""
    user = request.user
    if not user.is_authenticated:
        return {}
    subscribed = SimpleLazyObject(lambda: bool(user.email) and Subscriber.objects.filter(active=True, email__iexact=user.email).exists())
    if user.is_staff:
        return {"newsletter_subscribed": subscribed,
                "subs_active": SimpleLazyObject(lambda: Subscriber.objects.filter(active=True).count()),
            "unread_messages": SimpleLazyObject(lambda: Message.objects.filter(from_staff=False, read=False).count()),
            "new_contacts": SimpleLazyObject(lambda: ContactMessage.objects.filter(handled=False).count()),
        }
    return {"newsletter_subscribed": subscribed, "unread_messages": SimpleLazyObject(
        lambda: Message.objects.filter(thread__customer=user, from_staff=True, read=False).count())}
