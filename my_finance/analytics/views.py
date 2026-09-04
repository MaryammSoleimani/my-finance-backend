from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services.health_score import HealthScoreCalculator
from .services.anomaly_detection import AnomalyDetector
from .services.goal_setting import SmartGoalCalculator
from decimal import Decimal


class HealthScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = f'health_score_{request.user.id}'
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response(cached_result)

        calculator = HealthScoreCalculator(request.user)
        result = calculator.calculate()
        cache.set(cache_key, result, 300)

        return Response(result)


class AnomalyDetectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cache_key = f'anomaly_alerts_{request.user.id}'
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response(cached_result)

        detector = AnomalyDetector(request.user)
        alerts = detector.detect()
        cache.set(cache_key, {'alerts': alerts}, 300)  # 5 دقیقه

        return Response({'alerts': alerts})


class SmartGoalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        goal_amount = request.data.get('goal_amount')
        months = request.data.get('months')

        # Validate input
        if goal_amount is None or months is None:
            return Response(
                {
                    'error': 'Goal amount and timeframe are required.'
                },
                status=400
            )

        try:
            goal_amount = Decimal(str(goal_amount))
            months = int(months)

            if goal_amount <= 0:
                return Response(
                    {
                        'error': 'Goal amount must be greater than zero.'
                    },
                    status=400
                )

            if months <= 0:
                return Response(
                    {
                        'error': 'Timeframe must be greater than zero.'
                    },
                    status=400
                )

            calculator = SmartGoalCalculator(
                request.user,
                goal_amount,
                months
            )

            result = calculator.calculate()

            return Response(result)

        except (ValueError, TypeError, ArithmeticError) as e:

            return Response(
                {
                    'error': str(e)
                },
                status=400
            )

