from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"

    def ready(self):
        from django.contrib import admin

        from . import signals  # noqa: F401
        # Second lock on the admin site itself: only active superusers pass, whatever the URL.
        admin.site.has_permission = lambda request: request.user.is_active and request.user.is_superuser
