from django.urls import path
from .views import (
    HealthScoreView,
    AnomalyDetectionView,
    SmartGoalView
)

urlpatterns = [
    path('health-score/', HealthScoreView.as_view(), name='health-score'),
    path('anomaly-detection/', AnomalyDetectionView.as_view(), name='anomaly-detection'),
    path('smart-goal/', SmartGoalView.as_view(), name='smart-goal'),
]