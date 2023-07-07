from dataclasses import asdict, dataclass, field
from typing import Optional

import stripe

from ..constants import PaymentError, PaymentStatus
from ..core import BasicProvider


def convert_amount(currency, amount) -> int:
    """convert_amount

    Converts amount from decimal to integer cents

    Args:
        currency (currency): Your currency code
        amount (decimal): decimal amount

    Returns:
        _type_: _description_
    """
    factor = 100 if currency.lower() not in zero_decimal_currency else 1
    return int(amount * factor)


@dataclass
class StripeProductData:
    name: str
    description: Optional[str] = field(init=False, repr=False, default=None)
    images: Optional[str] = field(init=False, repr=False, default=None)
    metadata: Optional[dict] = field(init=False, repr=False, default=None)
    tax_code: Optional[str] = field(init=False, repr=False, default=None)


@dataclass
class StripePriceData:
    currency: str
    product_data: StripeProductData
    unit_amount: int
    recurring: Optional[dict] = field(init=False, repr=False, default=None)
    tax_behavior: Optional[str] = field(init=False, repr=False, default=None)


@dataclass
class StripeLineItem:
    price_data: StripePriceData
    quantity: int
    adjustable_quantity: Optional[dict] = field(init=False, repr=False, default=None)
    dynamic_tax_rates: Optional[dict] = field(init=False, repr=False, default=None)
    tax_rates: Optional[str] = field(init=False, repr=False, default=None)


zero_decimal_currency = [
    "bif",
    "clp",
    "djf",
    "gnf",
    "jpy",
    "kmf",
    "krw",
    "mga",
    "pyg",
    "rwf",
    "ugx",
    "vnd",
    "vuv",
    "xaf",
    "xof",
    "xpf",
]


class StripeCheckoutProvider(BasicProvider):
    """StripeCheckoutProvider

    StripeCheckoutProvider for Stripe Checkout payments
    it handles:

    - Creating a Checkout Session

    - Refunding payment

    - Process payment confirmation with callback

    Args:
        secret_key (string): Your stripe secret_key
    """

    def __init__(self, secret_key, **kwargs):
        super().__init__(**kwargs)
        self.secret_key = secret_key

    def process_payment(self, payment):
        """process_payment

        Process payment instance via StripeCheckoutProvider

        Args:
            payment (payment): Your app payment instance

        """
        if payment.transaction_id:
            raise PaymentError("This payment has already been processed.")
        stripe.api_key = self.secret_key
        session_data = {
            "line_items": self.get_line_items(payment),
            "mode": "payment",
            "success_url": payment.success_url,
            "cancel_url": payment.failure_url,
            "client_reference_id": payment.pk,
        }
        # Patch session with billing email if exists
        if payment.billing_email:
            session_data["customer_email"] = payment.billing_email
        try:
            session = stripe.checkout.Session.create(**session_data)
            payment.transaction_id = session.get("id", None)
            payment.extra_data["session"] = session
            payment.save(update_fields=["extra_data", "transaction_id"])
            return session

        except stripe.error.StripeError as e:
            raise PaymentError(e) from e

    def refund(self, payment, amount=None):
        """refund

        Refund payment instance

        Args:
            payment (payment): Your payment instance
            amount (int, optional): Amount to refund. Defaults to None.

        """
        if payment.status == PaymentStatus.CONFIRMED.name:
            to_refund = amount or payment.total
            payment_intent = payment.extra_data.get("session", {}).get("payment_intent", None)
            if not payment_intent:
                raise PaymentError("Can't Refund, payment_intent does not exist")
            stripe.api_key = self.secret_key
            try:
                refund = stripe.Refund.create(
                    payment_intent=payment_intent,
                    amount=convert_amount(payment.currency, to_refund),
                    reason="requested_by_customer",
                )
            except stripe.error.StripeError as e:
                raise PaymentError(e) from e
            else:
                payment.extra_data["refund"] = refund
                payment.status = PaymentStatus.REFUNDED.name
                payment.save(update_fields=["extra_data", "status"])

                return convert_amount(payment.currency, to_refund)

        raise PaymentError("Only Confirmed payments can be refunded")

    def get_line_items(self, payment):
        """get_line_items

        Construct `line_items` from payment

        Args:
            payment (payment): Your payment instance

        """
        order_no = payment.pk
        product_data = StripeProductData(name=f"Order #{order_no}")

        price_data = StripePriceData(
            currency=payment.currency.lower(),
            unit_amount=convert_amount(payment.currency, payment.total),
            product_data=product_data,
        )
        line_item = StripeLineItem(
            quantity=1,
            price_data=price_data,
        )
        return [asdict(line_item)]


class StripeProvider(BasicProvider):
    """StripeProvider
    Creating payment based on `payment_method` created on FE part

    it handles:

    - Creating a payment intent

    - Refunding payment

    - Receiving payment confirmation with callback

    Args:
        secret_key (string): Your stripe secret_key
        public_key (string): Your stripe public_key
    """

    def __init__(self, secret_key, public_key, **kwargs):
        super().__init__(**kwargs)
        self.secret_key = secret_key
        self.public_key = public_key

    def process_payment(self, payment):
        """process_payment

        Process payment, require `payment_method.id` that should be generated on client side and
        passed in payment.transaction_id

        Args:
            payment (payment): Payment instance
        """
        stripe.api_key = self.secret_key
        # * Create payment intent with payment method generated on FE
        intent_data = {
            "payment_method": payment.transaction_id,
            "amount": int(payment.total * 100),
            "currency": payment.currency,
            "confirmation_method": "automatic",
            "confirm": True,
            "metadata": {"order_no": payment.pk},
        }
        try:
            payment_intent = stripe.PaymentIntent.create(**intent_data)
        except stripe.error.StripeError as e:
            raise PaymentError(e) from e
        payment.extra_data["payment_intent"] = payment_intent
        # * Switching transaction id to payment intent_id
        payment.transaction_id = payment_intent.get("id", None)
        payment.save(update_fields=["extra_data", "transaction_id"])

    def refund(self, payment, amount=None):
        """refund

        Refund payment instance

        Args:
            payment (payment): Your payment instance
            amount (int, optional): Amount to refund. Defaults to None.

        """
        if payment.status == PaymentStatus.CONFIRMED.name:
            to_refund = amount or payment.total
            payment_intent = payment.extra_data.get("payment_intent", None).get("id", None)
            if not payment_intent:
                raise PaymentError("Can't Refund, payment_intent does not exist")
            stripe.api_key = self.secret_key
            try:
                refund = stripe.Refund.create(
                    payment_intent=payment_intent,
                    amount=convert_amount(payment.currency, to_refund),
                    reason="requested_by_customer",
                )
            except stripe.error.StripeError as e:
                raise PaymentError(e) from e
            else:
                payment.extra_data["refund"] = refund
                payment.status = PaymentStatus.REFUNDED.name
                payment.save(update_fields=["extra_data", "status"])
                return convert_amount(payment.currency, to_refund)

        raise PaymentError("Only Confirmed payments can be refunded")
