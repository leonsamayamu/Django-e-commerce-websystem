from django.urls import path

from . import views

urlpatterns = [
    path("assistant/init/", views.init, name="assistant_init"),
    path("assistant/chat/", views.chat, name="assistant_chat"),
    path("assistant/reset/", views.reset, name="assistant_reset"),
]
