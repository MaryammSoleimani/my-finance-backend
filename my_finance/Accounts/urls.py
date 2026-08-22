from django.urls import path
from .views import *

urlpatterns = [
    path('summary/', AccountSummaryView.as_view(), name='account-summary'),
    path('', AccountListView.as_view(), name='account-list'),
    path('<int:pk>/', AccountListView.as_view(), name='account-delete'),
]