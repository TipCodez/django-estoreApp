from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError # IMPORTANT: Added the missing import
from .models import Profile, Product, Cart, CartItem 

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

# --- Basic E-commerce Views ---

def home(request):
    featured_products = Product.objects.filter(is_active=True).order_by('-created_at')[:4]
    return render(request, 'index.html', {'featured_products': featured_products})

def shop(request):
    all_products = Product.objects.filter(is_active=True)
    return render(request, "shop.html", {'all_products': all_products})

def about(request):
    return render(request, "about.html")

def contact(request):
    return render(request, "contact.html")

def product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    return render(request, 'product.html', {'product': product, 'related_products': related_products})

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
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("home")
        else:
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
    
    cart = get_or_create_cart(request)
    # Assuming product.final_price() exists on your Product model
    current_price = product.final_price()
    
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
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
    cart_items = Cart.objects.filter(user=request.user)


    
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'cart_total': cart.total_price(),
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
        else:
            item.quantity = new_quantity
            item.save()
            messages.success(request, f"Quantity for '{item.product.name}' updated to {new_quantity}.")
            
    return redirect('cart')