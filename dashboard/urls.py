from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="products"),
    path("products/add/", views.product_edit, name="product_add"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("products/<int:pk>/images/<int:image_id>/delete/", views.product_image_delete, name="product_image_delete"),
    path("categories/", views.category_list, name="categories"),
    path("categories/add/", views.category_edit, name="category_add"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<str:order_number>/", views.order_detail, name="order_detail"),
    path("customers/", views.customer_list, name="customers"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/toggle/", views.customer_toggle, name="customer_toggle"),
    path("analytics/", views.analytics_page, name="analytics"),
    path("sales/", views.sales_page, name="sales"),
    path("sales/export/", views.sales_export, name="sales_export"),
]
