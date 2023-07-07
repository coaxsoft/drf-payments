from django.urls import path

from drf_payments import get_payment_service
from drf_payments.braintree import BraintreeProvider
from drf_payments.mixins import PaymentCallbackView, PaymentSettingsView

urlpatterns = [
    path("callback", PaymentCallbackView.as_view(), name="payment-callback"),
]
# TODO: Check if other payments need settings view
if isinstance(get_payment_service("braintree"), BraintreeProvider):
    urlpatterns.append(path("settings", PaymentSettingsView().as_view(), name="braintree-settings"))
