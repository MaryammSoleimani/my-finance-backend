from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from Accounts.views import *

router = DefaultRouter()
router.register(r'main', TransactionViewSet, basename='transaction')


urlpatterns = [
    path('', include(router.urls)),
    path('category-expenses/', CategoryExpensesChart.as_view()),
    path('daily-expenses/', DailyExpensesChart.as_view(), name='daily-expenses'),
    path('grouped/', GroupedTransactionsView.as_view(), name='grouped-transactions'),
    path('latest/', LatestTransactionsView.as_view(), name='latest-transactions'),
]