"""REST API views for read-only property access."""

from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Property
from .serializers import PropertySerializer


class PropertyViewSet(ReadOnlyModelViewSet):
    """Provide public list and detail endpoints for imported properties."""

    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [AllowAny]
    lookup_field = "property_id"
    lookup_url_kwarg = "id"
