from django.urls import path
from .views import get_budget_status

urlpatterns = [
    path('status/', get_budget_status),
]