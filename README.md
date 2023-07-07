# DRF payments

<p align="center">
  <a href="https://dufran.github.io/drf-payments/"><img src="https://img.shields.io/badge/doc-mkdocs-02a6f2?style=flat-square&logo=read-the-docs" alt="Documentation"></a>
  <a href="https://github.com/Dufran/drf-payments/actions/workflows/tests.yml" ><img src="https://github.com/Dufran/drf-payments/actions/workflows/tests.yml/badge.svg?branch=main" alt="Tests"/></a>
<img alt="PyPI" src="https://img.shields.io/pypi/v/drf-payments">
<a><img src="https://img.shields.io/pypi/pyversions/drf-payments"/></a>
<a><img src="https://img.shields.io/pypi/frameworkversions/django/drf-payments"/></a>
<img alt="GitHub tag (latest SemVer pre-release)" src="https://img.shields.io/github/v/tag/dufran/drf-payments">
</p>

Package to handle various payments provider inside your drf project

This package will allow you to create transactional payments on various payment providers:

- Stripe
- Paypal
- Braintree
- Authorize.net

Upon creation of your app `Payment` model this library will handle:

- Creation of payment on selected provider
  - Direct charge
  - Checkout session
- Handling webhook event from payment gateway to update `Payment` status
- Handle Refund on the payment if payment was processed
- Write along the way all payment gateway responses in `extra_data` json field of your `Payment` model

For example of usage please see `example` app inside repository.

## Installation

- `pip install drf-payments`
- Add to `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "drf_payments",
    ...
]
```

- Add callback url

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    ...
    path("drf-payments/", include("drf_payments.urls")),
]

```

- Provide required settings

```python

PAYMENT_MODEL = "stripe_checkout.StripeCheckoutPayment"
PAYMENT_CALLBACK_URL = "http://localhost:8000/drf-payments/callback/"
PAYMENT_SUCCESS_URL = "http://localhost:3000/payments/success/"
PAYMENT_FAILURE_URL = "http://localhost:3000/payments/failure/"

PAYMENT_VARIANTS = {
    "stripe": (
        "drf_payments.stripe.StripeCheckoutProvider",
        {
            "secret_key": os.environ.get("STRIPE_SECRET_KEY"),
            "public_key": os.environ.get("STRIPE_PUBLIC_KEY"),
        },
    ),
    "paypal": (
        "drf_payments.paypal.PaypalProvider",
        {
            "client_id": os.environ.get("PAYPAL_CLIENT_ID"),
            "secret": os.environ.get("PAYPAL_SECRET_KEY"),
            "endpoint": os.environ.get("PAYPAL_URL", "https://api.sandbox.paypal.com"),
        },
    ),
}
```

## Usage

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

For even more detail check [documentation](https://dufran.github.io/drf-payments/)
