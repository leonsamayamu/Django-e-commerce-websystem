from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory

from accounts.models import Profile
from accounts.roles import allowed_statuses, caps_for
from assistant.models import AssistantCommand, AssistantSettings
from content.models import AboutPage, AboutPhoto, AboutSection, StoreSettings
from payments.models import PaymentGateway
from store.forms import MultipleImageField
from store.models import Category, Order, Product, ProductVariant
from support.emails import send_safely

ROLE_CHOICES = [("customer", "Customer"), ("staff", "Staff")]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]


# ------------------------------------------------------------------ products: size / colour options
VariantFormSet = inlineformset_factory(
    Product, ProductVariant, fields=["name", "sku", "price", "stock", "available", "position"],
    extra=0, can_delete=True,
    widgets={"name": forms.TextInput(attrs={"placeholder": "e.g. Size 42 / Black"}),
             "price": forms.NumberInput(attrs={"placeholder": "Product price"}),
             "position": forms.NumberInput(attrs={"class": "!w-16"})})


# ------------------------------------------------------------------ users
class UniqueEmailMixin:
    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("That email is used by another account.")
        return email


def _staff_role_field():
    return forms.ChoiceField(choices=[("", "---------")] + Profile.STAFF_ROLES, required=False, label="Staff role",
                             help_text="Warehouse, delivery, support, marketing or manager. Decides which panel sections they see.")


class UserCreateForm(UniqueEmailMixin, UserCreationForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial="customer")
    staff_role = _staff_role_field()
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True, label="First name")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]

    field_order = ["username", "first_name", "last_name", "email", "role", "staff_role", "password1", "password2", "is_active"]

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["is_active"].initial = True
        if not actor.is_superuser:  # only shop admins create staff accounts
            self.fields["role"].choices = [("customer", "Customer")]
            self.fields["role"].help_text = "Only shop admins can create staff accounts."
            del self.fields["staff_role"]

    def clean(self):
        data = super().clean()
        if data.get("role") == "staff" and not data.get("staff_role"):
            self.add_error("staff_role", "Choose a staff role.")
        return data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_staff = self.cleaned_data["role"] == "staff"
        user.is_superuser = False  # superusers are only created with `manage.py createsuperuser`
        user.save()
        Profile.objects.update_or_create(user=user, defaults={"staff_role": self.cleaned_data.get("staff_role") or "" if user.is_staff else ""})
        return user


