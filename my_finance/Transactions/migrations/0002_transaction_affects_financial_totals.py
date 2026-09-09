from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('Transactions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='affects_financial_totals',
            field=models.BooleanField(default=True),
        ),
    ]
