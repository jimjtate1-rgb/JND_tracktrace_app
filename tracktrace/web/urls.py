from django.urls import path

from tracktrace.web.views import aircargo_view, ocean_view, track_view

app_name = "web"

urlpatterns = [
    path("", track_view, name="track"),
    path("aircargo/", aircargo_view, name="aircargo"),
    path("ocean/", ocean_view, name="ocean"),
]
