from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError # IMPORTANT: Added the missing import
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import hashlib
import hmac
import json
import uuid
from decimal import Decimal
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError
from .models import (
    HeroBanner, Profile, Product, Cart, CartItem, Order, OrderItem, Coupon,
    ProductTestimonial, Wishlist, WishlistItem
)
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.db.models import Sum, Count, DecimalField, ExpressionWrapper
from .notifications import send_order_placed_email, send_payment_confirmed_email
from .audit import log_security_event
from .models import SecurityAuditLog


def staff_required(view_func):
    return login_required(user_passes_test(lambda u: u.is_staff, login_url="login")(view_func))

# --- Helper Function for Cart Retrieval (Supports Guests) ---

def get_or_create_cart(request):
    """
    Retrieves the current user's cart or creates one. 
    Handles both authenticated users and guests using session keys.
    """
    if request.user.is_authenticated:
        # 1. Logged-in user: get or create cart linked to the User
        cart, created = Cart.objects.get_or_create(user=request.user)
        # (Merge logic omitted for simplicity, but can be added here)
        
    else:
        # 2. Guest user: ensure session key exists
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        
        # Get or create cart linked to the session key
        cart, created = Cart.objects.get_or_create(
            session_key=session_key, 
            user__isnull=True
        )
        
    return cart


def get_or_create_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _get_coupon_from_session(request):
    code = request.session.get("coupon_code")
    if not code:
        return None
    return Coupon.objects.filter(code__iexact=code, active=True).first()


def _validate_coupon(coupon, subtotal):
    now = timezone.now()
    if not coupon or not coupon.active:
        return False, "Invalid coupon."
    if coupon.starts_at and now < coupon.starts_at:
        return False, "Coupon is not active yet."
    if coupon.expires_at and now > coupon.expires_at:
        return False, "Coupon has expired."
    if coupon.usage_limit is not None and coupon.usage_count >= coupon.usage_limit:
        return False, "Coupon usage limit reached."
    if subtotal < coupon.min_order_amount:
        return False, f"Minimum order for this coupon is GHS {coupon.min_order_amount}."
    return True, ""


def _compute_discount(subtotal, coupon):
    if not coupon:
        return Decimal("0.00")
    if coupon.discount_type == Coupon.DISCOUNT_PERCENT:
        discount = (subtotal * coupon.discount_value) / Decimal("100")
    else:
        discount = coupon.discount_value
    if discount < 0:
        discount = Decimal("0.00")
    if discount > subtotal:
        discount = subtotal
    return discount.quantize(Decimal("0.01"))

# --- Basic E-commerce Views ---

def home(request):
    featured_products = Product.objects.filter(is_active=True).order_by('-created_at')[:4]
    hero_banner = HeroBanner.objects.filter(is_active=True).first()
    return render(
        request,
        'index.html',
        {
            'featured_products': featured_products,
            'hero_banner': hero_banner,
        },
    )

