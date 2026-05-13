from django.contrib import admin
from django.utils import timezone
from .models import (
    HeroBanner, Category, Product, Profile, Cart, CartItem, Order, OrderItem, Coupon,
    ProductTestimonial, Wishlist, WishlistItem, SecurityAuditLog
)
from .notifications import send_order_shipped_email, send_order_delivered_email


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "price", "stock", "stock_alert", "is_active", "created_at")
    list_filter = ("is_active", "category", "brand")
    search_fields = ("name", "brand")

    def stock_alert(self, obj):
        if obj.stock <= 0:
            return "Out of stock"
        if obj.stock <= 5:
            return "Low stock"
        return "OK"
    stock_alert.short_description = "Inventory"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "location")
    search_fields = ("user__username", "phone", "location")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "updated_at")
    search_fields = ("user__username", "session_key")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity", "price_at_addition")
    search_fields = ("product__name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price_at_purchase")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "payment_status", "coupon", "discount_amount", "total_amount", "created_at")
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("user__username", "shipping_address", "payment_reference")
    inlines = [OrderItemInline]
    actions = ["mark_shipped", "mark_delivered", "mark_cancelled"]

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        eligible = list(queryset.filter(status=Order.STATUS_PAID))
        count = queryset.filter(id__in=[o.id for o in eligible]).update(
            status=Order.STATUS_SHIPPED, shipped_at=timezone.now()
        )
        for order in eligible:
            order.status = Order.STATUS_SHIPPED
            send_order_shipped_email(order)
        self.message_user(request, f"{count} order(s) marked as shipped.")

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        eligible = list(queryset.filter(status=Order.STATUS_SHIPPED))
        count = queryset.filter(id__in=[o.id for o in eligible]).update(
            status=Order.STATUS_DELIVERED, delivered_at=timezone.now()
        )
        for order in eligible:
            order.status = Order.STATUS_DELIVERED
            send_order_delivered_email(order)
        self.message_user(request, f"{count} order(s) marked as delivered.")

    @admin.action(description="Mark selected orders as cancelled")
    def mark_cancelled(self, request, queryset):
        eligible = queryset.exclude(status=Order.STATUS_DELIVERED)
        count = eligible.update(status=Order.STATUS_CANCELLED, cancelled_at=timezone.now())
        self.message_user(request, f"{count} order(s) marked as cancelled.")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "active", "usage_count", "usage_limit", "expires_at")
    list_filter = ("active", "discount_type")
    search_fields = ("code",)


@admin.register(ProductTestimonial)
class ProductTestimonialAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("product__name", "user__username", "comment")
    actions = ["approve_testimonials", "reject_testimonials"]

    @admin.action(description="Approve selected testimonials")
    def approve_testimonials(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f"{count} testimonial(s) approved.")

    @admin.action(description="Reject selected testimonials")
    def reject_testimonials(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f"{count} testimonial(s) marked unapproved.")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__username",)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("wishlist", "product", "created_at")
    search_fields = ("wishlist__user__username", "product__name")


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "username", "ip_address", "path", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("username", "ip_address", "path", "details")
    readonly_fields = ("event_type", "username", "ip_address", "path", "details", "created_at")
