from django.contrib import admin
from django.urls import path

from apps.core.api import api
from apps.core.macro_setup import macro_setup_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("macro/", macro_setup_page, name="macro-setup"),
    path("api/", api.urls),
]