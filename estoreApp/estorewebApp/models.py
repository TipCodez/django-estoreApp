from django.db import models
from django.contrib.auth.models import User



class HeroBanner(models.Model):
    title = models.CharField(max_length=120, default="Homepage Banner")
    image = models.ImageField(upload_to="hero_banners/")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return f"{self.title} ({'active' if self.is_active else 'inactive'})"


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

    def is_out_of_stock(self):
        return self.stock <= 0

    def is_low_stock(self):
        return 0 < self.stock <= 5


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


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    PAYMENT_PENDING = "pending"
    PAYMENT_PAID = "paid"
    PAYMENT_FAILED = "failed"
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, "Pending"),
        (PAYMENT_PAID, "Paid"),
        (PAYMENT_FAILED, "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING,
    )
    payment_reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_provider = models.CharField(max_length=30, default="paystack")
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    coupon = models.ForeignKey("Coupon", on_delete=models.SET_NULL, null=True, blank=True)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_address = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def timeline_steps(self):
        steps = ["pending", "paid", "shipped", "delivered"]
        rank = {
            self.STATUS_PENDING: 0,
            self.STATUS_PAID: 1,
            self.STATUS_SHIPPED: 2,
            self.STATUS_DELIVERED: 3,
            self.STATUS_CANCELLED: -1,
        }
        current = rank.get(self.status, 0)
        return [(step, i <= current) for i, step in enumerate(steps)]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def sub_total(self):
        return self.quantity * self.price_at_purchase


class Coupon(models.Model):
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_PERCENT, "Percent"),
        (DISCOUNT_FIXED, "Fixed"),
    ]

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class ProductTestimonial(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="testimonials")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="testimonials")
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} - {self.user.username} ({self.rating}/5)"


class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wishlist")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wishlist for {self.user.username}"


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("wishlist", "product")

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.username}'s wishlist"


class SecurityAuditLog(models.Model):
    EVENT_RATE_LIMIT = "rate_limit"
    EVENT_LOGIN_FAILED = "login_failed"
    EVENT_LOGIN_LOCKED = "login_locked"
    EVENT_COUPON_INVALID = "coupon_invalid"
    EVENT_CHOICES = [
        (EVENT_RATE_LIMIT, "Rate Limit"),
        (EVENT_LOGIN_FAILED, "Login Failed"),
        (EVENT_LOGIN_LOCKED, "Login Locked"),
        (EVENT_COUPON_INVALID, "Coupon Invalid"),
    ]

    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    username = models.CharField(max_length=150, blank=True, default="")
    ip_address = models.CharField(max_length=64, blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="")
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.username or 'anonymous'} @ {self.created_at}"
