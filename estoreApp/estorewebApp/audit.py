from .models import SecurityAuditLog


def log_security_event(event_type, username="", ip_address="", path="", details=""):
    SecurityAuditLog.objects.create(
        event_type=event_type,
        username=username or "",
        ip_address=ip_address or "",
        path=path or "",
        details=details or "",
    )
