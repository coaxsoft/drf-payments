import os
from unittest.mock import patch

import requests
import stripe
from django.test import TestCase, override_settings
from django.urls import reverse

from drf_payments import get_payment_service
from drf_payments.constants import PaymentError, PaymentStatus

from .models import Payment

PAYMENT_MODEL = Payment


# * Changing stripe from checkout to regular payments
@override_settings(
    PAYMENT_VARIANTS={
        "stripe": (
            "drf_payments.stripe.StripeProvider",
            {
                "secret_key": os.environ.get("STRIPE_SECRET_KEY"),
                "public_key": os.environ.get("STRIPE_PUBLIC_KEY"),
            },
        ),
    },
)
class StripeChargePaymentTestCase(TestCase):
    def setUp(self):
        self.list_url = reverse("shop:payment-list")
        self.data = {"variant": "stripe", "total": 200, "use_token": False}
        self.payment = PAYMENT_MODEL.objects.create(
            variant="stripe",
            total=200,
            transaction_id="dummyId",
            extra_data={"session": "dummy_data"},
        )
        self.success_charge_event = {
            "id": "evt_3NJbGLDUbh92Jp783p8EKmrI",
            "object": "event",
            "api_version": "2022-11-15",
            "created": 1686916582,
            "data": {
                "object": {
                    "id": "pi_3NJbGLDUbh92Jp783euZaQSm",
                    "object": "payment_intent",
                    "amount": 20000,
                    "amount_capturable": 0,
                    "amount_details": {"tip": {}},
                    "amount_received": 20000,
                    "application": None,
                    "application_fee_amount": None,
                    "automatic_payment_methods": None,
                    "canceled_at": None,
                    "cancellation_reason": None,
                    "capture_method": "automatic",
                    "client_secret": "pi_3NJbGLDUbh92Jp783euZaQSm_secret_Cdl35JdEPPnrOVraXHD8d39UL",
                    "confirmation_method": "automatic",
                    "created": 1686916581,
                    "currency": "usd",
                    "customer": None,
                    "description": None,
                    "invoice": None,
                    "last_payment_error": None,
                    "latest_charge": "ch_3NJbGLDUbh92Jp78371X13qU",
                    "livemode": False,
                    "metadata": {"order_no": self.payment.id},
                    "next_action": None,
                    "on_behalf_of": None,
                    "payment_method": "pm_1NJbGLDUbh92Jp78PFXF2Ovv",
                    "payment_method_options": {
                        "card": {
                            "installments": None,
                            "mandate_options": None,
                            "network": None,
                            "request_three_d_secure": "automatic",
                        },
                    },
                    "payment_method_types": ["card"],
                    "processing": None,
                    "receipt_email": None,
                    "review": None,
                    "setup_future_usage": None,
                    "shipping": None,
                    "source": None,
                    "statement_descriptor": None,
                    "statement_descriptor_suffix": None,
                    "status": "succeeded",
                    "transfer_data": None,
                    "transfer_group": None,
                },
            },
            "livemode": False,
            "pending_webhooks": 3,
            "request": {"id": "req_smsonnhQrLMsEk", "idempotency_key": "cc39e207-ee68-49e9-9298-7e0ac2a20df4"},
            "type": "payment_intent.succeeded",
        }
        self.refund_created = {
            "id": "re_3NH0d2DUbh92Jp783eJpNpFj",
            "object": "refund",
            "amount": 20000,
            "payment_intent": "pi_3NH0d2DUbh92Jp783aAisgs6",
            "reason": "requested_by_customer",
            "status": "succeeded",
            "balance_transaction": "txn_3NH0d2DUbh92Jp783utPzsTE",
            "charge": "ch_3NH0d2DUbh92Jp7834gwlUPU",
            "created": 1686304384,
            "currency": "usd",
            "metadata": {},
            "receipt_number": None,
            "source_transfer_reversal": None,
            "transfer_reversal": None,
        }

    @patch("stripe.PaymentIntent.create")
    def test_create_payment_stripe(self, mock_charge):
        """
        We should have payment_method id when submitting post request
        can be obtained like this
        ```python
        stripe.api_key = os.environ.get("STRIPE_PUBLIC_KEY")
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2025,
                "cvc": "314",
            },
        )
        ```
        """
        data = self.data.copy()
        data["transaction_id"] = "pm_12bc"
        mock_charge.return_value = self.success_charge_event["data"]["object"]
        resp = self.client.post(self.list_url, data)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.WAITING.name)
        self.assertEqual(resp.status_code, 201)

    def test_success_callback(self):
        resp = self.client.post(
            reverse("payment-callback"),
            data=self.success_charge_event,
            content_type="application/json",
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.CONFIRMED.name)
        # Updates payment_method data in DB
        self.assertEqual(self.payment.extra_data["payment_intend"], self.success_charge_event["data"]["object"])
        self.assertEqual(resp.status_code, 201)

    def test_failed_callback(self):
        data = self.success_charge_event.copy()
        data["data"]["object"]["status"] = "failed"
        resp = self.client.post(
            reverse("payment-callback"),
            data=data,
            content_type="application/json",
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.WAITING.name)
        # Updates payment_method data in DB
        self.assertEqual(resp.status_code, 201)

    def test_missing_id_callback(self):
        payload = self.success_charge_event.copy()
        payload["data"]["object"]["metadata"]["order_no"] = 0
        resp = self.client.post(
            reverse("payment-callback"),
            data=self.success_charge_event,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("stripe.Refund.create")
    def test_refund_confirmed(self, mock_refund):
        mock_refund.return_value = self.refund_created
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.extra_data["payment_intent"] = self.success_charge_event["data"]["object"]
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 200)

    @patch("stripe.Refund.create")
    def test_refund_fail(self, mock_refund):
        mock_refund.return_value = self.refund_created
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.extra_data["payment_intent"] = {}
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    @patch("stripe.Refund.create")
    def test_refund_already_refunded(self, mock_refund):
        mock_refund.side_effect = stripe.error.StripeError(message="already_refunded")
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.extra_data["payment_intent"] = self.success_charge_event["data"]["object"]
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    def test_refund_not_confirmed(self):
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    def test_already_processed(self):
        with self.assertRaises(PaymentError):
            get_payment_service("stripe").process_payment(self.payment)


