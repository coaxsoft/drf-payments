from drf_payments.models import BasePayment


class Payment(BasePayment):
    class Meta:
        db_table = "payment"
