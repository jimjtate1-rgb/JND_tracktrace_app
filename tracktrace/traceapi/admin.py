from django.contrib import admin

from tracktrace.traceapi.models import (
    CargoItem,
    Container,
    Shipment,
    TrackingEvent,
)


class ContainerInline(admin.TabularInline):
    model = Container
    extra = 1


class CargoItemInline(admin.TabularInline):
    model = CargoItem
    extra = 1


class TrackingEventInline(admin.TabularInline):
    model = TrackingEvent
    extra = 1
    fields = ("event_datetime", "code", "description", "location", "location_code", "is_estimated")
    ordering = ("event_datetime",)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        "primary_reference",
        "mode",
        "carrier_name",
        "status",
        "origin_port",
        "destination_port",
        "eta",
    )
    list_filter = ("mode", "status", "carrier_code")
    search_fields = (
        "bill_of_lading",
        "booking_number",
        "awb_number",
        "containers__container_number",
        "destination_port",
    )
    inlines = [ContainerInline, CargoItemInline, TrackingEventInline]


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ("container_number", "container_type", "shipment")
    search_fields = ("container_number",)
