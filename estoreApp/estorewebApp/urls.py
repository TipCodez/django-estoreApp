from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("product/", views.product, name="product_detail"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]
