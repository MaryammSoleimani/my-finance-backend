from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssetViewSet,
    CashFlowViewSet,
    EventViewSet,
    SimulationSummaryView,
    SimulationTimelineView,
    SimulationStepsView,
    SimulationRunView
)

router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='assets')
router.register(r'cash-flows', CashFlowViewSet, basename='cash-flows')
router.register(r'events', EventViewSet, basename='events')

urlpatterns = [
    path('', include(router.urls)),
    path('simulation/summary/', SimulationSummaryView.as_view(), name='simulation-summary'),
    path('simulation/timeline/', SimulationTimelineView.as_view(), name='simulation-timeline'),
    path('simulation/steps/', SimulationStepsView.as_view(), name='simulation-steps'),
    path('simulation/run/', SimulationRunView.as_view(), name='simulation-run'),
]