@override_settings(
    PAYMENT_VARIANTS={
        "stripe": (
            "drf_payments.stripe.StripeCheckoutProvider",
            {
                "secret_key": os.environ.get("STRIPE_SECRET_KEY"),
                "public_key": os.environ.get("STRIPE_PUBLIC_KEY"),
            },
        ),
    },
)
class StripeCheckoutPaymentTestCase(TestCase):
    def setUp(self):
        self.list_url = reverse("shop:payment-list")
        self.data = {"variant": "stripe", "total": 200, "billing_email": "customer@example.com"}
        self.payment = PAYMENT_MODEL.objects.create(
            variant="stripe",
            total=200,
            transaction_id="dummyId",
            extra_data={"session": "dummy_data"},
        )
        self.success_checkout_event = {
            "id": "evt_1NH0d3DUbh92Jp78NMwfLhn4",
            "object": "event",
            "api_version": "2022-11-15",
            "created": 1686299105,
            "data": {
                "object": {
                    "id": "cs_test_a1tRvrAvKSR7hNUP9dS7X3hVmDnrlwTS9d9E93YEXGjpaOEQWOqMwzazZm",
                    "object": "checkout.session",
                    "after_expiration": None,
                    "allow_promotion_codes": None,
                    "amount_subtotal": 20000,
                    "amount_total": 20000,
                    "automatic_tax": {"enabled": False, "status": None},
                    "billing_address_collection": None,
                    "cancel_url": "http://localhost:3000/payments/failure/",
                    "client_reference_id": self.payment.id,
                    "consent": None,
                    "consent_collection": None,
                    "created": 1686299007,
                    "currency": "usd",
                    "currency_conversion": None,
                    "custom_fields": [],
                    "custom_text": {"shipping_address": None, "submit": None},
                    "customer": None,
                    "customer_creation": "if_required",
                    "customer_details": {
                        "address": {
                            "city": None,
                            "country": "UA",
                            "line1": None,
                            "line2": None,
                            "postal_code": None,
                            "state": None,
                        },
                        "email": "test@gmail.com",
                        "name": "test",
                        "phone": None,
                        "tax_exempt": "none",
                        "tax_ids": [],
                    },
                    "customer_email": None,
                    "expires_at": 1686385407,
                    "invoice": None,
                    "invoice_creation": {
                        "enabled": False,
                        "invoice_data": {
                            "account_tax_ids": None,
                            "custom_fields": None,
                            "description": None,
                            "footer": None,
                            "metadata": {},
                            "rendering_options": None,
                        },
                    },
                    "livemode": False,
                    "locale": None,
                    "metadata": {},
                    "mode": "payment",
                    "payment_intent": "pi_3NH0d2DUbh92Jp783aAisgs6",
                    "payment_link": None,
                    "payment_method_collection": "always",
                    "payment_method_options": {},
                    "payment_method_types": ["card", "link", "cashapp"],
                    "payment_status": "paid",
                    "phone_number_collection": {"enabled": False},
                    "recovered_from": None,
                    "setup_intent": None,
                    "shipping_address_collection": None,
                    "shipping_cost": None,
                    "shipping_details": None,
                    "shipping_options": [],
                    "status": "complete",
                    "submit_type": None,
                    "subscription": None,
                    "success_url": "http://localhost:3000/payments/success/",
                    "total_details": {"amount_discount": 0, "amount_shipping": 0, "amount_tax": 0},
                    "url": None,
                },
            },
            "livemode": False,
            "pending_webhooks": 3,
            "request": {"id": None, "idempotency_key": None},
            "type": "checkout.session.completed",
        }
        self.refund_created = {
            "id": "re_3NH0d2DUbh92Jp783eJpNpFj",
            "object": "refund",
            "amount": 20000,
            "payment_intent": "pi_3NH0d2DUbh92Jp783aAisgs6",
            "reason": "requested_by_customer",
            "status": "succeeded",
            "balance_transaction": "txn_3NH0d2DUbh92Jp783utPzsTE",
            "charge": "ch_3NH0d2DUbh92Jp7834gwlUPU",
            "created": 1686304384,
            "currency": "usd",
            "metadata": {},
            "receipt_number": None,
            "source_transfer_reversal": None,
            "transfer_reversal": None,
        }

    @patch("stripe.checkout.Session.create")
    def test_create_payment_stripe(self, mock_session):
        mock_session.return_value = self.success_checkout_event["data"]["object"]
        resp = self.client.post(self.list_url, self.data)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.WAITING.name)
        self.assertEqual(resp.status_code, 201)

    @patch("stripe.checkout.Session.create")
    def test_create_payment_stripe_error(self, mock_session):
        mock_session.side_effect = stripe.error.StripeError("test error")
        with self.assertRaises(PaymentError):
            self.client.post(self.list_url, self.data)

    @patch("stripe.checkout.Session.create")
    def test_create_payment_stripe_no_billing_email(self, mock_session):
        data = self.data.copy()
        data.pop("billing_email")
        mock_session.return_value = self.success_checkout_event["data"]["object"]
        resp = self.client.post(self.list_url, data)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.WAITING.name)
        self.assertEqual(resp.status_code, 201)

    def test_success_callback(self):
        resp = self.client.post(
            reverse("payment-callback"),
            data=self.success_checkout_event,
            content_type="application/json",
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.CONFIRMED.name)
        # Updates session data in DB
        self.assertEqual(self.payment.extra_data["session"], self.success_checkout_event["data"]["object"])
        self.assertEqual(resp.status_code, 201)

    def test_failed_callback(self):
        data = self.success_checkout_event.copy()
        data["data"]["object"]["payment_status"] = "failed"
        resp = self.client.post(
            reverse("payment-callback"),
            data=data,
            content_type="application/json",
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.WAITING.name)
        # Updates session data in DB
        self.assertEqual(resp.status_code, 201)

    def test_missing_id_callback(self):
        payload = self.success_checkout_event.copy()
        payload["data"]["object"]["client_reference_id"] = 0
        resp = self.client.post(
            reverse("payment-callback"),
            data=self.success_checkout_event,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_refund_not_confirmed(self):
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    # mock refund
    @patch("stripe.Refund.create")
    def test_refund_confirmed(self, mock_refund):
        mock_refund.return_value = self.refund_created
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.extra_data["session"] = self.success_checkout_event["data"]["object"]
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 200)

    # mock already refunded error
    @patch("stripe.Refund.create")
    def test_refund_already_refunded(self, mock_refund):
        mock_refund.side_effect = stripe.error.StripeError(message="already_refunded")
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.extra_data["session"] = self.success_checkout_event["data"]["object"]
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    @patch("stripe.Refund.create")
    def test_refund_missing_payment_intent(self, mock_refund):
        mock_refund.return_value = self.refund_created
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.extra_data = {}
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    def test_already_processed(self):
        with self.assertRaises(PaymentError):
            get_payment_service("stripe").process_payment(self.payment)


