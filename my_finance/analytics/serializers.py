from rest_framework import serializers
from .models import AnomalyAlert, HealthScore


class AnomalyAlertSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = AnomalyAlert
        fields = ['id', 'category', 'category_name', 'month', 'expected_amount', 'actual_amount',
                  'deviation_percentage', 'created_at']


class HealthScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthScore
        fields = ['score', 'grade', 'last_calculated']