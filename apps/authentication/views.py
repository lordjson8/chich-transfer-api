"""
Authentication API Views
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from .models import User, UserDevice, OTPVerification, BiometricChallenge
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    OTPVerificationSerializer, ResendOTPSerializer,
    BiometricSetupSerializer, BiometricLoginRequestSerializer,
    BiometricLoginVerifySerializer
)
from .utils import (
    create_otp_verification, send_otp_email, send_otp_sms,
    get_client_ip, generate_biometric_challenge,
    verify_biometric_signature
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def create_or_update_device(user, device_id, device_name=None, device_type=None, ip_address=None):
    """Create or update user device"""
    device, created = UserDevice.objects.get_or_create(
        user=user,
        device_id=device_id,
        defaults={
            'device_name': device_name or 'Unknown Device',
            'device_type': device_type or 'android',
        }
    )
    
    # Update last login info
    device.last_login_at = timezone.now()
    device.last_login_ip = ip_address
    device.save(update_fields=['last_login_at', 'last_login_ip'])
    
    return device


# ============================================================================
# REGISTRATION & LOGIN
# ============================================================================

class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint
    
    POST /api/auth/register
    {
        "email": "user@example.com",
        "phone": "+2250748672248",
        "password": "SecurePass123",
        "password_confirm": "SecurePass123",
        "full_name": "John Doe",
        "country": "CI"
    }
    """
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create user
        user = serializer.create(serializer.validated_data)
        
        # Get IP address
        ip_address = get_client_ip(request)

        print(ip_address,user)
        
        # Create OTP for email verification
        email_otp_verification, email_otp_code = create_otp_verification(
            user=user,
            otp_type='email_verification',
            sent_to=user.email,
            ip_address=ip_address
        )
        
        # Create OTP for phone verification
        phone_otp_verification, phone_otp_code = create_otp_verification(
            user=user,
            otp_type='phone_verification',
            sent_to=str(user.phone),
            ip_address=ip_address
        )
        
        # Send OTPs
        try:
            
            send_otp_email(user.email, email_otp_code, 'email_verification')
            send_otp_sms(str(user.phone), phone_otp_code)
            print('sent_otp')
        except Exception as e:
            # Log error but don't fail registration
            print(f"Error sending OTP: {e}")
        
        return Response({
            'success': True,
            'message': 'Registration successful. Please verify your email and phone.',
            'data': {
                'user_id': user.id,
                'email': user.email,
                'phone': str(user.phone),
                'email_masked': f"{user.email[:2]}***@{user.email.split('@')[1]}",
                'phone_masked': f"{str(user.phone)[:8]}***{str(user.phone)[-4:]}",
                'requires_verification': True
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """User login with email and password"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        # Validate
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is inactive
        inactive_user = serializer.validated_data.get('inactive_user')
        
        if inactive_user:
            # User exists and password is correct, but account not active
            return Response({
                'success': False,
                'error': 'Account not verified',
                'error_code': 'ACCOUNT_NOT_VERIFIED',
                'message': 'Please verify your email and phone number to activate your account.',
                'data': {
                    'user_id': inactive_user.id,
                    'email': inactive_user.email,
                    'phone': str(inactive_user.phone),
                    'email_verified': inactive_user.email_verified,
                    'phone_verified': inactive_user.phone_verified,
                    'email_masked': f"{inactive_user.email[:2]}***@{inactive_user.email.split('@')[1]}",
                    'phone_masked': f"{str(inactive_user.phone)[:8]}***{str(inactive_user.phone)[-4:]}",
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get active user
        user = serializer.validated_data['user']
        device_id = serializer.validated_data['device_id']
        device_name = serializer.validated_data.get('device_name')
        device_type = serializer.validated_data.get('device_type')
        
        # Check if 2FA is enabled
        if user.two_factor_enabled:
            ip_address = get_client_ip(request)
            otp_verification, otp_code = create_otp_verification(
                user=user,
                otp_type='login_2fa',
                sent_to=str(user.phone),
                ip_address=ip_address
            )
            
            # Send OTP
            send_otp_sms(str(user.phone), otp_code)
            
            return Response({
                'success': True,
                'requires_2fa': True,
                'message': 'OTP sent to your phone. Please verify to complete login.',
                'data': {
                    'user_id': user.id,
                    'phone_masked': f"{str(user.phone)[:8]}***{str(user.phone)[-4:]}"
                }
            })
        
        # Create/update device
        ip_address = get_client_ip(request)
        device = create_or_update_device(
            user, device_id, device_name, device_type, ip_address
        )
        
        # Update user last login info
        user.last_login_ip = ip_address
        user.last_login_device = device_name or device_id
        user.save(update_fields=['last_login_ip', 'last_login_device'])
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'data': {
                'user': UserSerializer(user).data,
                'tokens': tokens
            }
        })

# ============================================================================
# USER PROFILE
# ============================================================================

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update user profile
    
    GET /api/auth/profile
    PUT /api/auth/profile
    PATCH /api/auth/profile
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """
    Logout user (blacklist refresh token)
    
    POST /api/auth/logout
    {
        "refresh": "refresh-token-here"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({
                    'success': False,
                    'error': 'Refresh token required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# ============================================================================
# OTP VERIFICATION
# ============================================================================

class VerifyEmailView(APIView):
    """
    Verify email with OTP
    
    POST /api/auth/verify-email
    {
        "user_id": 1,
        "otp": "123456",
        "otp_type": "email_verification"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Force otp_type to email_verification
        data = request.data.copy()
        data['otp_type'] = 'email_verification'
        
        serializer = OTPVerificationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        otp_verification = serializer.validated_data['otp_verification']
        
        # Mark OTP as used
        otp_verification.mark_as_used()
        
        # Mark email as verified
        user.email_verified = True
        
        # If both email and phone verified, activate account
        # if user.phone_verified:
        user.is_active = True
        
        user.save(update_fields=['email_verified', 'is_active'])
        
        # Generate tokens if account is active
        tokens = None
        if user.is_active:
            tokens = get_tokens_for_user(user)
        
        return Response({
            'success': True,
            'message': 'Email verified successfully',
            'data': {
                'email_verified': True,
                'phone_verified': user.phone_verified,
                'account_active': user.is_active,
                'tokens': tokens,
                    'user': UserSerializer(user).data if user.is_active else None
            }
        })


class VerifyPhoneView(APIView):
    """
    Verify phone with OTP
    
    POST /api/auth/verify-phone
    {
        "user_id": 1,
        "otp": "789012",
        "otp_type": "phone_verification"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Force otp_type to phone_verification
        data = request.data.copy()
        data['otp_type'] = 'phone_'


class Verify2FAView(APIView):
    """
    Verify 2FA OTP for login
    
    POST /api/auth/verify-2fa
    {
        "user_id": 1,
        "otp": "456789",
        "otp_type": "login_2fa",
        "device_id": "abc-123-device-id"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Force otp_type to login_2fa
        data = request.data.copy()
        data['otp_type'] = 'login_2fa'
        
        serializer = OTPVerificationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        otp_verification = serializer.validated_data['otp_verification']
        device_id = request.data.get('device_id')
        
        if not device_id:
            return Response({
                'success': False,
                'error': 'device_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as used
        otp_verification.mark_as_used()
        
        # Create/update device
        ip_address = get_client_ip(request)
        device = create_or_update_device(
            user, device_id, ip_address=ip_address
        )
        
        # Update user last login
        user.last_login_ip = ip_address
        user.save(update_fields=['last_login_ip'])
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'success': True,
            'message': '2FA verification successful',
            'data': {
                'user': UserSerializer(user).data,
                'tokens': tokens
            }
        })

class ResendOTPView(APIView):
    """
    Resend OTP
    
    POST /api/auth/resend-otp
    {
        "user_id": 1,
        "otp_type": "email_verification"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        otp_type = serializer.validated_data['otp_type']
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check cooldown (prevent spam)
        last_otp = OTPVerification.objects.filter(
            user=user,
            otp_type=otp_type
        ).order_by('-created_at').first()
        
        if last_otp:
            time_since_last = timezone.now() - last_otp.created_at
            if time_since_last < timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS):
                remaining = settings.OTP_RESEND_COOLDOWN_SECONDS - time_since_last.seconds
                return Response({
                    'success': False,
                    'error': f'Please wait {remaining} seconds before requesting a new OTP'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Create new OTP
        ip_address = get_client_ip(request)
        
        if otp_type == 'email_verification':
            sent_to = user.email
            otp_verification, otp_code = create_otp_verification(
                user, otp_type, sent_to, ip_address
            )
            send_otp_email(user.email, otp_code, otp_type)
            masked = f"{user.email[:2]}***@{user.email.split('@')[1]}"
        else:  # phone_verification
            sent_to = str(user.phone)
            otp_verification, otp_code = create_otp_verification(
                user, otp_type, sent_to, ip_address
            )
            send_otp_sms(str(user.phone), otp_code)
            masked = f"{str(user.phone)[:8]}***{str(user.phone)[-4:]}"
        
        return Response({
            'success': True,
            'message': f'OTP sent to {masked}',
            'data': {
                'otp_type': otp_type,
                'sent_to_masked': masked,
                'expires_at': otp_verification.expires_at.isoformat()
            }
        })

# ============================================================================
# BIOMETRIC AUTHENTICATION
# ============================================================================

class BiometricSetupView(APIView):
    """
    Setup biometric authentication
    
    POST /api/auth/biometric/setup
    {
        "device_id": "abc-123-device-id",
        "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
        "algorithm": "RSA-2048"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = BiometricSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        device_id = serializer.validated_data['device_id']
        public_key = serializer.validated_data['public_key']
        algorithm = serializer.validated_data['algorithm']
        
        # Get or create device
        try:
            device = UserDevice.objects.get(
                user=request.user,
                device_id=device_id
            )
        except UserDevice.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Device not found. Please login first.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Enable biometric
        device.biometric_enabled = True
        device.biometric_public_key = public_key
        device.biometric_key_algorithm = algorithm
        device.save(update_fields=[
            'biometric_enabled',
            'biometric_public_key',
            'biometric_key_algorithm'
        ])
        
        return Response({
            'success': True,
            'message': 'Biometric authentication enabled successfully',
            'data': {
                'device_id': device_id,
                'biometric_enabled': True,
                'algorithm': algorithm
            }
        })


class BiometricChallengeView(APIView):
    """
    Request biometric challenge
    
    POST /api/auth/biometric/challenge
    {
        "device_id": "abc-123-device-id"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = BiometricLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        device_id = serializer.validated_data['device_id']
        
        # Get device
        try:
            device = UserDevice.objects.get(device_id=device_id)
        except UserDevice.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Device not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if not device.biometric_enabled:
            return Response({
                'success': False,
                'error': 'Biometric not enabled for this device'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate challenge
        challenge_data = generate_biometric_challenge()
        ip_address = get_client_ip(request)
        
        # Create challenge record
        challenge = BiometricChallenge.objects.create(
            user=device.user,
            device=device,
            challenge_data=challenge_data,
            expires_at=timezone.now() + timedelta(minutes=5),
            ip_address=ip_address
        )
        
        return Response({
            'success': True,
            'data': {
                'challenge_id': str(challenge.challenge_id),
                'challenge': challenge_data,
                'expires_at': challenge.expires_at.isoformat()
            }
        })


class BiometricVerifyView(APIView):
    """
    Verify biometric signature
    
    POST /api/auth/biometric/verify
    {
        "challenge_id": "uuid-here",
        "signature": "base64-encoded-signature",
        "device_id": "abc-123-device-id"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = BiometricLoginVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        challenge_id = serializer.validated_data['challenge_id']
        signature = serializer.validated_data['signature']
        device_id = serializer.validated_data['device_id']
        
        # Get challenge
        try:
            challenge = BiometricChallenge.objects.get(
                challenge_id=challenge_id,
                device__device_id=device_id
            )
        except BiometricChallenge.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Challenge not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate challenge
        if not challenge.is_valid:
            return Response({
                'success': False,
                'error': 'Challenge expired or already used'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify signature
        device = challenge.device
        is_valid = verify_biometric_signature(
            challenge.challenge_data,
            signature,
            device.biometric_public_key,
            device.biometric_key_algorithm
        )
        
        if not is_valid:
            return Response({
                'success': False,
                'error': 'Invalid signature'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Mark challenge as used
        challenge.mark_as_used()
        
        # Update device last login
        ip_address = get_client_ip(request)
        device.last_login_at = timezone.now()
        device.last_login_ip = ip_address
        device.save(update_fields=['last_login_at', 'last_login_ip'])
        
        # Update user last login
        user = challenge.user
        user.last_login_ip = ip_address
        user.save(update_fields=['last_login_ip'])
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'success': True,
            'message': 'Biometric authentication successful',
            'data': {
                'user': UserSerializer(user).data,
                'tokens': tokens
            }
        })
