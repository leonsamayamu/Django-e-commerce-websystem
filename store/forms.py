from django import forms
<<<<<<< HEAD
from django.conf import settings
from django.db import transaction
from django.db.models import Max

from .images import IMAGE_VALIDATORS
from .models import Product, ProductImage


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """ImageField that accepts several files and validates each one."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}))
        kwargs.setdefault("validators", IMAGE_VALIDATORS)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(d, initial) for d in data if d]
        return [single(data, initial)] if data else []


class ProductForm(forms.ModelForm):
    new_images = MultipleImageField(required=False, label="Upload photos",
                                    help_text="JPG, PNG or WebP, up to 5 MB each. Select several at once.")
    delete_images = forms.ModelMultipleChoiceField(queryset=ProductImage.objects.none(), required=False)
    cover = forms.ModelChoiceField(queryset=ProductImage.objects.none(), required=False)

    class Meta:
        model = Product
        fields = ["category", "name", "description", "price", "stock", "available", "image_url"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:  # restrict to this product's own photos
            own = self.instance.images.all()
            self.fields["delete_images"].queryset = own
            self.fields["cover"].queryset = own

    def clean(self):
        data = super().clean()
        existing = self.instance.images.count() if self.instance.pk else 0
        total = existing - len(data.get("delete_images") or []) + len(data.get("new_images") or [])
        if total > settings.MAX_PRODUCT_IMAGES:
            raise forms.ValidationError(f"A product can have at most {settings.MAX_PRODUCT_IMAGES} photos.")
        return data

    @transaction.atomic
    def save(self, commit=True):
        product = super().save()
        for img in self.cleaned_data["delete_images"]:
            img.delete()
        last = product.images.aggregate(m=Max("position"))["m"]
        start = 0 if last is None else last + 1
        for i, f in enumerate(self.cleaned_data["new_images"]):
            ProductImage.objects.create(product=product, image=f, position=start + i)
        cover = self.cleaned_data.get("cover")
        photos = list(product.images.all())
        if cover:
            photos.sort(key=lambda p: p.pk != cover.pk)  # stable: cover first, others keep order
        for pos, p in enumerate(photos):
            if p.position != pos:
                ProductImage.objects.filter(pk=p.pk).update(position=pos)
        return product
=======
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Order, Product


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=60, required=True, label="Full name")

    class Meta:
        model = User
        fields = ["username", "first_name", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        # Customers are never staff: is_staff/is_superuser stay False.
        if commit:
            user.save()
        return user


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "description", "price", "stock", "image_url", "available"]


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "paid"]
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
