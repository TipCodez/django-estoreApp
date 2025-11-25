from django.urls import path
from . import views


urlpatterns = [
    # Core Pages
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path('product/<int:product_id>/', views.product, name='product_detail'),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),

    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # User Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),

    # Cart Management
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_quantity, name='update_cart'),

    # # Checkout and Orders (New Additions)
    # path('checkout/', views.checkout_view, name='checkout'),
    # path('create_order/', views.create_order, name='create_order'),
    # path('orders/', views.order_history_view, name='order_history'),
    # path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
]