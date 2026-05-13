from django.urls import path
from . import views


urlpatterns = [
    # Core Pages
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path('product/<int:product_id>/', views.product, name='product_detail'),
    path('product/<int:product_id>/testimonial/', views.submit_testimonial, name='submit_testimonial'),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),

    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # User Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/move-to-cart/<int:item_id>/', views.move_wishlist_to_cart, name='move_wishlist_to_cart'),

    # Cart Management
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_quantity, name='update_cart'),
    path('cart/coupon/apply/', views.apply_coupon, name='apply_coupon'),
    path('cart/coupon/remove/', views.remove_coupon, name='remove_coupon'),

    # Checkout and Orders
    path('checkout/', views.checkout_view, name='checkout'),
    path('create_order/', views.create_order, name='create_order'),
    path('paystack/initialize/<int:order_id>/', views.initialize_payment, name='initialize_payment'),
    path('paystack/callback/', views.paystack_callback, name='paystack_callback'),
    path('paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),
    path('orders/', views.order_history_view, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
]
