"""
Authentication URLs
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'authentication'

urlpatterns = [
    # Registration & Login
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # OTP Verification
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('verify-phone/', views.VerifyPhoneView.as_view(), name='verify-phone'),
    path('verify-2fa/', views.Verify2FAView.as_view(), name='verify-2fa'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    
    # Biometric Authentication
    path('biometric/setup/', views.BiometricSetupView.as_view(), name='biometric-setup'),
    path('biometric/challenge/', views.BiometricChallengeView.as_view(), name='biometric-challenge'),
    path('biometric/verify/', views.BiometricVerifyView.as_view(), name='biometric-verify'),
    
    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('me/', views.MeView.as_view(), name='me'),
    path('me/update/', views.UpdateProfileView.as_view(), name='update-profile'),

    
    # JWT Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

     # Password Management
    path('password/request-reset/', views.RequestPasswordResetView.as_view(), name='request-password-reset'),
    path(
        "password/request-reset-email/",
        views.RequestPasswordViewNew.as_view(),
        name="password-reset-request-email",
    ),
    path(
        "reset-password/",
        views.ResetPasswordTemplateView.as_view(),
        name="password-reset-html",
    ),
    path('password/verify-token/', views.VerifyPasswordResetTokenView.as_view(), name='verify-reset-token'),
    path('password/reset/', views.ResetPasswordView.as_view(), name='reset-password'),
    path('password/change/', views.ChangePasswordView.as_view(), name='change-password'),
]
