from django.contrib import admin
from django.urls import path, re_path

from apps.core.api import api
from apps.core.macro_setup import macro_setup_page
from apps.core.pwa_static import serve_pwa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("macro/", macro_setup_page, name="macro-setup"),
    re_path(r"^app(?:/(?P<path>.*))?$", serve_pwa),
    path("api/", api.urls),
]