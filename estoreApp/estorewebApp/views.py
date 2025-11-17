from django.shortcuts import render, get_object_or_404
from .models import Product
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .models import Profile, Product, Order, OrderItem


def home(request):
    """
    Home page view, now fetches and displays featured products.
    """
    # Fetch a few products to feature on the homepage (e.g., first 4)
    featured_products = Product.objects.filter(is_active=True).order_by('-created_at')[:4]
    context = {
        'featured_products': featured_products
    }
    return render(request, 'index.html', context)

def shop(request):
    """
    Shop page view
    """
    # Fetch all active products
    all_products = Product.objects.filter(is_active=True)
    context = {
        'all_products': all_products
    }
    return render(request, "shop.html", context)


def about(request):
    """
    About page view
    """
    return render(request, "about.html")


def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm")

        phone = request.POST.get("phone")
        address = request.POST.get("address")
        location = request.POST.get("location")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        # Create User
        user = User.objects.create_user(username=username, email=email, password=password)

        # Save extra details in Profile
        user.profile.phone = phone
        user.profile.address = address
        user.profile.location = location
        user.profile.save()

        login(request, user)
        return redirect("home")

    return render(request, "accounts/signup.html")


def contact(request):
    """
    Contact page view
    """
    return render(request, "contact.html")


def product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # 🔑 Recommendation Logic: Find 4 other products in the same category
    related_products = Product.objects.filter(
        category=product.category # Filter by same category
    ).exclude(
        id=product.id # Exclude the current product
    )[:4] # Limit to 4 recommendations

    context = {
        'product': product,
        'related_products': related_products
    }
    return render(request, 'product.html', context)