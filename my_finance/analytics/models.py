from django.db import models
from django.contrib.auth.models import User
from categories.models import Category


class AnomalyAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anomaly_alerts')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    month = models.CharField(max_length=20)
    expected_amount = models.DecimalField(max_digits=15, decimal_places=2)
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2)
    deviation_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_alerted = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'anomaly_alerts'
        ordering = ['-created_at']


class HealthScore(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='health_score')
    score = models.IntegerField(default=0)
    grade = models.CharField(max_length=5, default='C')
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'health_scores'