def shop(request):
    products = Product.objects.filter(is_active=True).select_related("category")

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    brand = request.GET.get("brand", "").strip()
    in_stock = request.GET.get("in_stock", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(brand__icontains=q)
        )

    if category:
        products = products.filter(category__name__iexact=category)

    if brand:
        products = products.filter(brand__iexact=brand)

    if in_stock == "1":
        products = products.filter(stock__gt=0)

    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except Exception:
            pass

    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except Exception:
            pass

    sort_map = {
        "newest": "-created_at",
        "price_asc": "price",
        "price_desc": "-price",
        "name_asc": "name",
    }
    products = products.order_by(sort_map.get(sort, "-created_at"))

    paginator = Paginator(products, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = (
        Product.objects.filter(is_active=True)
        .values_list("category__name", flat=True)
        .distinct()
        .order_by("category__name")
    )
    brands = (
        Product.objects.filter(is_active=True)
        .exclude(brand__isnull=True)
        .exclude(brand__exact="")
        .values_list("brand", flat=True)
        .distinct()
        .order_by("brand")
    )

    context = {
        "all_products": page_obj.object_list,
        "page_obj": page_obj,
        "categories": categories,
        "brands": brands,
        "filters": {
            "q": q,
            "category": category,
            "brand": brand,
            "in_stock": in_stock,
            "min_price": min_price,
            "max_price": max_price,
            "sort": sort,
        },
    }
    return render(request, "shop.html", context)

def about(request):
    return render(request, "about.html")

def contact(request):
    return render(request, "contact.html")

def product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    testimonials = product.testimonials.filter(is_approved=True).select_related("user")
    return render(
        request,
        'product.html',
        {'product': product, 'related_products': related_products, 'testimonials': testimonials}
    )


@login_required
def submit_testimonial(request, product_id):
    if request.method != "POST":
        return redirect("product_detail", product_id=product_id)

    product = get_object_or_404(Product, id=product_id)
    comment = (request.POST.get("comment") or "").strip()
    try:
        rating = int(request.POST.get("rating", "5"))
    except ValueError:
        rating = 5
    rating = max(1, min(5, rating))

    if not comment:
        messages.error(request, "Please enter your comment.")
        return redirect("product_detail", product_id=product_id)

    ProductTestimonial.objects.create(
        product=product,
        user=request.user,
        rating=rating,
        comment=comment,
        is_approved=False,
    )
    messages.success(request, "Thanks. Your testimonial was submitted for moderation.")
    return redirect("product_detail", product_id=product_id)

# --- Authentication Views ---

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        location = request.POST.get("location")
        last_name_form = request.POST.get("last_name") # Added to capture last name in signup

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")
        try:
            validate_password(password)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect("signup")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('signup') 
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already taken.")
            return redirect('signup') 
                
        user = User.objects.create_user(username=username, email=email, password=password)
        user.last_name = last_name_form
        user.save()

        user.profile.phone = phone
        user.profile.address = address
        user.profile.location = location
        user.profile.save()

        login(request, user)
        messages.success(request, "Account created and logged in successfully!")
        return redirect("home")

    return render(request, "signup.html")

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        ip = _get_client_ip(request)
        lock_key = f"auth:lock:{username}:{ip}"
        fail_key = f"auth:fail:{username}:{ip}"

        if cache.get(lock_key):
            log_security_event(
                SecurityAuditLog.EVENT_LOGIN_LOCKED,
                username=username,
                ip_address=ip,
                path=request.path,
                details="Attempted login during lockout window.",
            )
            messages.error(request, "Too many failed login attempts. Please try again later.")
            return redirect("login")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            cache.delete(lock_key)
            cache.delete(fail_key)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("home")
        else:
            attempts = cache.get(fail_key, 0) + 1
            cache.set(fail_key, attempts, timeout=settings.LOGIN_LOCKOUT_SECONDS)
            log_security_event(
                SecurityAuditLog.EVENT_LOGIN_FAILED,
                username=username,
                ip_address=ip,
                path=request.path,
                details=f"Failed login attempt #{attempts}",
            )
            if attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                cache.set(lock_key, True, timeout=settings.LOGIN_LOCKOUT_SECONDS)
                log_security_event(
                    SecurityAuditLog.EVENT_LOGIN_LOCKED,
                    username=username,
                    ip_address=ip,
                    path=request.path,
                    details=f"Lockout triggered after {attempts} failed attempts.",
                )
            messages.error(request, "Invalid username or password.")
            return redirect("login")

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")

# --- Profile Management Views ---

@login_required
def profile_view(request):
    profile = request.user.profile
    return render(request, 'profile.html', {'profile': profile})


@login_required
def update_profile_view(request):
    user = request.user
    profile = request.user.profile

    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.last_name = request.POST.get('last_name') 
        profile.phone = request.POST.get('phone')
        profile.address = request.POST.get('address')
        
        if request.FILES.get('profile_image'):
            profile.profile_image = request.FILES.get('profile_image')

        try:
            user.save()
            profile.save()
            messages.success(request, 'Profile updated successfully!')
        except IntegrityError:
            messages.error(request, "Error saving profile. Username or email might be duplicated.")
            
        return redirect('profile')

    return render(request, 'update_profile.html', {'profile': profile})

# --- Cart Management Views ---

def add_to_cart(request, product_id):
    """Handles adding a product to the cart (supports guests and price protection)."""
    product = get_object_or_404(Product, id=product_id)
    quantity = 1
    if product.stock <= 0:
        messages.error(request, f"'{product.name}' is currently out of stock.")
        return redirect('product_detail', product_id=product.id)
    
    cart = get_or_create_cart(request)
    # Assuming product.final_price() exists on your Product model
    current_price = product.final_price()
    
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        if cart_item.quantity >= product.stock:
            messages.error(request, f"Only {product.stock} item(s) available for '{product.name}'.")
            return redirect('product_detail', product_id=product.id)
        cart_item.quantity += quantity
        cart_item.save()
        messages.success(request, f"'{product.name}' quantity updated in your cart.")
        
    except CartItem.DoesNotExist:
        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            price_at_addition=current_price 
        )
        messages.success(request, f"'{product.name}' added to your cart.")
        
    return redirect('product_detail', product_id=product.id)


