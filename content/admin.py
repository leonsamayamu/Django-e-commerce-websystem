from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import AboutPage, AboutPhoto, AboutSection, StoreSettings


class SingletonAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(StoreSettings, SingletonAdmin)
admin.site.register(AboutPage, SingletonAdmin)


@admin.register(AboutSection)
class AboutSectionAdmin(ModelAdmin):
    list_display = ["heading", "position"]


@admin.register(AboutPhoto)
class AboutPhotoAdmin(ModelAdmin):
    list_display = ["caption", "position"]
