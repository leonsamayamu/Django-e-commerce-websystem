from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AssistantCommand, AssistantSettings


@admin.register(AssistantSettings)
class AssistantSettingsAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return not AssistantSettings.objects.exists()


@admin.register(AssistantCommand)
class AssistantCommandAdmin(ModelAdmin):
    list_display = ["trigger", "title", "audience", "use_in_ai", "active"]
    list_filter = ["audience", "active", "use_in_ai"]
    search_fields = ["trigger", "title", "response"]
