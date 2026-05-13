# ElectroMart (Django E-commerce App)

ElectroMart is a full-featured Django e-commerce application with:
- product catalog and search/filtering
- cart and checkout
- Paystack payment integration
- order lifecycle management
- wishlist
- coupon discounts
- testimonial moderation
- profile management
- security hardening for production

This README documents the current project in detail so you can confidently deploy to production.

## 1. Tech Stack
- Python 3.13
- Django 5.2+ (project currently running with Django 6.0.5 in your environment)
- PostgreSQL (configured for production-ready use)
- Pillow (image handling)
- django-environ + python-dotenv (environment management)

## 2. Project Structure
- `estoreApp/` - Django project config
  - `settings.py`
  - `urls.py`
- `estorewebApp/` - main app
  - `models.py`
  - `views.py`
  - `urls.py`
  - `admin.py`
  - `middleware.py`
  - `templates/`
  - `static/`
- `media/` - uploaded files (product/profile images)
- `staticfiles/` - collected static assets for production
- `.env` - environment variables
- `requirements.txt`

## 3. Implemented Features

### 3.1 Authentication and Profile
- Sign up, login, logout
- Password validation via Django validators
- Login lockout after repeated failures
- User profile page and profile update page
- Profile image upload and display in navbar avatar

### 3.2 Product Catalog
- Product model with:
  - category
  - brand
  - JSON specifications
  - discount price
  - stock and active state
  - image
- Shop page with:
  - keyword search
  - category filter
  - brand filter
  - min/max price filter
  - in-stock filter
  - sorting (newest, price asc/desc, name)
  - pagination
- Product detail page with related products

### 3.3 Cart System
- Supports authenticated users and guests (session-based carts)
- Add to cart from product page
- Quantity updates
- Remove item
- Auto stock consistency checks in cart view:
  - removes out-of-stock items
  - clamps quantity when stock drops
- Price protection:
  - each `CartItem` stores `price_at_addition`

### 3.4 Wishlist
- Add product to wishlist
- Remove from wishlist
- Move wishlist item directly to cart
- Duplicate prevention per user/product

### 3.5 Coupons and Discounts
- Coupon model supports:
  - percent and fixed discounts
  - min order amount
  - active window (`starts_at`, `expires_at`)
  - usage limits and usage count
- Apply/remove coupon at cart
- Discount computed at checkout/order creation

### 3.6 Orders and Checkout
- Checkout page with shipping address support
- Order creation from cart
- Stores:
  - subtotal
  - discount amount
  - final total
  - order status
  - payment status
- Order history page
- Order detail page with status timeline support

### 3.7 Paystack Payment Integration
- Payment initialization endpoint creates Paystack transaction
- Callback endpoint verifies payment
- Webhook endpoint validates HMAC signature
- Idempotent order payment marking
- Stock is decremented only after successful payment verification
- Cart cleared after successful payment

### 3.8 Testimonials / Reviews Moderation
- Customers can submit product testimonials with rating/comment
- Testimonials default to unapproved
- Admin moderation actions:
  - approve
  - unapprove/reject

### 3.9 Admin Operations
- Rich Django admin registrations for all models
- Order admin actions:
  - mark shipped (sends email)
  - mark delivered (sends email)
  - mark cancelled
- Product stock visibility in admin list

### 3.10 Analytics Dashboard
- Staff-only dashboard route
- KPIs:
  - total orders
  - paid/pending/cancelled counts
  - gross revenue
  - discount totals
  - average order value
  - top products
  - status/payment breakdown

### 3.11 Security Hardening
- Endpoint rate limiting middleware for sensitive POST routes:
  - `/login/`
  - `/signup/`
  - `/cart/coupon/apply/`
- Login lockout strategy:
  - failed-attempt counter
  - lockout window
- Security audit logging model (`SecurityAuditLog`)
- Secure settings support:
  - secure cookies
  - HSTS
  - nosniff
  - clickjacking protection
  - secure referrer policy
  - SSL redirect support

### 3.12 UI/UX Enhancements Completed
- Consistent shared navbar across pages
- Professional icon-based navbar and avatar profile entry
- Toast popup notifications for success/error/info/warning states
- Improved product action buttons (no overlap)
- Modernized cart page UI
- Improved wishlist card sizing/layout

