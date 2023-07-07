import importlib
from decimal import Decimal
from typing import NamedTuple, Optional, Union

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from drf_payments.authorizenet import AuthorizeNetProvider
from drf_payments.braintree import BraintreeProvider
from drf_payments.paypal import PaypalProvider
from drf_payments.stripe import StripeCheckoutProvider, StripeProvider


class PurchasedItem(NamedTuple):
    """A single item in a purchase."""

    name: str
    quantity: int
    price: Decimal
    currency: str
    sku: str
    tax_rate: Optional[Decimal] = None


def get_payment_model():
    """
    Method to get payment model from project settings
    """
    try:
        app_label, model_name = settings.PAYMENT_MODEL.split(".")
    except (ValueError, AttributeError) as e:
        raise ImproperlyConfigured("PAYMENT_MODEL must be of the form " '"app_label.model_name"') from e
    payment_model = apps.get_model(app_label, model_name)
    if payment_model is None:
        msg = f'PAYMENT_MODEL refers to model "{settings.PAYMENT_MODEL}" that has not been installed'
        raise ImproperlyConfigured(msg)
    return payment_model


def get_payment_service(
    variant=None,
) -> Union[BraintreeProvider, StripeCheckoutProvider, StripeProvider, PaypalProvider, AuthorizeNetProvider]:
    """Returns instance of payment service based on variant"""
    if variant == "stripe":
        module, service_name = settings.PAYMENT_VARIANTS.get(variant)[0].rsplit(".", 1)
        return getattr(importlib.import_module(module), service_name)(
            secret_key=settings.PAYMENT_VARIANTS.get(variant)[1]["secret_key"],
            public_key=settings.PAYMENT_VARIANTS.get(variant)[1]["public_key"],
        )
    elif variant == "paypal":
        module, service_name = settings.PAYMENT_VARIANTS.get(variant)[0].rsplit(".", 1)
        return getattr(importlib.import_module(module), service_name)(
            client_id=settings.PAYMENT_VARIANTS.get(variant)[1]["client_id"],
            secret_key=settings.PAYMENT_VARIANTS.get(variant)[1]["secret"],
            endpoint=settings.PAYMENT_VARIANTS.get(variant)[1]["endpoint"],
        )
    elif variant == "braintree":
        module, service_name = settings.PAYMENT_VARIANTS.get(variant)[0].rsplit(".", 1)
        return getattr(importlib.import_module(module), service_name)(
            merchant_id=settings.PAYMENT_VARIANTS.get(variant)[1]["merchant_id"],
            public_key=settings.PAYMENT_VARIANTS.get(variant)[1]["public_key"],
            private_key=settings.PAYMENT_VARIANTS.get(variant)[1]["private_key"],
            sandbox=settings.PAYMENT_VARIANTS.get(variant)[1]["sandbox"],
        )
    elif variant == "authorizenet":
        module, service_name = settings.PAYMENT_VARIANTS.get(variant)[0].rsplit(".", 1)
        return getattr(importlib.import_module(module), service_name)(
            login_id=settings.PAYMENT_VARIANTS.get(variant)[1]["login_id"],
            transaction_key=settings.PAYMENT_VARIANTS.get(variant)[1]["transaction_key"],
            endpoint=settings.PAYMENT_VARIANTS.get(variant)[1]["endpoint"],
        )
    else:
        raise ImproperlyConfigured(f"{variant} is not valid variant")
