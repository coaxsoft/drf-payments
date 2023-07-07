# Stripe

There is 2 stripe providers:

- StripeCheckoutProvider
- StripeProvider

## Settings for provider

```python
PAYMENT_VARIANTS = {
    "stripe": (
        "drf_payments.stripe.StripeCheckoutProvider",
        {
            "secret_key": os.environ.get("STRIPE_SECRET_KEY"),
            "public_key": os.environ.get("STRIPE_PUBLIC_KEY"),
        },
    ),
    "stripe": (
        "drf_payments.stripe.StripeProvider",
        {
            "secret_key": os.environ.get("STRIPE_SECRET_KEY"),
            "public_key": os.environ.get("STRIPE_PUBLIC_KEY"),
        },
    ),
    }
```

---

## StripeCheckoutProvider

::: drf_payments.stripe.StripeCheckoutProvider
    options:
      heading_level: 3

---

## StripeProvider

::: drf_payments.stripe.StripeProvider
    options:
      heading_level: 3
