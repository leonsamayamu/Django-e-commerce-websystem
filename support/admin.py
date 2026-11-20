from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import ContactMessage, Message, Newsletter, Subscriber, Thread


class MessageInline(TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["sender", "from_staff", "created"]


@admin.register(Thread)
class ThreadAdmin(ModelAdmin):
    list_display = ["subject", "customer", "updated"]
    inlines = [MessageInline]


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ["subject", "name", "email", "created", "handled"]
    list_filter = ["handled"]
    search_fields = ["name", "email", "subject"]


@admin.register(Subscriber)
class SubscriberAdmin(ModelAdmin):
    list_display = ["email", "active", "created", "unsubscribed_at"]
    list_filter = ["active"]
    search_fields = ["email"]


@admin.register(Newsletter)
class NewsletterAdmin(ModelAdmin):
    list_display = ["subject", "sent_at", "recipients", "sent_by"]
    readonly_fields = ["sent_at", "recipients", "sent_by"]
