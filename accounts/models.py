from django.conf import settings
from django.db import models

from store.images import IMAGE_VALIDATORS, avatar_path, optimize_image


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    STAFF_ROLES = [("manager", "Manager"), ("warehouse", "Warehouse"), ("delivery", "Delivery"),
                   ("support", "Customer support"), ("marketing", "Marketing")]
    staff_role = models.CharField(max_length=12, choices=STAFF_ROLES, blank=True,
                                  help_text="Only used for staff accounts. Controls which panel sections they can use.")
    avatar = models.ImageField(upload_to=avatar_path, blank=True, validators=IMAGE_VALIDATORS)

    def __str__(self):
        return f"Profile of {self.user}"

    def save(self, *args, **kwargs):
        if self.pk:  # delete the replaced avatar file
            old = Profile.objects.filter(pk=self.pk).values_list("avatar", flat=True).first()
            if old and old != self.avatar.name:
                self.avatar.storage.delete(old)
        if self.avatar and not getattr(self.avatar, "_committed", True):
            self.avatar = optimize_image(self.avatar.file, max_side=512)
        super().save(*args, **kwargs)
