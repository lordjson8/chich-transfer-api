"""
Utility functions for authentication
"""
import secrets
import hashlib
import base64
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature


# ============================================================================
# OTP FUNCTIONS
# ============================================================================

def generate_otp(length=6):
    """Generate random OTP code"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


def hash_otp(otp_code):
    """Hash OTP code before storing"""
    return make_password(otp_code)


def verify_otp(otp_code, otp_hash):
    """Verify OTP code against hash"""
    return check_password(otp_code, otp_hash)


def create_otp_verification(user, otp_type, sent_to, ip_address=None):
    """
    Create OTP verification record
    
    Args:
        user: User instance
        otp_type: Type of OTP (email_verification, phone_verification, etc.)
        sent_to: Email or phone where OTP is sent
        ip_address: User's IP address
    
    Returns:
        tuple: (OTPVerification instance, plain OTP code)
    """
    from .models import OTPVerification
    
    # Generate OTP
    otp_code = generate_otp(length=settings.OTP_LENGTH)
    
    # Create verification record
    otp_verification = OTPVerification.objects.create(
        user=user,
        otp_type=otp_type,
        otp_code_hash=hash_otp(otp_code),
        sent_to=sent_to,
        expires_at=timezone.now() + timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        ),
        ip_address=ip_address
    )
    
    return otp_verification, otp_code


def send_otp_email(email, otp_code, otp_type='verification'):
    # print(f"Sending OTP {otp_code} to email {email} for {otp_type}")
    """Send OTP via email"""
    subject_map = {
        'email_verification': 'Verify Your Email',
        'phone_verification': 'Verify Your Phone',
        'login_2fa': 'Your Login Code',
        'transfer_confirmation': 'Confirm Your Transfer',
        'password_reset': 'Reset Your Password',
    }
    
    subject = subject_map.get(otp_type, 'Your Verification Code')
    
    message = f"""
    Your verification code is: {otp_code}
    
    This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    Money Transfer Team
    """
    print(f"Default_From {settings.DEFAULT_FROM_EMAIL}")
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def send_otp_sms(phone, otp_code):
    """
    Send OTP via SMS
    
    TODO: Integrate with Africa's Talking or other SMS provider
    """
    message = f"Your verification code is: {otp_code}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes."
    
    # TODO: Implement SMS sending
    # Example with Africa's Talking:
    # from integrations.sms_provider import send_sms
    # send_sms(phone, message)
    
    # print(f"SMS to {phone}: {message}")  # Development only


# ============================================================================
# BIOMETRIC FUNCTIONS
# ============================================================================

def generate_biometric_challenge():
    """Generate random challenge for biometric authentication"""
    # Generate random bytes
    random_bytes = secrets.token_bytes(32)
    
    # Add timestamp
    timestamp = str(timezone.now().timestamp())
    
    # Combine and encode
    challenge_data = f"{base64.b64encode(random_bytes).decode()}-{timestamp}"
    
    return challenge_data


def verify_biometric_signature(challenge_data, signature, public_key_pem, algorithm='RSA-2048'):
    """
    Verify biometric signature
    
    Args:
        challenge_data: Original challenge string
        signature: Base64 encoded signature from device
        public_key_pem: User's public key in PEM format
        algorithm: Key algorithm (RSA-2048 or ECDSA-P256)
    
    Returns:
        bool: True if signature is valid
    """
    try:
        # Decode signature
        signature_bytes = base64.b64decode(signature)
        
        # Load public key
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode()
        )
        
        # Verify signature
        if algorithm == 'RSA-2048':
            public_key.verify(
                signature_bytes,
                challenge_data.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
        else:
            # ECDSA verification
            from cryptography.hazmat.primitives.asymmetric import ec
            public_key.verify(
                signature_bytes,
                challenge_data.encode(),
                ec.ECDSA(hashes.SHA256())
            )
        
        return True
    
    except InvalidSignature:
        return False
    except Exception as e:
        print(f"Signature verification error: {e}")
        return False


def validate_public_key(public_key_pem, algorithm='RSA-2048'):
    """
    Validate public key format
    
    Args:
        public_key_pem: Public key in PEM format
        algorithm: Expected algorithm
    
    Returns:
        bool: True if valid
    """
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode()
        )
        
        if algorithm == 'RSA-2048':
            if not isinstance(public_key, rsa.RSAPublicKey):
                return False
            if public_key.key_size != 2048:
                return False
        
        return True
    
    except Exception:
        return False


# ============================================================================
# PASSWORD & PIN FUNCTIONS
# ============================================================================

def hash_pin(pin):
    """Hash PIN for storage"""
    return make_password(pin)


def verify_pin(pin, pin_hash):
    """Verify PIN against hash"""
    return check_password(pin, pin_hash)


# ============================================================================
# IP ADDRESS FUNCTION
# ============================================================================

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ============================================================================
# TOKEN GENERATION
# ============================================================================

def generate_unique_token():
    """Generate unique token (UUID)"""
    import uuid
    return uuid.uuid4()
