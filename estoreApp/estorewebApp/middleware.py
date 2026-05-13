from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from .audit import log_security_event
from .models import SecurityAuditLog


class EndpointRateLimitMiddleware:
    """
    Basic per-IP endpoint rate limiter for sensitive routes.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.rules = {
            "/login/": (
                getattr(settings, "RATE_LIMIT_LOGIN_MAX_REQUESTS", 10),
                getattr(settings, "RATE_LIMIT_LOGIN_WINDOW_SECONDS", 60),
            ),
            "/signup/": (
                getattr(settings, "RATE_LIMIT_SIGNUP_MAX_REQUESTS", 10),
                getattr(settings, "RATE_LIMIT_SIGNUP_WINDOW_SECONDS", 60),
            ),
            "/cart/coupon/apply/": (
                getattr(settings, "RATE_LIMIT_COUPON_MAX_REQUESTS", 20),
                getattr(settings, "RATE_LIMIT_COUPON_WINDOW_SECONDS", 60),
            ),
        }

    def __call__(self, request):
        if request.method == "POST":
            rule = self.rules.get(request.path)
            if rule:
                max_requests, window = rule
                ip = self._get_ip(request)
                key = f"rl:{request.path}:{ip}"
                count = cache.get(key, 0)
                if count >= max_requests:
                    username = request.POST.get("username", "") if hasattr(request, "POST") else ""
                    log_security_event(
                        SecurityAuditLog.EVENT_RATE_LIMIT,
                        username=username,
                        ip_address=ip,
                        path=request.path,
                        details=f"Exceeded {max_requests}/{window}s",
                    )
                    return HttpResponse("Too many requests. Please try again shortly.", status=429)
                cache.set(key, count + 1, timeout=window)

        return self.get_response(request)

    @staticmethod
    def _get_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
