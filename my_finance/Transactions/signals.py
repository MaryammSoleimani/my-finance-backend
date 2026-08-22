from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction


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