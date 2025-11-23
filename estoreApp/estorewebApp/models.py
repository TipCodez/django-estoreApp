from django.db import models
from django.contrib.auth.models import User



class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    specifications = models.JSONField(blank=True, null=True, help_text="Add specifications as key-value pairs.")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.brand})"

    def final_price(self):
        """Return discount price if available, else normal price."""
        return self.discount_price if self.discount_price else self.price


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', default='default.png')    
    location = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username


class Cart(models.Model):
    """
    Represents the shopping cart. Linked to a user OR a session key for guests.
    """
    # Allows cart to exist without a logged-in user
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    # Stores the session key for guest users
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        # Display truncated session key for guests
        return f"Guest Cart ({self.session_key[:8]}...)"

    def total_price(self):
        """Calculates the total price of all items in the cart."""
        # Use a list comprehension for efficiency and sum the sub_total from CartItem
        return sum(item.sub_total() for item in self.items.all())


class CartItem(models.Model):
    """
    Represents a specific product and quantity within a cart, storing the price for protection.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    # Stores the price at the moment the item was added (Price Protection)
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2)
    

    class Meta:
        # Ensures a product can only appear once in a given cart
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def sub_total(self):
        """Calculates the price using the stored price, providing price protection."""
        # Uses the price stored on this CartItem instance
        return self.quantity * self.price_at_addition
