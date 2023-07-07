# Paypal

Create Paypal checkout session to handle payment

## Settings for provider

```python
PAYMENT_VARIANTS = {
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

## PaypalProvider

::: drf_payments.paypal.PaypalProvider
    options:
      heading_level: 3
