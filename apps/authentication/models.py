"""
Authentication Models
- Custom User with email as primary identifier
- UserDevice for biometric authentication
- OTPVerification for email/phone verification
- BiometricChallenge for secure biometric login
"""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from phonenumber_field.modelfields import PhoneNumberField
from datetime import timedelta
import secrets



# ============================================================================
# USER MANAGER
# ============================================================================
class UserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier"""
    
    def create_user(self, email, phone, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError('Email address is required')
        if not phone:
            raise ValueError('Phone number is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, phone, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('phone_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, phone, password, **extra_fields)


# ============================================================================
# USER MODEL
# ============================================================================
class User(AbstractUser):
    """Custom User model with email as primary identifier"""
    
    # Remove username field (we use email instead)
    username = None
    
    # Authentication fields
    email = models.EmailField(
        unique=True,
        db_index=True,
        error_messages={
            'unique': 'A user with that email already exists.',
        }
    )
    phone = PhoneNumberField(
        unique=True,
        db_index=True,
        error_messages={
            'unique': 'A user with that phone number already exists.',
        }
    )
    
    # Personal information
    full_name = models.CharField(max_length=200, blank=True)
    country = models.CharField(
        max_length=2,
        help_text='ISO 3166-1 alpha-2 country code'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Verification status
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    # KYC status
    KYC_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    kyc_status = models.CharField(
        max_length=20,
        choices=KYC_STATUS_CHOICES,
        default='pending'
    )
    kyc_level = models.CharField(
        max_length=20,
        choices=[
            ('none', 'None'),
            ('basic', 'Basic'),
            ('advanced', 'Advanced'),
        ],
        default='none'
    )
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Security settings
    two_factor_enabled = models.BooleanField(default=False)
    pin_hash = models.CharField(max_length=255, blank=True)
    
    # Transaction limits (in EUR)
    daily_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5000.00
    )
    transaction_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000.00
    )
    
    # Metadata
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_device = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'is_active']),
            models.Index(fields=['phone', 'is_active']),
            models.Index(fields=['kyc_status']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def is_verified(self):
        """Check if both email and phone are verified"""
        return self.email_verified and self.phone_verified
    
    @property
    def can_transfer(self):
        """Check if user can make transfers"""
        return self.is_verified and self.kyc_status == 'approved' and self.is_active
    
    def get_remaining_daily_limit(self):
        """Calculate remaining daily transfer limit"""
        from apps.transfers.models import Transaction
        today = timezone.now().date()
        
        total_sent_today = Transaction.objects.filter(
            user=self,
            created_at__date=today,
            status__in=['processing', 'completed']
        ).aggregate(
            total=models.Sum('send_amount')
        )['total'] or 0
        
        return max(0, self.daily_limit - total_sent_today)


# ============================================================================
# USER DEVICE MODEL
# ============================================================================
class UserDevice(models.Model):
    """Store user devices and biometric public keys"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='devices'
    )
    device_id = models.CharField(
        max_length=255,
        # unique=True,
        db_index=True,
        help_text='Unique device identifier from mobile app'
    )
    device_name = models.CharField(
        max_length=255,
        help_text='e.g., iPhone 15 Pro, Samsung Galaxy S24'
    )
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('ios', 'iOS'),
            ('android', 'Android'),
        ]
    )
    
    # Biometric authentication
    biometric_enabled = models.BooleanField(default=False)
    biometric_public_key = models.TextField(
        blank=True,
        help_text='RSA/ECDSA public key for biometric verification'
    )
    biometric_key_algorithm = models.CharField(
        max_length=20,
        choices=[
            ('RSA-2048', 'RSA-2048'),
            ('ECDSA-P256', 'ECDSA-P256'),
        ],
        blank=True
    )
    
    # Device info
    os_version = models.CharField(max_length=50, blank=True)
    app_version = models.CharField(max_length=50, blank=True)
    
    # Security
    is_trusted = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_devices'
        verbose_name = 'User Device'
        verbose_name_plural = 'User Devices'
        ordering = ['-last_login_at']
        unique_together = [['user', 'device_id']]
        indexes = [
            models.Index(fields=['user', 'is_trusted']),
            models.Index(fields=['device_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.device_name}"


# ============================================================================
# OTP VERIFICATION MODEL
# ============================================================================
class OTPVerification(models.Model):
    """Store OTP codes for verification"""
    
    OTP_TYPE_CHOICES = [
        ('email_verification', 'Email Verification'),
        ('phone_verification', 'Phone Verification'),
        ('login_2fa', 'Login 2FA'),
        ('transfer_confirmation', 'Transfer Confirmation'),
        ('password_reset', 'Password Reset'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_verifications'
    )
    otp_type = models.CharField(max_length=30, choices=OTP_TYPE_CHOICES)
    otp_code_hash = models.CharField(
        max_length=255,
        help_text='Hashed OTP code (never store plain text)'
    )
    
    # Where OTP was sent
    sent_to = models.CharField(
        max_length=255,
        help_text='Email or phone number where OTP was sent'
    )
    
    # Expiry and usage
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Rate limiting
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'otp_verifications'
        verbose_name = 'OTP Verification'
        verbose_name_plural = 'OTP Verifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'otp_type', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.otp_type}"
    
    @property
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if OTP is still valid"""
        return not self.is_used and not self.is_expired and self.attempts < self.max_attempts
    
    def can_attempt(self):
        """Check if user can attempt verification"""
        return self.is_valid and self.attempts < self.max_attempts
    
    def increment_attempts(self):
        """Increment attempt counter"""
        self.attempts += 1
        self.save(update_fields=['attempts'])
    
    def mark_as_used(self):
        """Mark OTP as used"""
        self.is_used = True
        self.verified_at = timezone.now()
        self.save(update_fields=['is_used', 'verified_at'])


# ============================================================================
# BIOMETRIC CHALLENGE MODEL
# ============================================================================
class BiometricChallenge(models.Model):
    """Store biometric authentication challenges"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='biometric_challenges'
    )
    device = models.ForeignKey(
        UserDevice,
        on_delete=models.CASCADE,
        related_name='challenges'
    )
    
    # Challenge data
    challenge_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True
    )
    challenge_data = models.TextField(
        help_text='Random challenge string to be signed'
    )
    
    # Status
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'biometric_challenges'
        verbose_name = 'Biometric Challenge'
        verbose_name_plural = 'Biometric Challenges'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['challenge_id', 'is_used']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.challenge_id}"
    
    @property
    def is_expired(self):
        """Check if challenge has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if challenge is still valid"""
        return not self.is_used and not self.is_expired
    
    def mark_as_used(self):
        """Mark challenge as used"""
        self.is_used = True
        self.verified_at = timezone.now()
        self.save(update_fields=['is_used', 'verified_at'])


# ============================================================================
# PASSWORD RESET TOKEN MODEL
# ============================================================================
# class PasswordResetToken(models.Model):
#     """Store password reset tokens"""
    
#     user = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name='password_reset_tokens'
#     )
#     token = models.UUIDField(
#         default=uuid.uuid4,
#         unique=True,
#         db_index=True
#     )
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     expires_at = models.DateTimeField()
#     is_used = models.BooleanField(default=False)
#     used_at = models.DateTimeField(null=True, blank=True)
    
#     ip_address = models.GenericIPAddressField(null=True, blank=True)
    
#     class Meta:
#         db_table = 'password_reset_tokens'
#         verbose_name = 'Password Reset Token'
#         verbose_name_plural = 'Password Reset Tokens'
#         ordering = ['-created_at']
    
#     def __str__(self):
#         return f"{self.user.email} - {self.token}"
    
#     @property
#     def is_expired(self):
#         return timezone.now() > self.expires_at
    
#     @property
#     def is_valid(self):
#         return not self.is_used and not self.is_expired


# Password Reset



class PasswordResetToken(models.Model):
    """Token for password reset - expires after 1 hour"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token', 'expires_at']),
            models.Index(fields=['user', 'used_at']),
        ]
    
    def is_valid(self):
        """Check if token is still valid"""
        return (
            self.used_at is None and
            timezone.now() < self.expires_at
        )
    
    def mark_as_used(self):
        """Mark token as used"""
        self.used_at = timezone.now()
        self.is_used = True
        self.save(update_fields=['used_at','is_used'])
    
    @classmethod
    def create_token(cls, user, ip_address=None, valid_for_hours=1):
        """Create a new reset token"""
        # Delete old valid tokens to prevent multiple active tokens
        cls.objects.filter(
            user=user,
            used_at__isnull=True,
            expires_at__gt=timezone.now()
        ).delete()
        
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=valid_for_hours)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            ip_address=ip_address
        )
    
    def __str__(self):
        return f"Reset token for {self.user.email}"


class PasswordHistory(models.Model):
    """Track password changes for security audit"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_history')
    password_hash = models.CharField(max_length=255)
    changed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reason = models.CharField(
        max_length=50,
        choices=[
            ('reset', 'Password Reset'),
            ('change', 'Password Change'),
            ('forced', 'Forced Change'),
        ]
    )
    
    class Meta:
        verbose_name = "Password History"
        verbose_name_plural = "Password Histories"
        ordering = ['-changed_at']
    
    @classmethod
    def record_password_change(cls, user, ip_address=None, reason='change'):
        """Record password change in history"""
        return cls.objects.create(
            user=user,
            password_hash=user.password,
            ip_address=ip_address,
            reason=reason
        )
    
    def __str__(self):
        return f"{self.user.email} - {self.reason} ({self.changed_at})"
