import secrets

from django.conf import settings
from django.db import models


def generate_token():
    return secrets.token_urlsafe(32)


class Thread(models.Model):
    """A private conversation between one customer and the shop staff."""
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads")
    subject = models.CharField(max_length=120)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return f"{self.subject} ({self.customer})"


class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    from_staff = models.BooleanField(default=False)
    body = models.TextField(max_length=4000)
    created = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)  # read by the other side

    class Meta:
        ordering = ["created"]


class ContactMessage(models.Model):
    """Public 'Contact us' form submissions (visitors need no account)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=4000)
    created = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["handled", "-created"]

    def __str__(self):
        return f"{self.subject} - {self.email}"


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    token = models.CharField(max_length=64, unique=True, default=generate_token, editable=False)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.email


class Newsletter(models.Model):
    subject = models.CharField(max_length=150)
    body = models.TextField()
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    sent_at = models.DateTimeField(auto_now_add=True)
    recipients = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return self.subject
