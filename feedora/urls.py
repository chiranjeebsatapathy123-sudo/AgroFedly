from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("feedly.urls")),
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.svg", permanent=False)),
]
