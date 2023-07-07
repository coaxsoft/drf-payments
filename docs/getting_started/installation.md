# Installation

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
