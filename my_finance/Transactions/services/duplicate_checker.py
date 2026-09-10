from Transactions.models import Transaction

def normalize_text(value):

    if not value:
        return ""

    return (
        value
        .strip()
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )



def check_duplicate(
        user,
        account,
        date,
        amount,
        kind,
        description
):

    transactions = Transaction.objects.filter(

        user=user,

        account=account,

        date=date,

        amount=amount,

        kind=kind

    )


    normalized_new = normalize_text(
        description
    )


    for transaction in transactions:


        old_description = normalize_text(
            transaction.desc
        )


        if old_description == normalized_new:

            return True



    return False