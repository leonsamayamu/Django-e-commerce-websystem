from django.conf import settings
from django.db import migrations


def set_manager(apps, schema_editor):
    """Staff created before roles existed keep their full access by becoming managers."""
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Profile = apps.get_model("accounts", "Profile")
    for user in User.objects.filter(is_staff=True, is_superuser=False):
        profile, _ = Profile.objects.get_or_create(user=user)
        if not profile.staff_role:
            profile.staff_role = "manager"
            profile.save(update_fields=["staff_role"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_profile_staff_role")]
    operations = [migrations.RunPython(set_manager, migrations.RunPython.noop)]
