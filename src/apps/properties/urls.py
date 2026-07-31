"""Public REST routes for the property domain."""

from rest_framework.routers import DefaultRouter

from .views import PropertyViewSet

router = DefaultRouter(trailing_slash=False)
router.register("properties", PropertyViewSet, basename="property")

urlpatterns = router.urls
