from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("shop/", include("shop.urls")),
    path("drf-payments/", include("drf_payments.urls")),
]
