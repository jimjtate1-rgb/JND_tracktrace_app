from django.urls import path

from tracktrace.traceapi.apis import CarrierListApi, TraceApi

app_name = "traceapi"

urlpatterns = [
    path("trace/", TraceApi.as_view(), name="trace"),
    path("carriers/", CarrierListApi.as_view(), name="carriers"),
]
