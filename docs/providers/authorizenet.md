# Authorizenet

Create payment via Authorize.net

## Settings for provider

```python
PAYMENT_VARIANTS = {
    "braintree": (
        "drf_payments.braintree.BraintreeProvider",
        {
            "merchant_id": os.environ.get("BRAINTREE_MERCHANT_ID"),
            "public_key": os.environ.get("BRAINTREE_PUBLIC_KEY"),
            "private_key": os.environ.get("BRAINTREE_PRIVATE_KEY"),
            "sandbox": os.environ.get("BRAINTREE_SANDBOX", True),
        },
    ),
    }
```

## AuthorizeNetProvider

::: drf_payments.authorizenet.AuthorizeNetProvider
    options:
      heading_level: 3
