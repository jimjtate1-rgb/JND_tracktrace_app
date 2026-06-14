from django.urls import path

from tracktrace.feeds.webhooks import air_webhook, dcsa_webhook, trackcargo_webhook

app_name = "feeds"

urlpatterns = [
    path("dcsa/webhook/", dcsa_webhook, name="dcsa-webhook"),
    path("air/webhook/", air_webhook, name="air-webhook"),
    path("trackcargo/webhook/", trackcargo_webhook, name="trackcargo-webhook"),
]