class UserEditForm(UniqueEmailMixin, forms.ModelForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    staff_role = _staff_role_field()
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active"]

    field_order = ["first_name", "last_name", "email", "role", "staff_role", "is_active"]

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        target = self.instance
        profile = getattr(target, "profile", None)
        self.fields["role"].initial = "staff" if target.is_staff else "customer"
        self.fields["staff_role"].initial = (profile.staff_role if profile else "") or ("manager" if target.is_staff else "")
        if not actor.is_superuser:
            self.fields["role"].disabled = True
            del self.fields["staff_role"]
        else:
            if target.pk == actor.pk or target.is_superuser:
                self.fields["role"].disabled = True
                self.fields["staff_role"].disabled = True
        if target.pk == actor.pk:  # never let someone lock themselves out
            self.fields["is_active"].disabled = True
            self.fields["is_active"].help_text = "You cannot deactivate your own account."
        if target.is_superuser:
            self.fields["role"].help_text = "Shop admin. Managed outside this panel."

    def clean(self):
        data = super().clean()
        if "staff_role" in self.fields and not self.fields["role"].disabled and data.get("role") == "staff" and not data.get("staff_role"):
            self.add_error("staff_role", "Choose a staff role.")
        return data

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if not self.fields["role"].disabled:
            user.is_staff = self.cleaned_data["role"] == "staff"
        user.save()
        if "staff_role" in self.fields and not self.fields["staff_role"].disabled:
            Profile.objects.update_or_create(user=user, defaults={"staff_role": self.cleaned_data.get("staff_role") or "" if user.is_staff else ""})
        return user


# ------------------------------------------------------------------ orders
class OrderStatusForm(forms.ModelForm):
    """Role-aware: warehouse and delivery staff can only set the statuses their job covers. Cancelling returns
    items to stock; re-opening takes them again; delivering a cash-on-delivery order marks it paid."""

    courier = forms.ModelChoiceField(queryset=User.objects.none(), required=False, label="Assigned courier",
                                     empty_label="Not assigned")

    class Meta:
        model = Order
        fields = ["status", "paid", "courier"]

    def __init__(self, *args, actor, order_url="", **kwargs):
        super().__init__(*args, **kwargs)
        self._old_status = self.instance.status
        self._old_paid = self.instance.paid
        self.order_url = order_url
        caps = caps_for(actor)
        allowed = allowed_statuses(actor)
        if allowed is not None:  # None means any status
            self.fields["status"].choices = [c for c in Order.STATUS_CHOICES if c[0] in allowed or c[0] == self._old_status]
        if "orders_manage" not in caps:
            del self.fields["paid"]
        if actor.is_superuser or "orders_manage" in caps or (actor.profile.staff_role == "warehouse" if hasattr(actor, "profile") else False):
            self.fields["courier"].queryset = User.objects.filter(is_active=True, is_staff=True, profile__staff_role="delivery")
            self.fields["courier"].label_from_instance = lambda u: u.get_full_name() or u.username
        else:
            del self.fields["courier"]

    def clean(self):
        data = super().clean()
        new = data.get("status")
        paid = data.get("paid", self._old_paid)
        if new and self._old_status == "cancelled" and new != "cancelled":
            for item in self.instance.items.select_related("product", "variant"):
                if item.available_stock() < item.quantity:
                    self.add_error("status", f"Cannot re-open: only {item.available_stock()} of {item.display_name} left in stock.")
                    break
        if (new in ("shipped", "out_for_delivery", "delivered") and self.instance.payment_method == "payhero" and not paid):
            self.add_error("status", "This order is waiting for the customer's online payment, so it cannot be dispatched yet.")
        return data

    @transaction.atomic
    def save(self, commit=True):
        order = super().save(commit=False)
        old, new = self._old_status, order.status
        if new == "delivered" and order.payment_method == "cod":
            order.paid = True  # the courier collected the cash
        order.save()
        if old != new:
            sign = 1 if new == "cancelled" and old != "cancelled" else -1 if old == "cancelled" else 0
            if sign:
                for item in order.items.all():
                    item.adjust_stock(sign)
            link = self.order_url or order.get_absolute_url()
            transaction.on_commit(lambda: send_safely(
                f"Your order #{order.pk} is now {order.get_status_display().lower()}",
                f"Hello {order.name},\n\nThe status of your order #{order.pk} changed to {order.get_status_display()}.\n"
                f"Track it here: {link}\n\nThank you for shopping with us.", [order.email]))
        return order


# ------------------------------------------------------------------ payment gateways (shop admins only)
class GatewayForm(forms.ModelForm):
    api_username = forms.CharField(label="PayHero API username", required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    api_password = forms.CharField(label="PayHero API password", required=False,
                                   widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}))

    class Meta:
        model = PaymentGateway
        fields = ["name", "provider", "channel_id", "api_username", "api_password", "credential_id", "enabled", "position"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["api_username"].help_text = f"Saved: {self.instance.masked_username}. Leave blank to keep it."
            self.fields["api_password"].help_text = "Saved securely and never shown again. Leave blank to keep it."
        else:
            self.fields["api_username"].required = self.fields["api_password"].required = True
            self.fields["api_username"].help_text = "From PayHero dashboard > Account > API Keys."
        self.fields["position"].help_text = "Lower numbers are listed first."

    def save(self, commit=True):
        gateway = super().save(commit=False)
        gateway.set_credentials(self.cleaned_data.get("api_username"), self.cleaned_data.get("api_password"))
        gateway.save()
        return gateway


# ------------------------------------------------------------------ About page content
class AboutPageForm(forms.ModelForm):
    class Meta:
        model = AboutPage
        fields = ["headline", "intro"]
        widgets = {"intro": forms.Textarea(attrs={"rows": 4})}


class AboutSectionForm(forms.ModelForm):
    class Meta:
        model = AboutSection
        fields = ["heading", "body", "position"]
        widgets = {"body": forms.Textarea(attrs={"rows": 6})}
        help_texts = {"body": "Plain text. Leave a blank line between paragraphs.", "position": "Lower numbers appear first."}


class AboutPhotosUploadForm(forms.Form):
    images = MultipleImageField(required=True, label="Photos", help_text="JPG, PNG or WebP, up to 5 MB each. Select several at once. The first photo is the large banner.")
    caption = forms.CharField(max_length=140, required=False, help_text="Optional caption (applied to every photo you upload now; edit each one later).")

    def save(self):
        last = AboutPhoto.objects.order_by("-position").values_list("position", flat=True).first()
        start = 0 if last is None else last + 1
        return [AboutPhoto.objects.create(image=f, caption=self.cleaned_data.get("caption", ""), position=start + i)
                for i, f in enumerate(self.cleaned_data["images"])]


class AboutPhotoForm(forms.ModelForm):
    class Meta:
        model = AboutPhoto
        fields = ["caption", "position"]


class StoreSettingsForm(forms.ModelForm):
    class Meta:
        model = StoreSettings
        fields = ["business_name", "address", "phone", "email", "tax_pin", "tax_rate", "invoice_prefix", "invoice_footer",
                  "cod_enabled", "guest_checkout"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


# ------------------------------------------------------------------ AI assistant (shop admins only)
class AssistantSettingsForm(forms.ModelForm):
    class Meta:
        model = AssistantSettings
        fields = ["enabled", "name", "greeting", "use_ai", "extra_instructions", "fallback_message", "max_messages_per_day"]
        widgets = {"extra_instructions": forms.Textarea(attrs={"rows": 3}), "greeting": forms.Textarea(attrs={"rows": 2})}


class AssistantCommandForm(forms.ModelForm):
    class Meta:
        model = AssistantCommand
        fields = ["trigger", "title", "response", "keywords", "audience", "use_in_ai", "show_chip", "active", "position"]
        widgets = {"response": forms.Textarea(attrs={"rows": 5})}

    def clean_trigger(self):
        t = self.cleaned_data["trigger"].lower()
        if t in ("help", "commands"):
            raise ValidationError("'help' and 'commands' are built in.")
        return t