def cart_view(request):
    """Displays the current cart contents (supports guests)."""
    cart = get_or_create_cart(request)
    for item in cart.items.select_related("product").all():
        if item.product.stock <= 0:
            item.delete()
            messages.warning(request, f"Removed '{item.product.name}' because it is out of stock.")
            continue
        if item.quantity > item.product.stock:
            item.quantity = item.product.stock
            item.save(update_fields=["quantity"])
            messages.warning(request, f"Adjusted '{item.product.name}' quantity to available stock ({item.product.stock}).")
    subtotal = cart.total_price()
    coupon = _get_coupon_from_session(request)
    discount_amount = Decimal("0.00")
    if coupon:
        valid, reason = _validate_coupon(coupon, subtotal)
        if valid:
            discount_amount = _compute_discount(subtotal, coupon)
        else:
            request.session.pop("coupon_code", None)
            messages.warning(request, reason)
            coupon = None
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'cart_subtotal': subtotal,
        'coupon': coupon,
        'discount_amount': discount_amount,
        'cart_total': (subtotal - discount_amount),
    }
    return render(request, 'cart.html', context)


def remove_from_cart(request, item_id):
    """Handles removing a specific item from the cart."""
    item = get_object_or_404(CartItem, id=item_id)
    
    # Security Check: Ensure the item belongs to the current user/session's cart
    current_cart = get_or_create_cart(request)
    if item.cart != current_cart:
        messages.error(request, "Access denied.")
        return redirect('cart')

    item.delete()
    messages.success(request, f"'{item.product.name}' was removed from your cart.")
    
    return redirect('cart')


def update_cart_quantity(request, item_id): # <-- FIX: Removed @login_required
    """Handles updating the quantity of a CartItem using a POST request."""
    item = get_object_or_404(CartItem, id=item_id)
    
    current_cart = get_or_create_cart(request)
    if item.cart != current_cart:
        messages.error(request, "Access denied.")
        return redirect('cart')

    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity'))
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity provided.")
            return redirect('cart')
        
        if new_quantity <= 0:
            item.delete()
            messages.success(request, f"'{item.product.name}' removed from cart.")
        elif new_quantity > item.product.stock:
            item.quantity = item.product.stock
            item.save(update_fields=["quantity"])
            messages.warning(request, f"Only {item.product.stock} unit(s) are available for '{item.product.name}'.")
        else:
            item.quantity = new_quantity
            item.save()
            messages.success(request, f"Quantity for '{item.product.name}' updated to {new_quantity}.")
            
    return redirect('cart')


