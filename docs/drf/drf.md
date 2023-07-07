# DRF integration

For integrations with DRF we have couple of solutions.
Feel free to inherit them and override to more precise fit your needs

## PaymentCallbackView

View to handle webhooks from payment gateways

---
::: drf_payments.mixins.PaymentCallbackView
    options:
      heading_level: 3

## PaymentCallbackSerializerMixin

Serializer that contains all business logic related to processing webhook

---
::: drf_payments.mixins.PaymentCallbackSerializerMixin
    options:
      heading_level: 3

## PaymentSettingsView

Public view to return payment settings if needed on client part (currently only braintree provider)

---
::: drf_payments.mixins.PaymentSettingsView
    options:
      heading_level: 3

## PaymentViewMixin

View that handles creation of payment model, and adds refund action

---
::: drf_payments.mixins.PaymentViewMixin
    options:
      heading_level: 3

## PaymentSerializerMixin

Serializer to handle payment on model instance creation

---
::: drf_payments.mixins.PaymentSerializerMixin
    options:
      heading_level: 3
