from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("accounts/login/", views.ShopLoginView.as_view(), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),  # POST only (Django 5)
    path("accounts/register/", views.register, name="register"),
    path("account/profile/", views.profile, name="profile"),
    path("account/password/", auth_views.PasswordChangeView.as_view(), name="password_change"),
    path("account/password/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("accounts/password-reset/", auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("accounts/password-reset/done/", auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("accounts/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("accounts/reset/done/", auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
