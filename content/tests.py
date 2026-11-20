import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from content.models import AboutPage, AboutPhoto, AboutSection

PW = "Tr0ub4dor&3-xyz"
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
MEDIA = tempfile.mkdtemp()


def img(name="a.jpg", size=(1200, 800), color="navy"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class AboutPageTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.manager = User.objects.create_user("m", "m@x.com", PW, is_staff=True)
        self.marketing = User.objects.create_user("mk", "mk@x.com", PW, is_staff=True)
        self.marketing.profile.staff_role = "marketing"
        self.marketing.profile.save()
        self.warehouse = User.objects.create_user("w", "w@x.com", PW, is_staff=True)
        self.warehouse.profile.staff_role = "warehouse"
        self.warehouse.profile.save()
        self.cust = User.objects.create_user("c", "c@x.com", PW)

    def test_public_page_reads_everything_from_the_database(self):
        AboutPage.objects.update_or_create(pk=1, defaults={"headline": "Our journey", "intro": "Since 2015 in Nairobi."})
        AboutSection.objects.create(heading="Why us", body="Fair prices.\n\nFast delivery.", position=1)
        AboutPhoto.objects.create(image=img(), caption="Our shop front", position=0)
        AboutPhoto.objects.create(image=img("b.jpg"), caption="The team", position=1)
        page = self.client.get(reverse("about"))
        for text in ("Our journey", "Since 2015 in Nairobi.", "Why us", "Fair prices.", "Fast delivery.", "Our shop front", "The team"):
            self.assertContains(page, text)
        self.assertContains(page, "/media/about/")  # photo files come from the stored records
        self.assertNotContains(page, "Edit this page")  # visitors cannot see the edit button

    def test_default_content_exists_on_first_visit(self):
        self.assertEqual(self.client.get(reverse("about")).status_code, 200)

    def test_edit_button_only_for_people_who_can_edit(self):
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse("about")), "Edit this page")
        self.client.force_login(self.warehouse)
        self.assertNotContains(self.client.get(reverse("about")), "Edit this page")

    def test_edit_page_text_section_and_photos_through_the_panel(self):
        self.client.force_login(self.marketing)  # marketing has the content capability
        self.client.post(reverse("staff_about_edit"), {"headline": "New headline", "intro": "New intro"}, **AJAX)
        self.client.post(reverse("staff_section_new"), {"heading": "Values", "body": "Honesty", "position": 2}, **AJAX)
        section = AboutSection.objects.get(heading="Values")
        self.client.post(reverse("staff_section_edit", args=[section.pk]), {"heading": "Our values", "body": "Honesty and care", "position": 1}, **AJAX)
        r = self.client.post(reverse("staff_photo_upload"), {"images": [img("1.jpg", (3000, 2000)), img("2.jpg")], "caption": "Team"}, **AJAX)
        self.assertEqual(r.status_code, 200)
        public = self.client.get(reverse("about")).content.decode()
        self.assertIn("New headline", public)
        self.assertIn("Our values", public)
        photos = list(AboutPhoto.objects.all())
        self.assertEqual([p.position for p in photos], [0, 1])
        with Image.open(photos[0].image.path) as im:
            self.assertLessEqual(max(im.size), 1800)  # optimised like product photos
        self.client.post(reverse("staff_photo_edit", args=[photos[1].pk]), {"caption": "Changed", "position": 0}, **AJAX)
        photos[1].refresh_from_db()
        self.assertEqual(photos[1].caption, "Changed")
        path = photos[0].image.path
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("staff_photo_delete", args=[photos[0].pk]), {}, **AJAX)
        import os
        self.assertFalse(os.path.exists(path))  # the file is removed with the record
        self.client.post(reverse("staff_section_delete", args=[section.pk]), {}, **AJAX)
        self.assertFalse(AboutSection.objects.exists())

    def test_text_is_escaped_never_rendered_as_html(self):
        AboutSection.objects.create(heading="<b>Bold?</b>", body="<script>alert('x')</script>")
        page = self.client.get(reverse("about")).content.decode()
        self.assertNotIn("<script>alert('x')</script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<b>Bold?</b>", page)

    def test_uploads_are_validated(self):
        self.client.force_login(self.manager)
        bad = SimpleUploadedFile("evil.jpg", b"not an image", content_type="image/jpeg")
        r = self.client.post(reverse("staff_photo_upload"), {"images": [bad]}, **AJAX)
        self.assertEqual(r.status_code, 422)
        self.assertEqual(AboutPhoto.objects.count(), 0)

    def test_only_content_editors_reach_the_editor(self):
        for user, code in ((self.manager, 200), (self.marketing, 200), (self.warehouse, 403), (self.cust, 403)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("staff_about")).status_code, code, user.username)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("staff_about")).status_code, 302)
        self.client.force_login(self.warehouse)
        self.assertEqual(self.client.post(reverse("staff_about_edit"), {"headline": "x", "intro": "y"}, **AJAX).status_code, 403)

    def test_store_settings_are_admin_only(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("staff_settings")).status_code, 403)
        admin = User.objects.create_superuser("boss", "b@x.com", PW)
        self.client.force_login(admin)
        r = self.client.post(reverse("staff_settings_edit"), {
            "business_name": "Acme", "address": "1 Road", "phone": "0700", "email": "a@x.com", "tax_pin": "P1", "tax_rate": "16",
            "invoice_prefix": "AC-", "invoice_footer": "Thanks", "cod_enabled": "on", "guest_checkout": "on"}, **AJAX)
        self.assertEqual(r.status_code, 200)
        from content.models import StoreSettings
        self.assertEqual(StoreSettings.load().business_name, "Acme")
