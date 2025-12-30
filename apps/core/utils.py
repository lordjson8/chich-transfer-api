# apps/core/utils.py

from django.conf import settings


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def mask_phone_number(phone: str) -> str:
    """
    Mask phone number for display.
    Example: +237670123456 -> +2376***3456
    """
    if not phone or len(phone) < 8:
        return phone
    
    # Show first 5 and last 4 digits
    return f"{phone[:5]}***{phone[-4:]}"


def mask_email(email: str) -> str:
    """
    Mask email for display.
    Example: user@example.com -> u***r@example.com
    """
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@')
    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '***' + local[-1]
    
    return f"{masked_local}@{domain}"


def generate_reference_id(prefix: str = "TXN") -> str:
    """
    Generate unique reference ID.
    Example: TXN-A1B2C3D4E5F6
    """
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
