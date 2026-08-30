from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services.health_score import HealthScoreCalculator
from .services.anomaly_detection import AnomalyDetector
from .services.goal_setting import SmartGoalCalculator


class HealthScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        calculator = HealthScoreCalculator(request.user)
        result = calculator.calculate()
        return Response(result)


class AnomalyDetectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        detector = AnomalyDetector(request.user)
        alerts = detector.detect()
        return Response({'alerts': alerts})


class SmartGoalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        goal_amount = request.data.get('goal_amount')
        months = request.data.get('months')

        if not goal_amount or not months:
            return Response({'error': 'goal_amount and months are required'}, status=400)

        calculator = SmartGoalCalculator(request.user, goal_amount, months)
        result = calculator.calculate()
        return Response(result)