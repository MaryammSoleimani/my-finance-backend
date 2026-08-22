from rest_framework import serializers
from .models import Asset, CashFlow, PlanEvent

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'
        read_only_fields = ('user',)

class CashFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlow
        fields = '__all__'
        read_only_fields = ('user',)

class PlanEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanEvent
        fields = '__all__'
        read_only_fields = ('user',)