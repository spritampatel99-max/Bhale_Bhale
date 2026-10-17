from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="list"),
    path("products/<slug:slug>/", views.product_detail, name="detail"),
    path("categories/", views.category_list, name="categories"),
    path("categories/<slug:category_slug>/", views.product_list, name="category"),
]
