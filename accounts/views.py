from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from support.emails import send_welcome
from support.models import Subscriber

from .forms import ProfileForm, RegisterForm, UserForm
from .models import Profile


class ShopLoginView(LoginView):
    """Staff go to the staff dashboard; customers return to the shop (or ?next=)."""

    def get_success_url(self):
        return self.get_redirect_url() or ("/staff/" if self.request.user.is_staff else "/")


def register(request):
    if request.user.is_authenticated:
        return redirect("product_list")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if form.cleaned_data["subscribe"]:
            sub, created = Subscriber.objects.get_or_create(email=user.email)
            if created or not sub.active:
                sub.active, sub.unsubscribed_at = True, None
                sub.save()
                send_welcome(request, sub)
        login(request, user)
        messages.success(request, "Welcome! Your account has been created.")
        return redirect("product_list")
    return render(request, "registration/register.html", {"form": form})


@login_required
def profile(request):
    prof, _ = Profile.objects.get_or_create(user=request.user)
    uform = UserForm(request.POST or None, instance=request.user, prefix="u")
    pform = ProfileForm(request.POST or None, request.FILES or None, instance=prof, prefix="p")
    if request.method == "POST" and uform.is_valid() and pform.is_valid():
        uform.save()
        if request.POST.get("remove_avatar") and not request.FILES.get("p-avatar"):
            prof.avatar.delete(save=False)
            prof.avatar = ""
        pform.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"uform": uform, "pform": pform, "prof": prof})
