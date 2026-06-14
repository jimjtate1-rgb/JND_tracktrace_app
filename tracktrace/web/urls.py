from django.urls import path
from django.views.generic import RedirectView

from tracktrace.web.views import aircargo_view, ocean_view

app_name = "web"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="web:aircargo", permanent=False), name="home"),
    path("aircargo/", aircargo_view, name="aircargo"),
    path("ocean/", ocean_view, name="ocean"),
]
