from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from .constants import FraudStatus, PaymentCurrency, PaymentStatus


class BasePayment(models.Model):
    """
    Model to represent single payment transaction
    """

    variant = models.CharField(max_length=255)
    #: Transaction status
    status = models.CharField(
        max_length=255,
        choices=[(v.name, v.value) for v in PaymentStatus],
        blank=True,
        default=PaymentStatus.WAITING.name,
    )
    fraud_status = models.CharField(
        _("fraud check"),
        max_length=10,
        choices=[(v.name, v.value) for v in FraudStatus],
        default=FraudStatus.UNKNOWN.name,
    )
    fraud_message = models.TextField(blank=True, default="")
    #: Creation date and time
    created = models.DateTimeField(auto_now_add=True)
    #: Date and time of last modification
    modified = models.DateTimeField(auto_now=True)
    #: Transaction ID (if applicable)
    transaction_id = models.CharField(max_length=255, blank=True)
    #: Currency code (may be provider-specific)
    currency = models.CharField(
        _("Currency"),
        max_length=10,
        choices=[(v.name, v.value) for v in PaymentCurrency],
        default=PaymentCurrency.USD.name,
    )
    #: Total amount (gross)
    total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    delivery = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    description = models.TextField(blank=True, default="")
    billing_first_name = models.CharField(max_length=256, blank=True)
    billing_last_name = models.CharField(max_length=256, blank=True)
    billing_address_1 = models.CharField(max_length=256, blank=True)
    billing_address_2 = models.CharField(max_length=256, blank=True)
    billing_city = models.CharField(max_length=256, blank=True)
    billing_postcode = models.CharField(max_length=256, blank=True)
    billing_country_code = models.CharField(max_length=2, blank=True)
    billing_country_area = models.CharField(max_length=256, blank=True)
    billing_email = models.EmailField(blank=True)
    billing_phone = PhoneNumberField(blank=True)
    customer_ip_address = models.GenericIPAddressField(blank=True, null=True)
    extra_data = models.JSONField(default=dict)
    message = models.TextField(blank=True, default="")
    token = models.CharField(max_length=36, blank=True, default="")
    captured_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.variant}-{self.total}"

    @property
    def failure_url(self) -> str:
        return f"{settings.PAYMENT_FAILURE_URL}"

    @property
    def success_url(self) -> str:
        return f"{settings.PAYMENT_SUCCESS_URL}"
