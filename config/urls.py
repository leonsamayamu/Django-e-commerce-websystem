<<<<<<< HEAD
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("support.urls")),
    path("", include("content.urls")),
    path("", include("panel.urls")),
    path("", include("payments.urls")),
    path("", include("assistant.urls")),
    path("", include("store.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
=======
from django.contrib import admin
from django.urls import path, include

urlpatterns = [path("admin/", admin.site.urls), path("", include("store.urls"))]
>>>>>>> e3ba4c2ef93cb02a22c05fe11cdcdada809f318b
