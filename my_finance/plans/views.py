# backend/plans/views.py
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from .models import Asset, CashFlow, Event
from .serializer import AssetSerializer, CashFlowSerializer, EventSerializer
from .simulation import SimulationEngine


class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Asset.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def import_from_accounts(self, request):
        """Import all accounts as assets"""
        from Accounts.models import Account
        # اصلاح: استفاده از owner به جای user
        accounts = Account.objects.filter(owner=request.user)
        imported_count = 0

        for account in accounts:
            Asset.objects.get_or_create(
                user=request.user,
                name=account.name,
                defaults={
                    'amount': account.balance,
                    'asset_type': 'liquid' if not account.is_debt else 'illiquid',
                }
            )
            imported_count += 1

        return Response({'imported': imported_count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def available_accounts(self, request):
        from Accounts.models import Account
        # اصلاح: استفاده از owner به جای user
        accounts = Account.objects.filter(owner=request.user)
        data = [{
            'id': acc.id,
            'name': acc.name,
            'type': acc.type,
            'balance': acc.balance,
            'is_debt': acc.is_debt
        } for acc in accounts]
        return Response(data)

    @action(detail=False, methods=['post'])
    def import_selected(self, request):
        from Accounts.models import Account
        account_ids = request.data.get('account_ids', [])
        # اصلاح: استفاده از owner به جای user
        accounts = Account.objects.filter(owner=request.user, id__in=account_ids)

        for account in accounts:
            Asset.objects.get_or_create(
                user=request.user,
                name=account.name,
                defaults={
                    'amount': account.balance,
                    'asset_type': 'liquid' if not account.is_debt else 'illiquid',
                }
            )

        return Response({'imported': accounts.count()}, status=status.HTTP_200_OK)


class CashFlowViewSet(viewsets.ModelViewSet):
    serializer_class = CashFlowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CashFlow.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SimulationSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        engine = SimulationEngine(request.user)
        data = engine.calculate_summary()
        return Response(data)


class SimulationTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        engine = SimulationEngine(request.user)
        data = engine.calculate_timeline()
        return Response(data)


class SimulationStepsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        engine = SimulationEngine(request.user)
        data = engine.calculate_steps()
        return Response(data)


class SimulationRunView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        engine = SimulationEngine(request.user)
        # اجرای شبیه‌سازی و ذخیره نتایج
        summary = engine.calculate_summary()
        timeline = engine.calculate_timeline()
        steps = engine.calculate_steps()

        return Response({
            'summary': summary,
            'timeline': timeline,
            'steps': steps
        })