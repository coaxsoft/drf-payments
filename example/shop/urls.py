from rest_framework.routers import SimpleRouter

from drf_payments.mixins import PaymentViewMixin

app_name = "shop"

router = SimpleRouter()
router.register("payment", PaymentViewMixin, basename="payment")

urlpatterns = [*router.urls]
