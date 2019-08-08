from typing import Dict

import stripe

from saleor.payment.gateways.stripe.utils import (
    get_amount_for_stripe,
    get_amount_from_stripe,
    get_currency_for_stripe,
    get_currency_from_stripe,
)

from ... import TransactionKind
from ...interface import GatewayConfig, GatewayResponse, PaymentData
from .forms import StripePaymentModalForm
from .utils import get_amount_for_stripe, get_currency_for_stripe


def get_client_token(**_):
    """Not implemented for stripe gateway currently. The client token can be
    generated by Stripe's checkout.js or stripe.js automatically.
    """
    return


def authorize(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    kind = TransactionKind.CAPTURE if config.auto_capture else TransactionKind.AUTH
    client = _get_client(**config.connection_params)
    currency = get_currency_for_stripe(payment_information.currency)
    stripe_amount = get_amount_for_stripe(payment_information.amount, currency)

    try:
        intent = client.PaymentIntent.create(
            payment_method=payment_information.token,
            amount=stripe_amount,
            currency=currency,
            confirmation_method="manual",
            confirm=True,
            capture_method="automatic" if config.auto_capture else "manual",
        )
        response = GatewayResponse(
            is_success=intent.status in ("succeeded", "requires_capture"),
            transaction_id=intent.id,
            amount=get_amount_from_stripe(intent.amount, currency),
            currency=get_currency_from_stripe(intent.currency),
            error=None,
            kind=kind,
            raw_response=intent,
        )
    except stripe.error.StripeError as exc:
        response = GatewayResponse(
            is_success=False,
            transaction_id=payment_information.token,
            amount=payment_information.amount,
            currency=payment_information.currency,
            error=exc.user_message,
            kind=kind,
            raw_response=exc.json_body or {},
        )
    return response


def capture(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    client = _get_client(**config.connection_params)
    try:
        intent = client.PaymentIntent.retrieve(id=payment_information.token)
        capture = intent.capture()
        response = GatewayResponse(
            is_success=capture.status == "succeeded",
            transaction_id=intent.id,
            amount=get_amount_from_stripe(intent.amount, intent.currency),
            currency=get_currency_from_stripe(intent.currency),
            error=None,
            kind=TransactionKind.CAPTURE,
            raw_response=capture,
        )
    except stripe.error.StripeError as exc:
        response = GatewayResponse(
            is_success=False,
            transaction_id=payment_information.token,
            amount=payment_information.amount,
            currency=payment_information.currency,
            error=exc.user_message,
            kind=TransactionKind.CAPTURE,
            raw_response=exc.json_body or {},
        )
    return response


def refund(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    pass


def void(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    pass


def process_payment(
    payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    return authorize(payment_information, config)


def create_form(
    data: Dict, payment_information: PaymentData, connection_params: Dict
) -> StripePaymentModalForm:
    return StripePaymentModalForm(
        data=data,
        payment_information=payment_information,
        gateway_params=connection_params,
    )


def _get_client(**connection_params):
    stripe.api_key = connection_params.get("secret_key")
    return stripe
