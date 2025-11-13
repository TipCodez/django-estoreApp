from django.shortcuts import render, get_object_or_404
from .models import Product


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


def contact(request):
    """
    Contact page view
    """
    return render(request, "contact.html")


def product(request, product_id):
    """
    Product detail page view.
    Shows a single product based on its ID.
    """
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'product.html', {'product': product})