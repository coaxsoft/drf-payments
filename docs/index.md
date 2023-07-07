# DRF payments

Package to handle various payments provider inside your drf project

This package will allow you to create transactional payments on various payment providers:

- [Stripe](./providers/stripe.md)
- [Paypal](./providers/paypal.md)
- [Braintree](./providers/braintree.md)
- [Authorize.net](./providers/authorizenet.md)

---

Upon creation of your app `Payment` model this library will handle:

- Creation of payment on selected provider
  - Direct charge
  - Checkout session
- Handling webhook event from payment gateway to update `Payment` status
- Handle Refund on the payment if payment was processed
- Write along the way all payment gateway responses in `extra_data` json field of your `Payment` model

---

[Installation](./getting_started/installation.md) - Installation guide

[Usage](./getting_started/usage.md) - Usage

[Constants](constants.md) - List of predefined constants

[DRF](./drf/drf.md) - Explanation of DRF integration

For example of usage please see `example` app inside repository.
