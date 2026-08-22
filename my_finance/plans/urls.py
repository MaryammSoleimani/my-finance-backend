from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, CashFlowViewSet, PlanEventViewSet

router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='asset')
router.register(r'cash-flow', CashFlowViewSet, basename='cashflow')
router.register(r'events', PlanEventViewSet, basename='event')

urlpatterns = [
    path('', include(router.urls)),
]