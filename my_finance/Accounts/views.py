from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Account
from Transactions.models import Transaction
from .serializers import AccountSerializer
from django.db.models import Sum, Q
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404


class AccountListView(APIView):
    def get(self, request):
        accounts = Account.objects.filter(owner=request.user)
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        new_account = Account.objects.create(
            owner=request.user,
            name=data.get('name'),
            balance=data.get('balance', 0),
            color=data.get('color', '#3b82f6'),
            is_debt=data.get('is_debt', False),
            type=data.get('type', 'account')
        )
        return Response({"message": "Account created!"}, status=201)

    def delete(self, request, pk):
        account = get_object_or_404(Account, pk=pk, owner=request.user)
        account.delete()
        return Response({"message": "Account deleted successfully"}, status=204)


class AccountSummaryView(APIView):
    def get(self, request):
        accounts = Account.objects.filter(owner=request.user)
        assets = accounts.filter(is_debt=False)
        liabilities = accounts.filter(is_debt=True)

        total_assets = assets.aggregate(Sum('balance'))['balance__sum'] or 0
        total_liabilities = liabilities.aggregate(Sum('balance'))['balance__sum'] or 0
        net_worth = total_assets - total_liabilities

        period = request.query_params.get('period', '1m')

        if period == '2w':
            num_days, step = 14, 1
        elif period == '3m':
            num_days, step = 90, 7
        elif period == '1y':
            num_days, step = 365, 30
        elif period == 'all':
            num_days, step = 1000, 30
        else:  # default 1m
            num_days, step = 30, 1

        today = datetime.now().date()

        dates = [(today - timedelta(days=i)) for i in range(0, num_days, step)]
        dates.reverse()

        dates_str = [d.strftime('%b %d') for d in dates]

        chart_series = []
        for acc in accounts:
            daily_balances = []
            current_balance = float(acc.balance)

            for d in dates:
                future_trans = Transaction.objects.filter(account=acc, date__gt=d).aggregate(
                    inc=Sum('amount', filter=Q(kind='income')),
                    exp=Sum('amount', filter=Q(kind='expense'))
                )

                income_after = float(future_trans['inc'] or 0)
                expense_after = float(future_trans['exp'] or 0)

                historical_balance = current_balance - income_after + expense_after
                daily_balances.append(round(historical_balance, 2))

            chart_series.append({
                'name': acc.name,
                'data': daily_balances,
                'color': acc.color
            })

        return Response({
            'assets': AccountSerializer(assets, many=True).data,
            'liabilities': AccountSerializer(liabilities, many=True).data,
            'total_assets': float(total_assets),
            'total_liabilities': float(total_liabilities),
            'net_worth': float(net_worth),
            'chart_data': {
                'dates': dates_str,
                'series': chart_series
            }
        })