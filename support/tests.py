from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import ContactMessage, Message, Newsletter, Subscriber, Thread


class SubscriptionTests(TestCase):
    def test_subscribe_is_idempotent_and_sends_welcome_once(self):
        for _ in range(2):
            self.client.post(reverse("subscribe"), {"email": "A@x.com", "next": "/about/"})
        self.assertEqual(Subscriber.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("unsubscribe", mail.outbox[0].body.lower())

    def test_open_redirect_blocked_and_bots_ignored(self):
        r = self.client.post(reverse("subscribe"), {"email": "b@x.com", "next": "https://evil.example/"})
        self.assertEqual(r["Location"], "/")
        self.client.post(reverse("subscribe"), {"email": "bot@x.com", "website": "spam"})
        self.assertFalse(Subscriber.objects.filter(email="bot@x.com").exists())

    def test_unsubscribe_requires_post(self):
        s = Subscriber.objects.create(email="c@x.com")
        self.client.get(reverse("unsubscribe", args=[s.token]))
        s.refresh_from_db()
        self.assertTrue(s.active)
        self.client.post(reverse("unsubscribe", args=[s.token]))
        s.refresh_from_db()
        self.assertFalse(s.active)

    def test_newsletter_goes_only_to_active_subscribers(self):
        staff = User.objects.create_user("st", "st@x.com", "pw-Staff-123", is_staff=True)
        Subscriber.objects.create(email="on@x.com")
        Subscriber.objects.create(email="off@x.com", active=False)
        self.client.force_login(staff)
        self.client.post(reverse("staff_newsletter"), {"subject": "Hi", "body": "News", "confirm": "on"})
        self.assertEqual([m.to for m in mail.outbox], [["on@x.com"]])
        self.assertIn("Unsubscribe:", mail.outbox[0].body)
        self.assertEqual(Newsletter.objects.get().recipients, 1)


class ContactTests(TestCase):
    def test_contact_saved_and_shop_notified(self):
        r = self.client.post(reverse("contact"), {"name": "N", "email": "n@x.com", "subject": "Hi", "message": "Hello"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_honeypot(self):
        self.client.post(reverse("contact"), {"name": "N", "email": "n@x.com", "subject": "Hi", "message": "x", "website": "bot"})
        self.assertEqual(ContactMessage.objects.count(), 0)


class MessagingTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user("a", "a@x.com", "pw-A-12345")
        self.b = User.objects.create_user("b", "b@x.com", "pw-B-12345")
        self.staff = User.objects.create_user("st", "st@x.com", "pw-St-12345", is_staff=True)

    def test_conversation_flow_and_unread(self):
        self.client.force_login(self.a)
        r = self.client.post(reverse("new_thread"), {"subject": "Order?", "body": "Where is it?"})
        thread = Thread.objects.get()
        self.assertEqual(r["Location"], reverse("thread", args=[thread.pk]))
        self.client.force_login(self.staff)
        self.assertEqual(Message.objects.filter(read=False, from_staff=False).count(), 1)
        self.assertContains(self.client.get(reverse("staff_thread", args=[thread.pk])), "Where is it?")
        self.assertEqual(Message.objects.filter(read=False).count(), 0)  # marked read by staff
        self.client.post(reverse("staff_thread", args=[thread.pk]), {"body": "On its way"})
        msg = Message.objects.filter(from_staff=True).get()
        self.assertFalse(msg.read)
        self.client.force_login(self.a)
        self.assertContains(self.client.get(reverse("inbox")), "1 new")

    def test_customers_cannot_read_each_others_threads(self):
        t = Thread.objects.create(customer=self.a, subject="Private")
        Message.objects.create(thread=t, sender=self.a, body="secret")
        self.client.force_login(self.b)
        self.assertEqual(self.client.get(reverse("thread", args=[t.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("inbox")), "Private")
