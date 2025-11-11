from django.shortcuts import render, get_object_or_404


def home(request):
    return render(request, 'index.html')

def shop(request):
    """
    Shop page view
    """
    return render(request, "shop.html")


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



def product(request):
    """
    Product detail page view.
    Shows a single product based on its ID.
    """
    # Uncomment when you have a Product model
    # product = get_object_or_404(Product, id=product_id)

    # For now, just pass the product_id for template testing
   
    return render(request, "product.html")

