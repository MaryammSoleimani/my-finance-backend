from django.apps import AppConfig

class TransactionsConfig(AppConfig):
    name = 'Transactions'

    def ready(self):
        import Transactions.signals