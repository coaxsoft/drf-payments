import base64

import requests
from django.conf import settings

from drf_payments.constants import PaymentError, PaymentStatus
from drf_payments.core import BasicProvider


class PaypalProvider(BasicProvider):
    """PaypalProvider


    it handles:

    - Creating a Checkout Session

    - Refunding payment

    - Process payment confirmation with callback

    Args:
        client_id (string): Your paypal client_id
        secret_key (string): Your paypal secret_key
        endpoint (url): Paypal endpoint sanbox or production
    """

    def __init__(self, client_id, secret_key, endpoint, **kwargs):
        super().__init__(**kwargs)
        self.client_id = client_id
        self.secret_key = secret_key
        self.endpoint = endpoint

    def process_payment(self, payment):
        """process_payment

        Process payment instance via PaypalProvider

        Args:
            payment (payment): Your app payment instance

        """
        if payment.transaction_id:
            raise PaymentError("This payment has already been processed.")
        token = self._create_token()
        payload = {
            "intent": "CAPTURE",
            "application_context": {
                "return_url": settings.PAYMENT_SUCCESS_URL,
                "cancel_url": settings.PAYMENT_FAILURE_URL,
            },
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": payment.currency,
                        "value": float(payment.total),
                    },
                },
            ],
        }
        try:
            resp = requests.post(
                f"{self.endpoint}/v2/checkout/orders",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            ).json()
        except requests.exceptions.RequestException as e:
            raise PaymentError(e) from e
        payment.transaction_id = resp.get("id")
        payment.extra_data["order"] = resp
        payment.save(update_fields=["extra_data", "transaction_id"])

    def _create_token(self) -> str:
        """_create_token

        Method for creating authorization token for PayPal requests

        Returns:
            str: _description_
        """
        token = base64.b64encode(f"{self.client_id}:{self.secret_key}".encode("utf-8")).decode("utf-8")

        if access_token := (
            requests.post(
                f"{self.endpoint}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                headers={"Authorization": f"Basic {token}"},
            )
            .json()
            .get("access_token")
        ):
            return access_token
        else:
            raise PaymentError("Can't create token")

    def refund(self, payment, amount=None):
        """refund

        Refund payment instance

        Args:
            payment (payment): Your payment instance
            amount (int, optional): Amount to refund. Defaults to None.

        """
        if payment.status == PaymentStatus.CONFIRMED.name:
            try:
                capture = payment.extra_data["order"]["purchase_units"][0]["payments"]["captures"][0]["id"]
            except (IndexError, KeyError) as e:
                raise PaymentError("Can't Refund, payment has not been captured yet") from e
            token = self._create_token()
            resp = requests.post(
                f"{self.endpoint}/v2/payments/captures/{capture}/refund",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            ).json()
            payment.extra_data["order"] = resp
            payment.save(update_fields=["extra_data"])
            return
        raise PaymentError("Only Confirmed payments can be refunded")

    def capture(self, payment):
        """capture

        Upon successful checkout we will capture funds to finalize payment and have ability to refund

        Args:
            payment (payment): Your payment
        """
        token = self._create_token()
        resp = requests.post(
            f"{self.endpoint}/v2/checkout/orders/{payment.transaction_id}/capture",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        ).json()
        payment.extra_data["order"] = resp
        payment.save(update_fields=["extra_data"])
