from rest_framework import serializers
from .models import Notification, NotificationPreference

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'is_read', 'enabled', 'created_at']
        read_only_fields = ['id', 'created_at']

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['budget_alerts', 'spending_alerts', 'goal_reminders', 'weekly_summary', 'budget_threshold']