## 4. URL Map
Core routes (see `estorewebApp/urls.py`):
- `/` home
- `/shop/`
- `/product/<product_id>/`
- `/about/`
- `/contact/`
- `/analytics/` (staff)

Auth:
- `/signup/`
- `/login/`
- `/logout/`

User:
- `/profile/`
- `/profile/update/`
- `/wishlist/`
- `/wishlist/add/<product_id>/`
- `/wishlist/remove/<item_id>/`
- `/wishlist/move-to-cart/<item_id>/`

Cart/Checkout:
- `/cart/`
- `/cart/add/<product_id>/`
- `/cart/remove/<item_id>/`
- `/cart/update/<item_id>/`
- `/cart/coupon/apply/`
- `/cart/coupon/remove/`
- `/checkout/`
- `/create_order/`

Payments/Orders:
- `/paystack/initialize/<order_id>/`
- `/paystack/callback/`
- `/paystack/webhook/`
- `/orders/`
- `/orders/<order_id>/`

## 5. Environment Variables
Current project uses `.env` loaded by `django-environ` and `python-dotenv`.

Required/important variables:
- `SECRET_KEY`
- `DJANGO_DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

Database:
- `DB_ENGINE` (e.g. `django.db.backends.postgresql`)
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

Paystack:
- `PAYSTACK_PUBLIC_KEY`
- `PAYSTACK_SECRET_KEY`

Email:
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`

Security:
- `SESSION_COOKIE_SECURE`
- `CSRF_COOKIE_SECURE`
- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_HSTS_PRELOAD`

Rate limiting / lockout:
- `LOGIN_MAX_FAILED_ATTEMPTS`
- `LOGIN_LOCKOUT_SECONDS`
- `RATE_LIMIT_LOGIN_MAX_REQUESTS`
- `RATE_LIMIT_LOGIN_WINDOW_SECONDS`
- `RATE_LIMIT_SIGNUP_MAX_REQUESTS`
- `RATE_LIMIT_SIGNUP_WINDOW_SECONDS`
- `RATE_LIMIT_COUPON_MAX_REQUESTS`
- `RATE_LIMIT_COUPON_WINDOW_SECONDS`

## 6. Local Development Setup
1. Create and activate virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies
```powershell
pip install -r requirements.txt
```

3. Configure `.env` (already present in this project)

4. Run migrations
```powershell
python manage.py migrate
```

5. Create superuser
```powershell
python manage.py createsuperuser
```

6. Start server
```powershell
python manage.py runserver
```

## 7. Production Deployment Checklist
1. Set production domain values:
   - `ALLOWED_HOSTS`
   - `CSRF_TRUSTED_ORIGINS`
2. Set `DJANGO_DEBUG=False`
3. Set strong `SECRET_KEY`
4. Enforce HTTPS:
   - `SECURE_SSL_REDIRECT=True`
   - secure cookies true
   - HSTS configured
5. Use PostgreSQL (already configured)
6. Run:
```powershell
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```
7. Configure reverse proxy (Nginx/Caddy) and WSGI server (Gunicorn/Waitress)
8. Register Paystack webhook endpoint in Paystack dashboard:
   - `https://yourdomain.com/paystack/webhook/`

## 8. Paystack Notes
- Test keys are free and should be used in development.
- Production requires live keys from Paystack dashboard.
- Webhook signature verification is implemented; keep secret key private.
- Never mark orders paid from frontend-only success; backend verification is required (already implemented).

## 9. Known Deployment Notes
- `manage.py check --deploy` may still warn if:
  - `SECURE_HSTS_PRELOAD=False` (optional but recommended if you plan preload submission)
  - insecure env values are used
- For preload readiness, set:
  - `SECURE_HSTS_PRELOAD=True`

## 10. Maintenance Tips
- Keep `.env` out of version control.
- Rotate credentials periodically (DB, email, Paystack keys).
- Monitor `SecurityAuditLog` in admin for suspicious activity.
- Add tests for critical flows:
  - checkout/payment
  - stock integrity
  - coupon validation
  - webhook idempotency

## 11. License / Ownership
Internal project documentation not currently tied to a public license file. Add a `LICENSE` file before open-source distribution.

