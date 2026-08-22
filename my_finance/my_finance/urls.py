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
    path('api/transaction/', include('Transactions.url')),
    path('api/accounts/', include('Accounts.urls')),
    path('api/categories/', include('Category.urls')),
    path('api/budget/', include('Budget.url')),
    path('api/plans/', include('plans.urls')),
]