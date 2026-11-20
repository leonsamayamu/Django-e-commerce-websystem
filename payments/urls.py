from django.urls import path

from . import views

urlpatterns = [path("payments/payhero/callback/<str:token>/", views.payhero_callback, name="payhero_callback")]
