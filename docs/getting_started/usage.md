# Usage

For usage you can check example implementation in repo

- Inherit `drf_payments.models.BasePayment` model in your app

```python
from drf_payments.models import BasePayment

class StripeChargePayment(BasePayment):
    ...

    class Meta:
        db_table = "stripe_charge"
```

- Use `drf_payments.mixins.PaymentViewMixin` in view that handles your payment model

```python

from rest_framework.routers import SimpleRouter

from drf_payments.mixins import PaymentViewMixin

app_name = "shop"

router = SimpleRouter()
router.register("payment", PaymentViewMixin, basename="payment")

urlpatterns = [*router.urls]


```

- Point your payments events to endpoint from settings `PAYMENT_CALLBACK_URL`

For more info please check `example` app inside repository
