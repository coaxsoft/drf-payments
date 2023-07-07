from typing import Dict, Tuple

from django.conf import settings
from django.utils.module_loading import import_string

PAYMENT_VARIANTS: Dict[str, Tuple[str, Dict]] = {"default": ("drf_payments.stripe.StripeProvider", {})}


class BasicProvider:
    """Defined a base provider API.

    All providers backends should subclass this class.

    ``BasicProvider`` should not be instantiated directly. Use factory instead.
    """

    def __init__(self, capture=True, **kwargs):
        """Create a new provider instance.

        This method should not be called directly; use :func:`provider_factory`
        instead.
        """
        self._capture = capture

    def process_payment(self, payment):
        raise NotImplementedError()

    def refund(self, payment, amount=None):
        raise NotImplementedError()


PROVIDER_CACHE = {}


def _default_provider_factory(variant: str, payment=None):
    """Return the provider instance based on ``variant``.

    :arg variant: The name of a variant defined in ``PAYMENT_VARIANTS``.
    """
    variants = getattr(settings, "PAYMENT_VARIANTS", PAYMENT_VARIANTS)
    handler, config = variants.get(variant, (None, None))
    if not handler:
        raise ValueError(f"Payment variant does not exist: {variant}")
    if variant not in PROVIDER_CACHE:  # pragma no branch
        module_path, class_name = handler.rsplit(".", 1)
        module = __import__(str(module_path), globals(), locals(), [str(class_name)])
        class_ = getattr(module, class_name)
        PROVIDER_CACHE[variant] = class_(**config)
    return PROVIDER_CACHE[variant]


if PAYMENT_VARIANT_FACTORY := getattr(settings, "PAYMENT_VARIANT_FACTORY", None):
    provider_factory = import_string(PAYMENT_VARIANT_FACTORY)
else:
    provider_factory = _default_provider_factory
