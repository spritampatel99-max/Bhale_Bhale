from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_history, name="history"),
    path("orders/<str:order_number>/", views.order_detail, name="detail"),
    path("orders/<str:order_number>/confirmation/", views.confirmation, name="confirmation"),
    path("orders/<str:order_number>/cancel/", views.order_cancel, name="cancel"),
]
