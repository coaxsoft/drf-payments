from enum import Enum


class PaymentError(Exception):
    def __init__(self, message, code=None, gateway_message=None):
        super().__init__(message)
        self.code = code
        self.gateway_message = gateway_message


class PaymentStatus(Enum):
    WAITING = "waiting"
    PREAUTH = "preauth"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    REFUNDED = "refunded"
    ERROR = "error"
    INPUT = "input"


class FraudStatus(Enum):
    UNKNOWN = "unknown"
    ACCEPT = "accept"
    REJECT = "reject"
    REVIEW = "review"


class PaymentCurrency(Enum):
    CAD = "cad"
    USD = "usd"
    EUR = "eur"
    GBP = "gbp"
    AUD = "aud"
    JPY = "jpy"
    CHF = "chf"
    HKD = "hkd"
    NZD = "nzd"
    SGD = "sgd"
    SEK = "sek"
    DKK = "dkk"
    NOK = "nok"
    MXN = "mxn"
    BRL = "brl"
    MYR = "myr"
    PHP = "php"
    THB = "thb"
    IDR = "idr"
    TRY = "try"
    INR = "inr"
    RUB = "rub"
    ILS = "ils"
    SAR = "sar"