def apply_coupon(request):
    if request.method != "POST":
        return redirect("cart")

    cart = get_or_create_cart(request)
    subtotal = cart.total_price()
    code = (request.POST.get("coupon_code") or "").strip()
    if not code:
        log_security_event(
            SecurityAuditLog.EVENT_COUPON_INVALID,
            username=request.user.username if request.user.is_authenticated else "",
            ip_address=_get_client_ip(request),
            path=request.path,
            details="Empty coupon submitted.",
        )
        messages.error(request, "Please enter a coupon code.")
        return redirect("cart")

    coupon = Coupon.objects.filter(code__iexact=code, active=True).first()
    valid, reason = _validate_coupon(coupon, subtotal)
    if not valid:
        log_security_event(
            SecurityAuditLog.EVENT_COUPON_INVALID,
            username=request.user.username if request.user.is_authenticated else "",
            ip_address=_get_client_ip(request),
            path=request.path,
            details=f"Coupon '{code}' rejected: {reason}",
        )
        messages.error(request, reason)
        return redirect("cart")

    request.session["coupon_code"] = coupon.code
    messages.success(request, f"Coupon '{coupon.code}' applied.")
    return redirect("cart")


def remove_coupon(request):
    request.session.pop("coupon_code", None)
    messages.info(request, "Coupon removed.")
    return redirect("cart")


@login_required
def wishlist_view(request):
    wishlist = get_or_create_wishlist(request.user)
    items = wishlist.items.select_related("product").all()
    return render(request, "wishlist.html", {"wishlist_items": items})


@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    wishlist = get_or_create_wishlist(request.user)
    _, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
    if created:
        messages.success(request, f"'{product.name}' added to your wishlist.")
    else:
        messages.info(request, f"'{product.name}' is already in your wishlist.")
    return redirect("product_detail", product_id=product.id)


@login_required
def remove_from_wishlist(request, item_id):
    wishlist = get_or_create_wishlist(request.user)
    item = get_object_or_404(WishlistItem, id=item_id, wishlist=wishlist)
    name = item.product.name
    item.delete()
    messages.success(request, f"'{name}' removed from your wishlist.")
    return redirect("wishlist")


@login_required
def move_wishlist_to_cart(request, item_id):
    wishlist = get_or_create_wishlist(request.user)
    item = get_object_or_404(WishlistItem, id=item_id, wishlist=wishlist)
    product = item.product
    if product.stock <= 0:
        messages.error(request, f"'{product.name}' is out of stock.")
        return redirect("wishlist")

    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": 1, "price_at_addition": product.final_price()},
    )
    if not created:
        if cart_item.quantity >= product.stock:
            messages.error(request, f"Only {product.stock} item(s) available for '{product.name}'.")
            return redirect("wishlist")
        cart_item.quantity += 1
        cart_item.save(update_fields=["quantity"])

    item.delete()
    messages.success(request, f"'{product.name}' moved to cart.")
    return redirect("cart")


@login_required
def checkout_view(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product").all()

    if not cart_items:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")

    subtotal = cart.total_price()
    coupon = _get_coupon_from_session(request)
    discount_amount = Decimal("0.00")
    if coupon:
        valid, reason = _validate_coupon(coupon, subtotal)
        if valid:
            discount_amount = _compute_discount(subtotal, coupon)
        else:
            request.session.pop("coupon_code", None)
            messages.warning(request, reason)
            coupon = None

    return render(
        request,
        "checkout.html",
        {
            "cart_items": cart_items,
            "cart_subtotal": subtotal,
            "coupon": coupon,
            "discount_amount": discount_amount,
            "cart_total": (subtotal - discount_amount),
            "profile": request.user.profile,
        },
    )


@login_required
@transaction.atomic
def create_order(request):
    if request.method != "POST":
        return redirect("checkout")

    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related("product").all()

    if not cart_items:
        messages.error(request, "Cannot place an order with an empty cart.")
        return redirect("cart")

    shipping_address = request.POST.get("shipping_address") or request.user.profile.address
    if not shipping_address:
        messages.error(request, "Please provide a shipping address.")
        return redirect("checkout")

    for item in cart_items:
        if item.product.stock <= 0:
            messages.error(request, f"'{item.product.name}' is out of stock.")
            return redirect("cart")
        if item.quantity > item.product.stock:
            messages.error(request, f"Only {item.product.stock} unit(s) are available for '{item.product.name}'.")
            return redirect("cart")

    subtotal = sum(item.sub_total() for item in cart_items)
    coupon = _get_coupon_from_session(request)
    discount_amount = Decimal("0.00")
    if coupon:
        valid, reason = _validate_coupon(coupon, subtotal)
        if valid:
            discount_amount = _compute_discount(subtotal, coupon)
        else:
            request.session.pop("coupon_code", None)
            messages.warning(request, reason)
            coupon = None

    order = Order.objects.create(
        user=request.user,
        shipping_address=shipping_address,
        coupon=coupon,
        subtotal_amount=subtotal,
        discount_amount=discount_amount,
        total_amount=0,
    )

    for cart_item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            price_at_purchase=cart_item.price_at_addition,
        )
    order.total_amount = (subtotal - discount_amount)
    order.save(update_fields=["total_amount"])
    send_order_placed_email(order)
    return redirect("initialize_payment", order_id=order.id)


