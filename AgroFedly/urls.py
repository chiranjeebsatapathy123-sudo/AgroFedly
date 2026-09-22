from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView
from feedly.views.health import health_check, readiness_probe

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("feedly.urls")),
    path("sw.js", TemplateView.as_view(template_name="sw.js", content_type="application/javascript"), name="service_worker"),
    path("health/", include([
        path("", health_check, name="health_check"),
        path("readiness/", readiness_probe, name="readiness_probe"),
    ])),
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.svg", permanent=False)),
]

handler400 = 'feedly.views.errors.custom_400'
handler403 = 'feedly.views.errors.custom_403'
handler404 = 'feedly.views.errors.custom_404'
handler500 = 'feedly.views.errors.custom_500'
