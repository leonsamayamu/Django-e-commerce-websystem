from django.core.cache import cache
from django.db import models

from store.images import IMAGE_VALIDATORS, about_path, optimize_image


class Singleton(models.Model):
    """One editable row (pk=1) cached for a minute."""
    class Meta:
        abstract = True

    @classmethod
    def load(cls):
        key = f"singleton:{cls.__name__}"
        obj = cache.get(key)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(key, obj, 60)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(f"singleton:{type(self).__name__}")


class StoreSettings(Singleton):
    """Business details shown on invoices, plus checkout switches. Edited by shop admins."""
    business_name = models.CharField(max_length=120, default="My Shop")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    tax_pin = models.CharField("Tax PIN / VAT number", max_length=40, blank=True)
    tax_rate = models.DecimalField("VAT rate (%)", max_digits=5, decimal_places=2, default=0,
                                   help_text="Prices already include VAT. Shown on invoices when above 0.")
    invoice_prefix = models.CharField(max_length=10, default="INV-")
    invoice_footer = models.CharField(max_length=200, blank=True, default="Thank you for your business.")
    cod_enabled = models.BooleanField("Allow pay on delivery", default=True)
    guest_checkout = models.BooleanField("Allow guest checkout", default=True)

    class Meta:
        verbose_name_plural = "store settings"

    def __str__(self):
        return "Store settings"


class AboutPage(Singleton):
    headline = models.CharField(max_length=150, default="About us")
    intro = models.TextField(max_length=600, default="We make shopping simple: honest prices, clear photos and a team that answers when you write.")

    class Meta:
        verbose_name = "About page"

    def __str__(self):
        return "About page"


class AboutSection(models.Model):
    heading = models.CharField(max_length=120)
    body = models.TextField(max_length=3000)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.heading


class AboutPhoto(models.Model):
    image = models.ImageField(upload_to=about_path, validators=IMAGE_VALIDATORS)
    caption = models.CharField(max_length=140, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.caption or f"Photo {self.pk}"

    def save(self, *args, **kwargs):
        if self.image and not getattr(self.image, "_committed", True):
            self.image = optimize_image(self.image.file, max_side=1800)
        super().save(*args, **kwargs)