@login_required
def order_history_view(request):
    orders = request.user.orders.prefetch_related("items__product").all()
    return render(request, "order_history.html", {"orders": orders})


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        id=order_id,
        user=request.user,
    )
    return render(request, "order_detail.html", {"order": order})


def _paystack_request(endpoint, payload=None, method="GET"):
    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
    if not secret_key:
        raise ValueError("Missing PAYSTACK_SECRET_KEY")

    url = f"https://api.paystack.co/{endpoint}"
    data = None
    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib_request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"Paystack HTTP error: {exc.code} {body}") from exc
    except URLError as exc:
        raise ValueError(f"Paystack network error: {exc.reason}") from exc


def _amount_to_kobo(amount):
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


@transaction.atomic
def _mark_order_paid(order, reference, paid_amount_kobo):
    order = Order.objects.select_for_update().get(id=order.id)
    if order.payment_status == Order.PAYMENT_PAID:
        return order

    expected_amount_kobo = _amount_to_kobo(order.total_amount)
    if paid_amount_kobo != expected_amount_kobo:
        raise ValueError("Paid amount does not match order total.")

    for item in order.items.select_related("product").all():
        product = Product.objects.select_for_update().get(id=item.product_id)
        if item.quantity > product.stock:
            raise ValueError(f"Insufficient stock for {product.name}")
        product.stock -= item.quantity
        product.save(update_fields=["stock"])

    order.payment_status = Order.PAYMENT_PAID
    order.status = Order.STATUS_PAID
    order.paid_at = timezone.now()
    order.payment_reference = reference
    order.save(
        update_fields=["payment_status", "status", "paid_at", "payment_reference", "updated_at"]
    )
    if order.coupon_id:
        Coupon.objects.filter(id=order.coupon_id).update(usage_count=F("usage_count") + 1)
    send_payment_confirmed_email(order)

    cart = Cart.objects.filter(user=order.user).first()
    if cart:
        cart.items.all().delete()
    return order


@login_required
def initialize_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.payment_status == Order.PAYMENT_PAID:
        messages.info(request, "This order has already been paid.")
        return redirect("order_detail", order_id=order.id)

    for item in order.items.select_related("product").all():
        if item.product.stock <= 0:
            messages.error(request, f"'{item.product.name}' is out of stock. Please reorder.")
            return redirect("order_detail", order_id=order.id)
        if item.quantity > item.product.stock:
            messages.error(request, f"'{item.product.name}' stock changed. Available: {item.product.stock}.")
            return redirect("order_detail", order_id=order.id)

    reference = order.payment_reference or f"ORD-{order.id}-{uuid.uuid4().hex[:10]}"
    order.payment_reference = reference
    order.save(update_fields=["payment_reference", "updated_at"])

    callback_url = request.build_absolute_uri(reverse("paystack_callback"))
    payload = {
        "email": request.user.email or f"user-{request.user.id}@example.com",
        "amount": _amount_to_kobo(order.total_amount),
        "reference": reference,
        "callback_url": callback_url,
        "metadata": {"order_id": order.id, "user_id": request.user.id},
    }

    try:
        result = _paystack_request("transaction/initialize", payload=payload, method="POST")
    except ValueError as exc:
        messages.error(request, f"Could not start payment: {exc}")
        return redirect("order_detail", order_id=order.id)

    if not result.get("status"):
        messages.error(request, result.get("message", "Paystack initialization failed."))
        return redirect("order_detail", order_id=order.id)

    auth_url = result.get("data", {}).get("authorization_url")
    if not auth_url:
        messages.error(request, "Paystack did not return an authorization URL.")
        return redirect("order_detail", order_id=order.id)
    return redirect(auth_url)


