from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, views
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

import drf_payments
from drf_payments import get_payment_model, get_payment_service
from drf_payments.constants import PaymentStatus


class PaymentSerializerMixin(serializers.ModelSerializer):
    """PaymentSerializerMixin

    Should be used on your payment model, will handle payment related flow on creation of Payment Instance

    """

    card = serializers.CharField(required=False, write_only=True)
    card_expiration = serializers.CharField(required=False, write_only=True)
    card_cvv = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = get_payment_model()
        fields = "__all__"
        read_only_fields = ["status", "extra_data"]

    def validate(self, attrs):
        # * In case of authorizenet provider we must provide card data
        if self.initial_data.get("variant") == "authorizenet" and all(
            key not in attrs for key in ["card", "card_cvv", "card_expiration"]
        ):
            raise serializers.ValidationError("Card, card_expiration, card_cvv are required when using authorizenet")
        return super().validate(attrs)

    def create(self, validated_data):
        # * Move card data to extra data field in case of authorizenet provider
        if validated_data["variant"] == "authorizenet":
            validated_data["extra_data"] = {
                "card": {
                    "x_card_num": validated_data.pop("card"),
                    "x_card_code": validated_data.pop("card_cvv"),
                    "x_exp_date": validated_data.pop("card_expiration"),
                },
            }
        instance = super().create(validated_data)
        service = get_payment_service(instance.variant)
        service.process_payment(instance)
        return instance

    # ? Adding payment url from extra_data
    def to_representation(self, instance):
        """
        Override the default representation of the instance object to include the payment urls
        """
        data = super().to_representation(instance)
        if instance.variant == "stripe" and isinstance(
            get_payment_service(instance.variant),
            drf_payments.stripe.StripeCheckoutProvider,
        ):
            data["url"] = instance.extra_data["session"]["url"]
        # * In case of paypal we return url for checkout form
        if instance.variant == "paypal" and isinstance(
            get_payment_service(instance.variant),
            drf_payments.paypal.PaypalProvider,
        ):
            data["url"] = instance.extra_data["order"]["links"][1]["href"]
        return data


class PaymentViewMixin(ModelViewSet):
    "Add custom method for payment instance based on variant"
    serializer_class = PaymentSerializerMixin
    queryset = get_payment_model().objects.all()

    @action(detail=True, methods=["POST"])
    def refund(self, request, pk):
        payment = get_object_or_404(get_payment_model())
        try:
            get_payment_service(payment.variant).refund(payment)
        except Exception as e:
            return Response(data={"error": str(e)}, status=400)
        return Response(data=self.serializer_class(payment).data, status=200)


class PaymentCallbackSerializerMixin(serializers.Serializer):
    """
    StripeCheckoutProvider

    success stripe checkout session send 4 events:

    payment_intent.created

    charge.succeeded

    payment_intent.succeeded

    checkout.session.completed

    We will capture checkout.session.completed and modify our payment model data.
    example data:
    ```
    StripeProvider

    Send 3 events:

    payment_intent.created

    charge.succeeded

    payment_intent.succeeded

    PayPalProvider

    Send event

    CHECKOUT.ORDER.APPROVED


    """

    def create(self, validated_data):
        event = self.context.get("request", None).data
        # * Stripe checkout session hook
        if event.get("type") == "checkout.session.completed":
            payment_id = event["data"]["object"].get("client_reference_id")
            status = event["data"]["object"]["payment_status"]
            if status == "paid":
                try:
                    self._change_payment_status(payment_id, event, "session")
                except Exception as e:
                    raise serializers.ValidationError(f"Payment with id {payment_id} not found") from e
        # * Stripe payment  hook
        if event.get("type") == "payment_intent.succeeded":
            payment_id = event["data"]["object"].get("metadata", {}).get("order_no", None)
            status = event["data"]["object"]["status"]
            if status == "succeeded":
                try:
                    self._change_payment_status(payment_id, event, "payment_intend")
                except Exception as e:
                    raise serializers.ValidationError(f"Payment with id {payment_id} not found") from e
        # * Paypal hook
        if event.get("event_type") == "CHECKOUT.ORDER.APPROVED":
            payment_id = event.get("resource", {}).get("id")
            status = event.get("resource", {}).get("status")
            # * Upon checkout approval we change status and capture payment
            if status == "APPROVED":
                try:
                    payment = get_payment_model().objects.get(transaction_id=payment_id)
                    payment.status = PaymentStatus.CONFIRMED.name
                    payment.extra_data["order"] = event.get("resource", {})
                    payment.save(update_fields=["status", "extra_data"])
                    get_payment_service("paypal").capture(payment)
                except Exception as e:
                    raise serializers.ValidationError(f"Payment with id {payment_id} not found") from e
        # * Braintree webhook
        if "bt_signature" in event:
            bt = get_payment_service("braintree")
            try:
                result = bt.service.webhook_notification.parse(event["bt_signature"], event["bt_payload"])
            except Exception as e:
                raise serializers.ValidationError(f"Can't parse event {e}") from e
            try:
                payment = get_payment_model().objects.get(transaction_id=result.transaction.id)
                data = bt._serialize(bt.service.transaction.find(result.transaction.id).__dict__)
                payment.extra_data["transaction"] = data
                payment.status = PaymentStatus.CONFIRMED.name
                payment.save(update_fields=["status", "extra_data"])
            except Exception as e:
                raise serializers.ValidationError(f"Can't find payment {result.transaction.id}") from e
        return validated_data

    @staticmethod
    def _change_payment_status(payment_id, event, data):
        payment = get_payment_model().objects.get(pk=payment_id)
        payment.status = PaymentStatus.CONFIRMED.name
        payment.extra_data[data] = event["data"]["object"]
        payment.save(update_fields=["status", "extra_data"])

    def to_representation(self, instance):
        return {"message": "Your payment was successful"}


class PaymentCallbackView(generics.CreateAPIView):
    """Override your serializer_class"""

    serializer_class = PaymentCallbackSerializerMixin
    permission_classes = (AllowAny,)


class PaymentSettingsView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        try:
            token = get_payment_service("braintree").get_client_token()
        except Exception:
            return Response(status=400)

        return Response(status=200, data={"client_token": token})
