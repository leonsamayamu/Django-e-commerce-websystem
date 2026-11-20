import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

TMP_MEDIA = tempfile.mkdtemp()
STRONG = "Tr0ub4dor&3-xyz"


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class AccountTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_register_creates_customer_with_profile(self):
        r = self.client.post(reverse("register"), {"username": "bob", "first_name": "Bob", "email": "Bob@X.com",
                                                   "password1": STRONG, "password2": STRONG, "is_staff": "on"})
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username="bob")
        self.assertFalse(u.is_staff)  # cannot escalate via form tampering
        self.assertEqual(u.email, "bob@x.com")
        self.assertTrue(hasattr(u, "profile"))

    def test_duplicate_email_rejected(self):
        User.objects.create_user("a", "dup@x.com", STRONG)
        r = self.client.post(reverse("register"), {"username": "b", "first_name": "B", "email": "DUP@x.com",
                                                   "password1": STRONG, "password2": STRONG})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="b").exists())

    def test_profile_update_with_avatar(self):
        u = User.objects.create_user("a", "a@x.com", STRONG)
        self.client.force_login(u)
        buf = io.BytesIO()
        Image.new("RGB", (900, 900), "blue").save(buf, "PNG")
        r = self.client.post(reverse("profile"), {
            "u-first_name": "Al", "u-last_name": "B", "u-email": "a@x.com", "p-phone": "0700", "p-city": "Nairobi",
            "p-address": "Street 1", "p-avatar": SimpleUploadedFile("me.png", buf.getvalue(), content_type="image/png")})
        self.assertEqual(r.status_code, 302)
        u.refresh_from_db()
        self.assertEqual(u.first_name, "Al")
        with Image.open(u.profile.avatar.path) as im:
            self.assertLessEqual(max(im.size), 512)

    def test_staff_login_redirects_to_dashboard(self):
        User.objects.create_user("st", "st@x.com", STRONG, is_staff=True)
        r = self.client.post(reverse("login"), {"username": "st", "password": STRONG})
        self.assertEqual(r["Location"], "/staff/")
