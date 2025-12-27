"""
Serializers for authentication
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from phonenumber_field.serializerfields import PhoneNumberField
from .models import User, UserDevice, OTPVerification
from .utils import verify_otp, validate_public_key


# ============================================================================
# USER SERIALIZERS
# ============================================================================

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'full_name', 'country',
            'email_verified', 'phone_verified', 'kyc_status',
            'kyc_level', 'two_factor_enabled', 'is_verified',
            'can_transfer', 'daily_limit', 'transaction_limit',
            'created_at'
        ]
        read_only_fields = [
            'id', 'email_verified', 'phone_verified',
            'kyc_status', 'kyc_level', 'is_verified',
            'can_transfer', 'created_at'
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text='Password must be at least 8 characters with uppercase, lowercase, and numbers'
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'phone', 'password',  # ← Removed password_confirm
            'full_name', 'country'
        ]
    
    # Remove the validate method since no password_confirm
    def validate(self, attrs):
        """Validate registration data"""

        print(f"attrs {attrs}")
        return super().validate(attrs)
    
    def create(self, validated_data):
        """Create user"""
        user = User.objects.create_user(
            email=validated_data['email'],
            phone=validated_data['phone'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            country=validated_data['country'],
            # is_active=False,  # Inactive until verified
        )
        
        return user

class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    device_id = serializers.CharField(required=True)
    device_name = serializers.CharField(required=False)
    device_type = serializers.ChoiceField(
        choices=['ios', 'android'],
        required=False
    )
    
    def validate(self, attrs):
        """Validate credentials"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError(
                'Must include "email" and "password".',
                code='required'
            )
        
        # Step 1: Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                'Invalid email or password.',
                code='invalid_credentials'
            )
        
        # Step 2: Check password
        if not user.check_password(password):
            raise serializers.ValidationError(
                'Invalid email or password.',
                code='invalid_credentials'
            )
        
        # Step 3: Check if account is active
        if not user.email_verified:
            # Return user data for verification flow
            attrs['user'] = None  # Set to None to indicate inactive
            attrs['inactive_user'] = user  # Pass the inactive user
            return attrs
        
        # Step 4: All checks passed
        attrs['user'] = user
        return attrs


# ============================================================================
# OTP SERIALIZERS
# ============================================================================

class OTPVerificationSerializer(serializers.Serializer):
    """OTP verification serializer"""
    
    user_id = serializers.IntegerField(required=True)
    otp = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6
    )
    otp_type = serializers.ChoiceField(
        choices=[
            'email_verification',
            'phone_verification',
            'login_2fa',
            'transfer_confirmation',
        ],
        required=True
    )
    
    def validate(self, attrs):
        """Validate OTP"""
        user_id = attrs.get('user_id')
        otp_code = attrs.get('otp')
        otp_type = attrs.get('otp_type')
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found.')
        
        # Get latest valid OTP
        otp_verification = OTPVerification.objects.filter(
            user=user,
            otp_type=otp_type,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp_verification:
            raise serializers.ValidationError('No OTP found. Please request a new one.')
        
        if not otp_verification.can_attempt():
            raise serializers.ValidationError(
                'Maximum attempts exceeded or OTP expired. Please request a new one.'
            )
        
        # Verify OTP
        if not verify_otp(otp_code, otp_verification.otp_code_hash):
            otp_verification.increment_attempts()
            remaining = otp_verification.max_attempts - otp_verification.attempts
            raise serializers.ValidationError(
                f'Invalid OTP code. {remaining} attempts remaining.'
            )
        
        attrs['user'] = user
        attrs['otp_verification'] = otp_verification
        return attrs


class ResendOTPSerializer(serializers.Serializer):
    """Resend OTP serializer"""
    
    user_id = serializers.IntegerField(required=True)
    otp_type = serializers.ChoiceField(
        choices=[
            'email_verification',
            'phone_verification',
        ],
        required=True
    )


# ============================================================================
# BIOMETRIC SERIALIZERS
# ============================================================================

class BiometricSetupSerializer(serializers.Serializer):
    """Biometric setup serializer"""
    
    device_id = serializers.CharField(required=True)
    public_key = serializers.CharField(required=True)
    algorithm = serializers.ChoiceField(
        choices=['RSA-2048', 'ECDSA-P256'],
        default='RSA-2048'
    )
    
    def validate_public_key(self, value):
        """Validate public key format"""
        algorithm = self.initial_data.get('algorithm', 'RSA-2048')
        
        if not validate_public_key(value, algorithm):
            raise serializers.ValidationError('Invalid public key format.')
        
        return value


class BiometricLoginRequestSerializer(serializers.Serializer):
    """Request biometric challenge"""
    
    device_id = serializers.CharField(required=True)


class BiometricLoginVerifySerializer(serializers.Serializer):
    """Verify biometric signature"""
    
    challenge_id = serializers.UUIDField(required=True)
    signature = serializers.CharField(required=True)
    device_id = serializers.CharField(required=True)