@login_required
def paystack_callback(request):
    reference = request.GET.get("reference")
    if not reference:
        messages.error(request, "Missing payment reference.")
        return redirect("order_history")

    order = get_object_or_404(Order, payment_reference=reference, user=request.user)
    try:
        result = _paystack_request(f"transaction/verify/{reference}")
        data = result.get("data", {})
        paid_ok = result.get("status") and data.get("status") == "success"
        if paid_ok:
            _mark_order_paid(order, reference, int(data.get("amount", 0)))
            messages.success(request, f"Payment successful for Order #{order.id}.")
        else:
            order.payment_status = Order.PAYMENT_FAILED
            order.save(update_fields=["payment_status", "updated_at"])
            messages.error(request, "Payment was not successful.")
    except ValueError as exc:
        messages.error(request, f"Payment verification failed: {exc}")
    return redirect("order_detail", order_id=order.id)


@csrf_exempt
def paystack_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(secret_key.encode("utf-8"), request.body, hashlib.sha512).hexdigest()
    if not secret_key or not hmac.compare_digest(signature, expected):
        return HttpResponse(status=401)

    try:
        event = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if event.get("event") == "charge.success":
        data = event.get("data", {})
        reference = data.get("reference")
        amount = int(data.get("amount", 0))
        if reference:
            try:
                order = Order.objects.get(payment_reference=reference)
                _mark_order_paid(order, reference, amount)
            except (Order.DoesNotExist, ValueError):
                return HttpResponse(status=400)

    return JsonResponse({"status": "ok"})


@staff_required
def analytics_dashboard(request):
    paid_orders = Order.objects.filter(payment_status=Order.PAYMENT_PAID)
    all_orders = Order.objects.all()

    gross_revenue = paid_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    discount_total = paid_orders.aggregate(total=Sum("discount_amount"))["total"] or Decimal("0.00")
    avg_order_value = paid_orders.aggregate(avg=Sum("total_amount"))["avg"] or Decimal("0.00")

    top_products = (
        OrderItem.objects.filter(order__payment_status=Order.PAYMENT_PAID)
        .values("product__id", "product__name")
        .annotate(
            units_sold=Sum("quantity"),
            sales=Sum(
                ExpressionWrapper(
                    F("quantity") * F("price_at_purchase"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
        )
        .order_by("-units_sold")[:5]
    )

    status_breakdown = all_orders.values("status").annotate(count=Count("id")).order_by("-count")
    payment_breakdown = all_orders.values("payment_status").annotate(count=Count("id")).order_by("-count")

    context = {
        "total_orders": all_orders.count(),
        "paid_orders": paid_orders.count(),
        "pending_orders": all_orders.filter(status=Order.STATUS_PENDING).count(),
        "cancelled_orders": all_orders.filter(status=Order.STATUS_CANCELLED).count(),
        "gross_revenue": gross_revenue,
        "discount_total": discount_total,
        "avg_order_value": (gross_revenue / paid_orders.count()) if paid_orders.exists() else Decimal("0.00"),
        "top_products": top_products,
        "status_breakdown": status_breakdown,
        "payment_breakdown": payment_breakdown,
    }
    return render(request, "analytics_dashboard.html", context)
