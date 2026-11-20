from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin, StackedInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Profile

admin.site.unregister(User)
admin.site.unregister(Group)


class ProfileInline(StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = [ProfileInline]
    list_display = ["username", "email", "first_name", "is_active", "is_staff", "date_joined"]


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ["user", "phone", "city"]
    search_fields = ["user__username", "user__email", "phone"]
