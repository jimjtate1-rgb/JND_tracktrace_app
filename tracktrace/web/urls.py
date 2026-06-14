from django.urls import path

from tracktrace.web.views import track_view

app_name = "web"

urlpatterns = [
    path("", track_view, name="track"),
]
