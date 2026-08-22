from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import Asset, CashFlow, PlanEvent
from .serializer import AssetSerializer, CashFlowSerializer, PlanEventSerializer
from django.db import models
from rest_framework.decorators import action
from rest_framework.response import Response
from Accounts.models import Account

# Create your views here.

class AssetViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssetSerializer

    def get_queryset(self):
        return Asset.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def import_from_accounts(self, request):
        total_balance = Account.objects.filter(owner=request.user).aggregate(
            total=models.Sum('balance'))['total'] or 0

        asset, created = Asset.objects.update_or_create(
            user=request.user,
            name='Imported Cash Accounts',
            defaults={
                'amount': total_balance,
                'asset_type': 'liquid',
                'growth_rate': 0
            }
        )

        serializer = self.get_serializer(asset)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def import_selected(self, request):
        account_ids = request.data.get('account_ids', [])
        user_accounts = Account.objects.filter(owner=request.user, id__in=account_ids)

        for acc in user_accounts:
            Asset.objects.update_or_create(
                user=request.user,
                name=f"Account: {acc.name}",
                defaults={
                    'amount': acc.balance,
                    'asset_type': 'liquid',
                    'growth_rate': 0
                }
            )
        return Response({"status": "success"})



class CashFlowViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CashFlowSerializer

    def get_queryset(self):
        return CashFlow.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PlanEventViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PlanEventSerializer

    def get_queryset(self):
        return PlanEvent.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)