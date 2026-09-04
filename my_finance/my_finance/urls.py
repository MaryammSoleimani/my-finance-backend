# backend/my_finance/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/transaction/', include('Transactions.urls')),
    path('api/accounts/', include('Accounts.urls')),
    path('api/budget/', include('budget.urls')),
    path('api/categories/', include('categories.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/plans/', include('plans.urls')),
    path('api/assistant/', include('assistant.urls')),
    path('api/analytics/', include('analytics.urls'))
]