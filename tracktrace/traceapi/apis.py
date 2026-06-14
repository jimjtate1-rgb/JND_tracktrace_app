from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from tracktrace.api.pagination import (
    LimitOffsetPagination,
    get_paginated_response_context,
)
from tracktrace.traceapi.carriers import carriers as list_carriers, detect_carrier
from tracktrace.traceapi.models import Shipment, TransportMode
from tracktrace.traceapi.selectors import (
    get_traces,
    serialize_cargo,
    serialize_containers,
    serialize_events,
)


class TraceApi(APIView):
    """
    GET /api/traceapi/trace/

    Track ocean and air shipments. Filter by mode, bill_of_lading,
    booking_number, container_number, awb_number, carrier, or free-text search.
    """

    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterTraceSerializer(serializers.Serializer):
        search = serializers.CharField(required=False, max_length=100)
        mode = serializers.ChoiceField(choices=TransportMode.choices, required=False)
        bill_of_lading = serializers.CharField(required=False, max_length=40)
        booking_number = serializers.CharField(required=False, max_length=40)
        awb_number = serializers.CharField(required=False, max_length=20)
        container_number = serializers.CharField(required=False, max_length=11)
        carrier = serializers.CharField(required=False, max_length=100)

    class OutputTraceSerializer(serializers.ModelSerializer):
        carrier = serializers.SerializerMethodField()
        references = serializers.SerializerMethodField()
        shipper = serializers.SerializerMethodField()
        consignee = serializers.SerializerMethodField()
        origin = serializers.SerializerMethodField()
        destination = serializers.SerializerMethodField()
        transport = serializers.SerializerMethodField()
        containers = serializers.SerializerMethodField()
        cargo = serializers.SerializerMethodField()
        events = serializers.SerializerMethodField()
        weather = serializers.SerializerMethodField()

        class Meta:
            model = Shipment
            fields = (
                "mode",
                "status",
                "carrier",
                "references",
                "shipper",
                "consignee",
                "origin",
                "destination",
                "transport",
                "containers",
                "cargo",
                "events",
                "weather",
            )

        def get_carrier(self, obj):
            return {"name": obj.carrier_name, "code": obj.carrier_code}

        def get_references(self, obj):
            return {
                "bill_of_lading": obj.bill_of_lading or None,
                "booking_number": obj.booking_number or None,
                "awb_number": obj.awb_number or None,
            }

        def get_shipper(self, obj):
            return {"name": obj.shipper_name, "address": obj.shipper_address}

        def get_consignee(self, obj):
            return {"name": obj.consignee_name, "address": obj.consignee_address}

        def get_origin(self, obj):
            return {
                "port": obj.origin_port,
                "code": obj.origin_code,
                "country": obj.origin_country,
            }

        def get_destination(self, obj):
            return {
                "port": obj.destination_port,
                "code": obj.destination_code,
                "country": obj.destination_country,
                "city": obj.destination_city,
            }

        def get_transport(self, obj):
            if obj.mode == TransportMode.OCEAN:
                conveyance = {"vessel": obj.vessel_name or None, "voyage": obj.voyage_number or None}
            else:
                conveyance = {"flight_number": obj.flight_number or None}
            return {
                **conveyance,
                "etd": obj.etd.isoformat() if obj.etd else None,
                "eta": obj.eta.isoformat() if obj.eta else None,
            }

        def get_containers(self, obj):
            return serialize_containers(obj)

        def get_cargo(self, obj):
            return serialize_cargo(obj)

        def get_events(self, obj):
            return serialize_events(obj)

        def get_weather(self, obj):
            weather = obj.weather
            if weather is None:
                return None
            return {"temperature": weather.temperature, "wind_speed": weather.wind_speed}

    @extend_schema(parameters=[FilterTraceSerializer], responses=OutputTraceSerializer)
    def get(self, request):
        filters_serializer = self.FilterTraceSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)

        try:
            query = (
                get_traces(filters=filters_serializer.validated_data)
                .select_related("weather")
                .prefetch_related("containers", "cargo", "events")
            )
        except Exception as ex:
            return Response(
                {"detail": "Filter Error - " + str(ex)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return get_paginated_response_context(
            pagination_class=self.Pagination,
            serializer_class=self.OutputTraceSerializer,
            queryset=query,
            request=request,
            view=self,
        )


class CarrierListApi(APIView):
    """
    GET /api/traceapi/carriers/

    List supported ocean BOL carriers (sourced from track-trace.com).
      ?with_scac=true   only carriers that have a SCAC mapped
      ?search=<text>    filter by name or SCAC
      ?detect=<number>  identify a carrier from a BOL/container number prefix
    """

    def get(self, request):
        detect = request.query_params.get("detect")
        if detect:
            match = detect_carrier(detect)
            return Response({"input": detect, "carrier": match})

        data = list_carriers(with_scac_only=request.query_params.get("with_scac") == "true")

        search = request.query_params.get("search")
        if search:
            s = search.lower()
            data = [c for c in data if s in c["name"].lower() or (c["scac"] or "").lower() == s]

        return Response({"count": len(data), "carriers": data})
