from rest_framework import serializers
from .models import AnomalyAlert, HealthScore
import jdatetime

class AnomalyAlertSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    expected_amount_toman = serializers.SerializerMethodField()
    actual_amount_toman = serializers.SerializerMethodField()

    class Meta:
        model = AnomalyAlert
        fields = ['id', 'category', 'category_name', 'month', 'expected_amount',
                  'expected_amount_toman', 'actual_amount', 'actual_amount_toman',
                  'deviation_percentage']
        read_only_fields = ['id']

    def get_expected_amount_toman(self, obj):
        return float(obj.expected_amount)

    def get_actual_amount_toman(self, obj):
        return float(obj.actual_amount)



    class HealthScoreSerializer(serializers.ModelSerializer):
        class Meta:
            model = HealthScore
            fields = ['score', 'grade', 'last_calculated']




