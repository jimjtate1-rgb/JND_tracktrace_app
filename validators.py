from django.db.models import Q
from django_filters import CharFilter, ChoiceFilter, FilterSet

from tracktrace.traceapi.models import Shipment, TransportMode


class TraceFilter(FilterSet):
    """
    Filter shipments across both transport modes.

    Free-text `search` matches any reference number, the carrier, and the
    origin/destination ports, plus container numbers (ocean). It uses
    case-insensitive matching so it runs identically on SQLite and PostgreSQL;
    for production-scale full-text you'd add a Postgres SearchVector + GIN index.
    """

    mode = ChoiceFilter(choices=TransportMode.choices)
    bill_of_lading = CharFilter(field_name="bill_of_lading", lookup_expr="iexact")
    booking_number = CharFilter(field_name="booking_number", lookup_expr="iexact")
    awb_number = CharFilter(method="filter_awb")
    container_number = CharFilter(method="filter_container")
    carrier = CharFilter(method="filter_carrier")
    search = CharFilter(method="filter_search")

    class Meta:
        model = Shipment
        fields = ("mode", "bill_of_lading", "booking_number")

    def filter_awb(self, queryset, name, value):
        digits = value.replace("-", "").replace(" ", "")
        return queryset.filter(awb_number=digits)

    def filter_container(self, queryset, name, value):
        return queryset.filter(
            containers__container_number__iexact=value.replace(" ", "")
        ).distinct()

    def filter_carrier(self, queryset, name, value):
        return queryset.filter(
            Q(carrier_name__icontains=value) | Q(carrier_code__iexact=value)
        )

    def filter_search(self, queryset, name, value):
        v = value.strip()
        return queryset.filter(
            Q(bill_of_lading__icontains=v)
            | Q(booking_number__icontains=v)
            | Q(awb_number__icontains=v.replace("-", "").replace(" ", ""))
            | Q(carrier_name__icontains=v)
            | Q(carrier_code__iexact=v)
            | Q(origin_port__icontains=v)
            | Q(origin_code__iexact=v)
            | Q(destination_port__icontains=v)
            | Q(destination_code__iexact=v)
            | Q(destination_city__icontains=v)
            | Q(containers__container_number__icontains=v.replace(" ", ""))
        ).distinct()
