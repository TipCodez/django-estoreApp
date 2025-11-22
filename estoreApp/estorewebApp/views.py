from django.shortcuts import render, get_object_or_404
from .models import Product
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Profile, Product

profile = Profile()

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
        
        if User.objects.filter(username=username).exists():
                messages.error(request, "Username already taken.")
                return redirect('signup') 
            
        if User.objects.filter(email=email).exists():
                messages.error(request, "Email already taken.")
                return redirect('signup') 
                
        # Create User
        user = User.objects.create_user(username=username, email=email, password=password)

        # Save extra details in Profile
        user.profile.phone = phone
        user.profile.address = address
        user.profile.location = location
        user.profile.save()

        login(request, user)
        return redirect("home")

    return render(request, "signup.html")

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("login")



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



# @login_required
# def profile_view(request):
#     profile = request.user.profile

#     if request.method == 'POST':
#         user = request.user
#         profile = request.user.profile

#         # Update user fields
#         user.first_name = request.POST.get('first_name')
#         user.last_name = request.POST.get('last_name')
#         user.email = request.POST.get('email')
#         user.save()

#         # Update profile fields
      
#         profile.phone = request.POST.get('phone')
#         profile.address = request.POST.get('address')

#         if request.FILES.get('profile_image'):
#             profile.profile_image = request.FILES.get('profile_image')

#         profile.save()

#         return redirect('profile')

#     return render(request, 'profile.html', {"profile": profile})


@login_required
def update_profile_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        user = request.user
        # Update user fields
        user.username = request.POST.get('username')
        user.last_name = request.POST.get('last_name')
        # profile.username = request.POST.get('username')
        profile.last_name = request.POST.get('last_name')
        profile.phone = request.POST.get('phone')
        profile.address = request.POST.get('address')

        # Handle image upload
        if request.FILES.get('profile_image'):
            profile.profile_image = request.FILES.get('profile_image')

        profile.save()
        user.save()

        return redirect('profile')   # ⬅ Redirect back to profile page

    return render(request, 'update_profile.html', {'profile': profile})


@login_required
def profile_view(request):
    profile = request.user.profile
    return render(request, 'profile.html', {'profile': profile})
