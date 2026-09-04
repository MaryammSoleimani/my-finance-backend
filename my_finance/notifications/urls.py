from django.urls import path
from .views import NotificationListView, NotificationPreferenceView

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('read-all/', NotificationListView.as_view(), name='notification-read-all'),
]