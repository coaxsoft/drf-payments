from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from shop.models import Payment

from drf_payments import get_payment_model, get_payment_service
from drf_payments.core import BasicProvider, _default_provider_factory


class CoreTest(TestCase):
    def setUp(self):
        self.payment = Payment.objects.create(
            variant="stripe",
            total=200,
            transaction_id="dummyId",
            extra_data={"session": "dummy_data"},
        )

    def test_get_payment_model(self):
        get_payment_model()

    @patch("django.apps.apps.get_model")
    def test_get_payment_model_none(self, mock):
        mock.return_value = None
        with self.assertRaises(ImproperlyConfigured):
            get_payment_model()

    @override_settings(
        PAYMENT_MODEL="some.wrong.model",
    )
    def test_get_payment_model_error(self):
        with self.assertRaises(ImproperlyConfigured):
            get_payment_model()

    def test_get_payment_service_error(self):
        with self.assertRaises(ImproperlyConfigured):
            get_payment_service("some.wrong.variant")

    def test_factory(self):
        _default_provider_factory("stripe")

    def test_factory_wrong_provider(self):
        with self.assertRaises(ValueError):
            _default_provider_factory("random")

    def test_process_payment_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            BasicProvider().process_payment(self.payment)

    def test_refund_payment_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            BasicProvider().refund(self.payment)

    @override_settings(
        PAYMENT_VARIANT_FACTORY="some_factory",
    )
    def test_factory_from_string(self):
        get_payment_service("stripe")
