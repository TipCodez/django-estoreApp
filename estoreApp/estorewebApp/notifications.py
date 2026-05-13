from django.conf import settings
from django.core.mail import send_mail


def _can_send_email():
    return bool(getattr(settings, "EMAIL_HOST_USER", "")) and bool(getattr(settings, "DEFAULT_FROM_EMAIL", ""))


def _send_order_email(order, subject, body):
    if not _can_send_email():
        return False
    recipient = order.user.email
    if not recipient:
        return False
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=True,
    )
    return True


def send_order_placed_email(order):
    return _send_order_email(
        order,
        subject=f"Order #{order.id} created - awaiting payment",
        body=(
            f"Hi {order.user.username},\n\n"
            f"Your order #{order.id} was created successfully.\n"
            f"Total: GHS {order.total_amount}\n"
            "Please complete payment to confirm your order.\n\n"
            "Thank you for shopping with ElectroMart."
        ),
    )


def send_payment_confirmed_email(order):
    return _send_order_email(
        order,
        subject=f"Payment received for Order #{order.id}",
        body=(
            f"Hi {order.user.username},\n\n"
            f"We've received your payment for order #{order.id}.\n"
            f"Amount: GHS {order.total_amount}\n"
            "We'll notify you when your order ships.\n\n"
            "ElectroMart"
        ),
    )


def send_order_shipped_email(order):
    return _send_order_email(
        order,
        subject=f"Order #{order.id} has been shipped",
        body=(
            f"Hi {order.user.username},\n\n"
            f"Great news. Your order #{order.id} has been shipped.\n"
            "We'll notify you again once it is delivered.\n\n"
            "ElectroMart"
        ),
    )


def send_order_delivered_email(order):
    return _send_order_email(
        order,
        subject=f"Order #{order.id} delivered",
        body=(
            f"Hi {order.user.username},\n\n"
            f"Your order #{order.id} was marked as delivered.\n"
            "Thank you for shopping with ElectroMart.\n\n"
            "ElectroMart"
        ),
    )
