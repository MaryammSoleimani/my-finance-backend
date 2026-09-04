from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction
from budget.models import Budget
from notifications.models import Notification

@receiver(post_save, sender=Transaction)
def create_notifications(sender, instance, created, **kwargs):
    if not created or instance.kind != 'expense':
        return

    budget = Budget.objects.filter(
        user=instance.user,
        category=instance.category
    ).first()

    if budget:
        from django.db.models import Sum
        from datetime import datetime

        start_date = datetime.now().replace(day=1)
        total_spent = Transaction.objects.filter(
            user=instance.user,
            category=instance.category,
            kind='expense',
            date__gte=start_date
        ).aggregate(total=Sum('amount'))['total'] or 0

        percentage = (total_spent / float(budget.amount)) * 100

        if percentage >= 100:
            Notification.objects.create(
                user=instance.user,
                title='Budget Exceeded',
                message=f'You have exceeded your {budget.name} budget by ${total_spent - budget.amount:.2f}',
                type='budget'
            )
        elif percentage >= 80:
            Notification.objects.create(
                user=instance.user,
                title='Budget Warning',
                message=f'You have used {percentage:.0f}% of your {budget.name} budget',
                type='budget'
            )


@receiver(post_save, sender=Transaction)
def update_budget(sender, instance, created, **kwargs):
    if created and instance.kind == 'expense':
        budget = Budget.objects.filter(
            user=instance.user,
            category=instance.category
        ).first()

        if budget:
            budget.spent_amount += instance.amount
            budget.save()


@receiver(post_delete, sender=Transaction)
def restore_budget(sender, instance, **kwargs):
    if instance.kind == 'expense':
        budget = Budget.objects.filter(
            user=instance.user,
            category=instance.category
        ).first()

        if budget:
            budget.spent_amount -= instance.amount
            budget.save()


@receiver(post_save, sender=Transaction)
def update_account_balance(sender, instance, created, **kwargs):
    if created:
        account = instance.account
        # چون در مدل Account از DecimalField استفاده کردی، بهتر است تبدیل انجام شود
        from decimal import Decimal
        amount = Decimal(str(instance.amount))

        if instance.kind == 'income':
            account.balance += amount
        else:
            account.balance -= amount

        account.save()


@receiver(post_delete, sender=Transaction)
def restore_account_balance(sender, instance, **kwargs):
    account = instance.account
    from decimal import Decimal
    amount = Decimal(str(instance.amount))

    if instance.kind == 'income':
        account.balance -= amount
    else:
        account.balance += amount

    account.save()