class BraintreeChargePaymentTestCase(TestCase):
    def setUp(self):
        self.list_url = reverse("shop:payment-list")
        self.data = {
            "variant": "braintree",
            "total": 200,
            "billing_email": "customer_email@example.com",
            "transaction_id": "fake-valid-nonce",
        }
        self.payment = PAYMENT_MODEL.objects.create(variant="braintree", total=200, transaction_id="1")
        self.event = {
            "id": "1n2q9wsg",
            "status": "submitted_for_settlement",
            "type": "sale",
            "currency_iso_code": "USD",
            "amount": "200.00",
            "amount_requested": "200.00",
            "merchant_account_id": "test",
            "sub_merchant_account_id": None,
            "master_merchant_account_id": None,
            "order_id": None,
            "created_at": "2023-06-30 09:52:13",
            "updated_at": "2023-06-30 09:52:13",
            "customer": {
                "id": None,
                "first_name": None,
                "last_name": None,
                "company": None,
                "email": None,
                "website": None,
                "phone": None,
                "fax": None,
            },
            "billing": {
                "id": None,
                "first_name": None,
                "last_name": None,
                "company": None,
                "street_address": None,
                "extended_address": None,
                "locality": None,
                "region": None,
                "postal_code": "94107",
                "country_name": None,
                "country_code_alpha2": None,
                "country_code_alpha3": None,
                "country_code_numeric": None,
            },
            "refund_id": None,
            "refund_ids": [],
            "refunded_transaction_id": None,
            "partial_settlement_transaction_ids": [],
            "authorized_transaction_id": None,
            "settlement_batch_id": None,
            "shipping": {
                "id": None,
                "first_name": None,
                "last_name": None,
                "company": None,
                "street_address": None,
                "extended_address": None,
                "locality": None,
                "region": None,
                "postal_code": None,
                "country_name": None,
                "country_code_alpha2": None,
                "country_code_alpha3": None,
                "country_code_numeric": None,
            },
            "custom_fields": "",
            "account_funding_transaction": False,
            "avs_error_response_code": None,
            "avs_postal_code_response_code": "M",
            "avs_street_address_response_code": "I",
            "cvv_response_code": "M",
            "gateway_rejection_reason": None,
            "processor_authorization_code": "TNVKD7",
            "processor_response_code": "1000",
            "processor_response_text": "Approved",
            "additional_processor_response": None,
            "voice_referral_number": None,
            "purchase_order_number": None,
            "tax_amount": None,
            "tax_exempt": False,
            "sca_exemption_requested": None,
            "processed_with_network_token": False,
            "credit_card": {
                "token": None,
                "bin": "401288",
                "last_4": "1881",
                "card_type": "Visa",
                "expiration_month": "12",
                "expiration_year": "2024",
                "customer_location": "US",
                "cardholder_name": None,
                "image_url": "https://assets.braintreegateway.com/payment_method_logo/visa.png?environment=sandbox",
                "is_network_tokenized": False,
                "prepaid": "No",
                "healthcare": "Unknown",
                "debit": "Unknown",
                "durbin_regulated": "Unknown",
                "commercial": "Unknown",
                "payroll": "Unknown",
                "issuing_bank": "Unknown",
                "country_of_issuance": "Unknown",
                "product_id": "Unknown",
                "global_id": None,
                "account_type": "credit",
                "unique_number_identifier": None,
                "venmo_sdk": False,
                "account_balance": None,
            },
            "plan_id": None,
            "subscription_id": None,
            "subscription": {"billing_period_end_date": None, "billing_period_start_date": None},
            "add_ons": [],
            "discounts": [],
            "recurring": False,
            "channel": None,
            "service_fee_amount": None,
            "escrow_status": None,
            "disputes": [],
            "ach_return_responses": [],
            "authorization_adjustments": [],
            "payment_instrument_type": "credit_card",
            "processor_settlement_response_code": "",
            "processor_settlement_response_text": "",
            "network_response_code": "XX",
            "network_response_text": "sample network response text",
            "merchant_advice_code": None,
            "merchant_advice_code_text": None,
            "three_d_secure_info": None,
            "ships_from_postal_code": None,
            "shipping_amount": None,
            "discount_amount": None,
            "network_transaction_id": "020230630095213",
            "processor_response_type": "approved",
            "authorization_expires_at": "2023-07-07 09:52:13",
            "retry_ids": [],
            "retried_transaction_id": None,
            "refund_global_ids": [],
            "partial_settlement_transaction_global_ids": [],
            "refunded_transaction_global_id": None,
            "authorized_transaction_global_id": None,
            "global_id": "dHJhbnNhY3Rpb25fMW4ycTl3c2c",
            "graphql_id": "dHJhbnNhY3Rpb25fMW4ycTl3c2c",
            "retry_global_ids": [],
            "retried_transaction_global_id": None,
            "retrieval_reference_number": "1234567",
            "ach_return_code": None,
            "installment_count": None,
            "installments": [],
            "refunded_installments": [],
            "response_emv_data": None,
            "acquirer_reference_number": None,
            "merchant_identification_number": "123456789012",
            "terminal_identification_number": "00000001",
            "merchant_name": "DESCRIPTORNAME",
            "merchant_address": {
                "street_address": "",
                "locality": "Braintree",
                "region": "MA",
                "postal_code": "02184",
                "phone": "5555555555",
            },
            "pin_verified": False,
            "debit_network": None,
            "processing_mode": None,
            "payment_receipt": {
                "id": "1n2q9wsg",
                "global_id": "dHJhbnNhY3Rpb25fMW4ycTl3c2c",
                "amount": "200.00",
                "currency_iso_code": "USD",
                "processor_response_code": "1000",
                "processor_response_text": "Approved",
                "processor_authorization_code": "TNVKD7",
                "merchant_name": "DESCRIPTORNAME",
                "merchant_address": {
                    "street_address": "",
                    "locality": "Braintree",
                    "region": "MA",
                    "postal_code": "02184",
                    "phone": "5555555555",
                },
                "merchant_identification_number": "123456789012",
                "terminal_identification_number": "00000001",
                "type": "sale",
                "pin_verified": False,
                "processing_mode": None,
                "network_identification_code": None,
                "card_type": "Visa",
                "card_last_4": "1881",
                "account_balance": None,
            },
            "risk_data": None,
        }

    @patch("drf_payments.BraintreeProvider")
    def test_token(self, mock_service):
        mock_service.service.client_token.generate.return_value = "DummyToken"
        get_payment_service("braintree").get_client_token()

    @patch("drf_payments.BraintreeProvider.get_client_token")
    def test_get_braintree_setting(self, mock):
        mock.return_value = "Dummy_token"
        resp = self.client.get(reverse("braintree-settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue("client_token" in resp.data)

    @patch("drf_payments.BraintreeProvider._serialize")
    @patch("braintree.BraintreeGateway")
    def test_create_payment(self, mock, serialize):
        mock.return_value.transaction.sale.return_value.transaction.id = 20
        serialize.return_value = {"id": 20}
        resp = self.client.post(self.list_url, self.data)
        payment = PAYMENT_MODEL.objects.last()
        self.assertEqual(payment.status, PaymentStatus.WAITING.name)

        self.assertEqual(resp.status_code, 201)

    def test_create_payment_mock_for_serialize(self):
        get_payment_service("braintree")._serialize(self.event)

    @patch("drf_payments.BraintreeProvider._serialize")
    @patch("braintree.BraintreeGateway")
    def test_create_payment_exception(self, mock, serialize):
        mock.return_value.transaction.sale.side_effect = Exception
        with self.assertRaises(Exception):
            self.client.post(self.list_url, self.data)

    @override_settings(
        PAYMENT_VARIANTS={
            "braintree": (
                "drf_payments.braintree.BraintreeProvider",
                {
                    "merchant_id": os.environ.get("BRAINTREE_MERCHANT_ID"),
                    "public_key": os.environ.get("BRAINTREE_PUBLIC_KEY"),
                    "private_key": os.environ.get("BRAINTREE_PRIVATE_KEY"),
                    "sandbox": False,
                },
            ),
        },
    )
    @patch("drf_payments.BraintreeProvider._serialize")
    @patch("braintree.BraintreeGateway")
    def test_create_payment_no_sandbox(self, mock, serialize):
        mock.return_value.transaction.sale.return_value.transaction.id = 20
        serialize.return_value = {"id": 20}
        resp = self.client.post(self.list_url, self.data)
        payment = PAYMENT_MODEL.objects.last()
        self.assertEqual(payment.status, PaymentStatus.WAITING.name)
        self.assertEqual(resp.status_code, 201)

    @patch("drf_payments.BraintreeProvider._serialize")
    @patch("braintree.BraintreeGateway")
    def test_webhook_success(self, mock, serialize):
        serialize.return_value = {"id": 20}
        payment = PAYMENT_MODEL.objects.last()
        mock.return_value.webhook_notification.parse.return_value.transaction.id = 20
        payment.transaction_id = 20
        payment.save()
        payload = {"bt_signature": "DummySignature", "bt_payload": "DummyPayload"}
        resp = self.client.post(
            reverse("payment-callback"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CONFIRMED.name)

    @patch("braintree.BraintreeGateway")
    def test_webhook_wrong_id(self, mock):
        mock.return_value.webhook_notification.parse.return_value.transaction.id = 20
        payload = {"bt_signature": "DummySignature", "bt_payload": "DummyPayload"}
        resp = self.client.post(
            reverse("payment-callback"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("braintree.BraintreeGateway")
    def test_refund_confirmed(self, mock):
        mock.return_value.transaction.refund.return_value.transaction.id = 20
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 200)

    @patch("braintree.BraintreeGateway")
    def test_refund_error(self, mock):
        mock.return_value.transaction.refund.side_effect = Exception
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    def test_refund_not_confirmed(self):
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)


class PaypalCheckoutPaymentTestCase(TestCase):
    def setUp(self):
        self.list_url = reverse("shop:payment-list")
        self.data = {"variant": "paypal", "total": 200, "billing_email": "customer_email@example.com"}
        self.payment = PAYMENT_MODEL.objects.create(
            variant="paypal",
            total=200,
            extra_data={"order": {"id": "9EW16729JN210181D"}},
        )
        self.successful_checkout_session = {
            "id": "9EW16729JN210181D",
            "status": "CREATED",
            "links": [
                {
                    "href": "https://api.sandbox.paypal.com/v2/checkout/orders/57P96319U8590230E",
                    "rel": "self",
                    "method": "GET",
                },
                {
                    "href": "https://www.sandbox.paypal.com/checkoutnow?token=57P96319U8590230E",
                    "rel": "approve",
                    "method": "GET",
                },
                {
                    "href": "https://api.sandbox.paypal.com/v2/checkout/orders/57P96319U8590230E",
                    "rel": "update",
                    "method": "PATCH",
                },
                {
                    "href": "https://api.sandbox.paypal.com/v2/checkout/orders/57P96319U8590230E/capture",
                    "rel": "capture",
                    "method": "POST",
                },
            ],
        }
        self.success_checkout_event = {
            "id": "WH-50F982379F838005B-4SC708914G302751R",
            "event_version": "1.0",
            "create_time": "2023-06-20T07:37:02.475Z",
            "resource_type": "checkout-order",
            "resource_version": "2.0",
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "summary": "An order has been approved by buyer",
            "resource": {
                "create_time": "2023-06-20T07:36:02Z",
                "purchase_units": [
                    {
                        "reference_id": "default",
                        "amount": {"currency_code": "USD", "value": "200.00"},
                        "payee": {
                            "email_address": "sb-9vfxd26351007@business.example.com",
                            "merchant_id": "ASDASD",
                        },
                        "shipping": {
                            "name": {"full_name": "John Doe"},
                            "address": {
                                "address_line_1": "1 Main St",
                                "admin_area_2": "San Jose",
                                "admin_area_1": "CA",
                                "postal_code": "95131",
                                "country_code": "US",
                            },
                        },
                    },
                ],
                "links": [
                    {
                        "href": "https://api.sandbox.paypal.com/v2/checkout/orders/0RY11163YP699884H",
                        "rel": "self",
                        "method": "GET",
                    },
                    {
                        "href": "https://api.sandbox.paypal.com/v2/checkout/orders/0RY11163YP699884H",
                        "rel": "update",
                        "method": "PATCH",
                    },
                    {
                        "href": "https://api.sandbox.paypal.com/v2/checkout/orders/0RY11163YP699884H/capture",
                        "rel": "capture",
                        "method": "POST",
                    },
                ],
                "id": "0RY11163YP699884H",
                "payment_source": {"paypal": {}},
                "intent": "CAPTURE",
                "payer": {
                    "name": {"given_name": "John", "surname": "Doe"},
                    "email_address": "sb-0zm3c763407@personal.example.com",
                    "payer_id": "NM7GXM7D8FAM8",
                    "address": {"country_code": "US"},
                },
                "status": "APPROVED",
            },
            "links": [
                {
                    "href": "https://api.sandbox.paypal.com/v1/notifications/webhooks-events/WH-50F982379F838005B-4SC708914G302751R",
                    "rel": "self",
                    "method": "GET",
                },
                {
                    "href": "https://api.sandbox.paypal.com/v1/notifications/webhooks-events/WH-50F982379F838005B-4SC708914G302751R/resend",
                    "rel": "resend",
                    "method": "POST",
                },
            ],
        }
        self.capture_event = {
            "id": "0RY11163YP699884H",
            "status": "COMPLETED",
            "payment_source": {
                "paypal": {
                    "email_address": "sb-0zm3c763407@personal.example.com",
                    "account_id": "NM7GXM7D8FAM8",
                    "account_status": "VERIFIED",
                    "name": {"given_name": "John", "surname": "Doe"},
                    "address": {"country_code": "US"},
                },
            },
            "purchase_units": [
                {
                    "reference_id": "default",
                    "shipping": {
                        "name": {"full_name": "John Doe"},
                        "address": {
                            "address_line_1": "1 Main St",
                            "admin_area_2": "San Jose",
                            "admin_area_1": "CA",
                            "postal_code": "95131",
                            "country_code": "US",
                        },
                    },
                    "payments": {
                        "captures": [
                            {
                                "id": "7D906882J3054405C",
                                "status": "COMPLETED",
                                "amount": {"currency_code": "USD", "value": "200.00"},
                                "final_capture": True,
                                "seller_protection": {
                                    "status": "ELIGIBLE",
                                    "dispute_categories": ["ITEM_NOT_RECEIVED", "UNAUTHORIZED_TRANSACTION"],
                                },
                                "seller_receivable_breakdown": {
                                    "gross_amount": {"currency_code": "USD", "value": "200.00"},
                                    "paypal_fee": {"currency_code": "USD", "value": "7.47"},
                                    "net_amount": {"currency_code": "USD", "value": "192.53"},
                                },
                                "links": [
                                    {
                                        "href": "https://api.sandbox.paypal.com/v2/payments/captures/7D906882J3054405C",
                                        "rel": "self",
                                        "method": "GET",
                                    },
                                    {
                                        "href": "https://api.sandbox.paypal.com/v2/payments/captures/7D906882J3054405C/refund",
                                        "rel": "refund",
                                        "method": "POST",
                                    },
                                    {
                                        "href": "https://api.sandbox.paypal.com/v2/checkout/orders/0RY11163YP699884H",
                                        "rel": "up",
                                        "method": "GET",
                                    },
                                ],
                                "create_time": "2023-06-20T07:40:05Z",
                                "update_time": "2023-06-20T07:40:05Z",
                            },
                        ],
                    },
                },
            ],
            "payer": {
                "name": {"given_name": "John", "surname": "Doe"},
                "email_address": "sb-0zm7sdad63407@personal.example.com",
                "payer_id": "NM7GXM7D8FAM8",
                "address": {"country_code": "US"},
            },
            "links": [
                {
                    "href": "https://api.sandbox.paypal.com/v2/checkout/orders/0RY11163YP699884H",
                    "rel": "self",
                    "method": "GET",
                },
            ],
        }
        self.refund_create = {
            "id": "381835005N4484450",
            "status": "COMPLETED",
            "links": [
                {
                    "href": "https://api.sandbox.paypal.com/v2/payments/refunds/381835005N4484450",
                    "rel": "self",
                    "method": "GET",
                },
                {
                    "href": "https://api.sandbox.paypal.com/v2/payments/captures/7D906882J3054405C",
                    "rel": "up",
                    "method": "GET",
                },
            ],
        }

    @patch("requests.post")
    def test_create_payment(self, mock_payment):
        response = self.successful_checkout_session
        response["access_token"] = "DummyToken"
        mock_payment.return_value.json.return_value = response
        resp = self.client.post(self.list_url, self.data)
        self.assertEqual(resp.status_code, 201)
        payment = PAYMENT_MODEL.objects.last()
        self.assertEqual(payment.status, PaymentStatus.WAITING.name)
        self.assertEqual(payment.extra_data["order"], response)

    @patch("requests.post")
    def test_create_payment_timeout(self, mock_payment):
        response = self.successful_checkout_session
        response["access_token"] = "DummyToken"
        mock_payment.side_effect = requests.exceptions.RequestException
        with self.assertRaises(requests.exceptions.RequestException):
            resp = self.client.post(self.list_url, self.data)
            self.assertEqual(resp.status_code, 201)
            payment = PAYMENT_MODEL.objects.last()
            self.assertEqual(payment.status, PaymentStatus.WAITING.name)
            self.assertEqual(payment.extra_data["order"], self.successful_checkout_session)

    @patch("requests.post")
    def test_token_error(self, mock_payment):
        mock_payment.return_value.json.return_value = self.successful_checkout_session
        with self.assertRaises(PaymentError):
            self.client.post(self.list_url, self.data)

    @patch("requests.post")
    def test_success_callback(self, mock_token):
        mock_token.return_value.json.return_value = {"access_token": "DummyToken"}
        self.payment.transaction_id = self.success_checkout_event["resource"]["id"]
        self.payment.save()
        resp = self.client.post(
            reverse("payment-callback"),
            data=self.success_checkout_event,
            content_type="application/json",
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.CONFIRMED.name)
        # Updates session data in DB
        self.assertEqual(resp.status_code, 201)

    @patch("requests.post")
    def test_failed_callback(self, mock_token):
        mock_token.return_value.json.return_value = {"access_token": "DummyToken"}
        self.payment.transaction_id = self.success_checkout_event["resource"]["id"]
        self.payment.save()
        data = self.success_checkout_event.copy()
        data["resource"]["status"] = "FAILED"
        resp = self.client.post(
            reverse("payment-callback"),
            data=data,
            content_type="application/json",
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.WAITING.name)
        # Updates session data in DB
        self.assertEqual(resp.status_code, 201)

    @patch("requests.post")
    def test_callback_wrong_id(self, mock_token):
        mock_token.return_value.json.return_value = {"access_token": "DummyToken"}
        self.payment.transaction_id = 0
        self.payment.save()
        data = self.success_checkout_event.copy()
        resp = self.client.post(
            reverse("payment-callback"),
            data=data,
            content_type="application/json",
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.WAITING.name)
        # Updates session data in DB
        self.assertEqual(resp.status_code, 400)

    @patch("requests.post")
    def test_refund_confirmed(self, mock_refund):
        response = self.refund_create
        response["access_token"] = "DummyToken"
        mock_refund.return_value.json.return_value = response
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.extra_data["order"] = self.capture_event
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 200)

    @patch("requests.post")
    def test_refund_missing_data(self, mock_refund):
        response = self.refund_create
        response["access_token"] = "DummyToken"
        mock_refund.return_value.json.return_value = response
        self.payment.status = PaymentStatus.CONFIRMED.name
        self.payment.save()
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    def test_refund_wrong_status(self):
        resp = self.client.post(f"{self.list_url}{self.payment.id}/refund/")
        self.assertEqual(resp.status_code, 400)

    def test_already_processed(self):
        self.payment.transaction_id = 123
        with self.assertRaises(PaymentError):
            get_payment_service("paypal").process_payment(self.payment)


class AuthorizeNetTestCase(TestCase):
    def setUp(self):
        self.list_url = reverse("shop:payment-list")
        self.data = {
            "variant": "authorizenet",
            "total": 200,
            "card": 5424000000000015,
            "card_expiration": "2025-12",
            "card_cvv": 123,
            "billing_email": "customer_email@example.com",
            "transaction_id": "fake-valid-nonce",
        }
        self.payment = PAYMENT_MODEL.objects.create(variant="authorizenet", total=200, transaction_id="1")
        self.successful_transaction = (
            "1|1|1|(TESTMODE) This transaction has been approved.|000000|P|0|||200.00|CC"
            + "|auth_capture|||||,||||||||||||||||||||||||||||||||||XXXX0015|MasterCard|||||||||||||||||2|"
        )

    @patch("requests.post")
    def test_create_payment(self, mock_post):
        mock_post.return_value.text.split.return_value = self.successful_transaction.split("|")
        resp = self.client.post(self.list_url, self.data)
        payment = PAYMENT_MODEL.objects.last()
        self.assertEqual(payment.status, PaymentStatus.CONFIRMED.name)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue("card" in payment.extra_data)

    @patch("requests.post")
    def test_create_payment_failed(self, mock_post):
        failed_data = self.successful_transaction.split("|")
        failed_data[0] = "2"
        mock_post.return_value.text.split.return_value = failed_data

        resp = self.client.post(self.list_url, self.data)
        payment = PAYMENT_MODEL.objects.last()
        self.assertEqual(payment.status, PaymentStatus.REJECTED.name)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue("card" in payment.extra_data)

    @patch("requests.post")
    def test_create_payment_failed_request(self, mock_post):
        mock_post.return_value.text = ""
        with self.assertRaises(PaymentError):
            self.client.post(self.list_url, self.data)

    @patch("requests.post")
    def test_create_payment_response_nok(self, mock_post):
        failed_data = self.successful_transaction.split("|")
        failed_data[0] = False
        mock_post.ok = False
        mock_post.return_value.text.split.return_value = failed_data
        self.client.post(self.list_url, self.data)
