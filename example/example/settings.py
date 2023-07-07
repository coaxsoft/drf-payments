import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "04l*lbg=0q&5e4p^9-d$ijzf^#@+^hufstf*er!vqd^2z2!=2-"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "drf_payments",
    "shop",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "example.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "example.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


PAYMENT_MODEL = "shop.Payment"
PAYMENT_CALLBACK_URL = "http://localhost:8000/drf-payments/callback/"
PAYMENT_SUCCESS_URL = "http://localhost:3000/payments/success/"
PAYMENT_FAILURE_URL = "http://localhost:3000/payments/failure/"

PAYMENT_VARIANTS = {
    "stripe": (
        "drf_payments.stripe.StripeCheckoutProvider",
        {
            "secret_key": os.environ.get("STRIPE_SECRET_KEY"),
            "public_key": os.environ.get("STRIPE_PUBLIC_KEY"),
        },
    ),
    "paypal": (
        "drf_payments.paypal.PaypalProvider",
        {
            "client_id": os.environ.get("PAYPAL_CLIENT_ID"),
            "secret": os.environ.get("PAYPAL_SECRET_KEY"),
            "endpoint": os.environ.get("PAYPAL_URL", "https://api.sandbox.paypal.com"),
        },
    ),
    "braintree": (
        "drf_payments.braintree.BraintreeProvider",
        {
            "merchant_id": os.environ.get("BRAINTREE_MERCHANT_ID"),
            "public_key": os.environ.get("BRAINTREE_PUBLIC_KEY"),
            "private_key": os.environ.get("BRAINTREE_PRIVATE_KEY"),
            "sandbox": os.environ.get("BRAINTREE_SANDBOX", True),
        },
    ),
    "authorizenet": (
        "drf_payments.authorizenet.AuthorizeNetProvider",
        {
            "login_id": os.environ.get("AUTHORIZENET_LOGIN_ID"),
            "transaction_key": os.environ.get("AUTHORIZENET_TRANSACTION_KEY"),
            "endpoint": os.environ.get("AUTHORIZENET_URL", True),
        },
    ),
}
