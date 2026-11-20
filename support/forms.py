from django import forms

from .models import ContactMessage


class HoneypotMixin(forms.Form):
    """Hidden field real users never fill; bots do."""
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}), label="")


class ContactForm(HoneypotMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 6, "maxlength": 4000})}


class SubscribeForm(HoneypotMixin):
    email = forms.EmailField(max_length=254)


class NewThreadForm(forms.Form):
    subject = forms.CharField(max_length=120)
    body = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={"rows": 5}), label="Message")


class ReplyForm(forms.Form):
    body = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Write a reply..."}), label="")


class NewsletterForm(forms.Form):
    subject = forms.CharField(max_length=150)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 10}), help_text="Plain text. An unsubscribe link is added automatically.")
    confirm = forms.BooleanField(label="I confirm I want to send this to all active subscribers")
