from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=60, required=True, label="Full name")
    subscribe = forms.BooleanField(required=False, label="Email me offers and news (you can unsubscribe any time)")

    class Meta:
        model = User
        fields = ["username", "first_name", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        if commit:  # is_staff / is_superuser stay False: customers can never self-register as staff
            user.save()
        return user


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("That email is used by another account.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["avatar", "phone", "city", "address"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
