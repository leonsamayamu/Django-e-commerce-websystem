from django.urls import path

from . import staff_views, views

urlpatterns = [
    path("contact/", views.contact, name="contact"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("account/newsletter/", views.newsletter_toggle, name="newsletter_toggle"),
    path("unsubscribe/<str:token>/", views.unsubscribe, name="unsubscribe"),

    path("account/messages/", views.inbox, name="inbox"),
    path("account/messages/new/", views.new_thread, name="new_thread"),
    path("account/messages/<int:pk>/", views.thread_detail, name="thread"),

    path("staff/messages/", staff_views.messages_list, name="staff_messages"),
    path("staff/messages/<int:pk>/", staff_views.thread_staff, name="staff_thread"),
    path("staff/inquiries/", staff_views.contacts, name="staff_contacts"),
    path("staff/inquiries/<int:pk>/delete/", staff_views.contact_delete, name="staff_contact_delete"),
    path("staff/subscribers/<int:pk>/delete/", staff_views.subscriber_delete, name="staff_subscriber_delete"),
    path("staff/subscribers/", staff_views.subscribers, name="staff_subscribers"),
    path("staff/newsletter/", staff_views.newsletter, name="staff_newsletter"),
]
