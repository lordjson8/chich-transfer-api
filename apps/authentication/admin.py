"""
Admin interface for authentication models
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User, UserDevice, OTPVerification, 
    BiometricChallenge, PasswordResetToken
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin"""
    
    list_display = [
        'email', 'phone', 'full_name', 'country',
        'kyc_status_badge', 'is_verified_badge',
        'two_factor_enabled', 'is_active', 'created_at'
    ]
    list_filter = [
        'kyc_status', 'kyc_level', 'email_verified',
        'phone_verified', 'two_factor_enabled',
        'is_active', 'is_staff', 'country', 'created_at'
    ]
    search_fields = ['email', 'phone', 'full_name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'phone', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'country', 'date_of_birth')
        }),
        ('Verification Status', {
            'fields': (
                'email_verified', 'phone_verified',
                'kyc_status', 'kyc_level', 'kyc_verified_at'
            )
        }),
        ('Security', {
            'fields': ('two_factor_enabled', 'pin_hash')
        }),
        ('Limits', {
            'fields': ('daily_limit', 'transaction_limit')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            )
        }),
        ('Metadata', {
            'fields': (
                'last_login', 'last_login_ip',
                'last_login_device', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': (
                'email', 'phone', 'password1', 'password2',
                'full_name', 'country', 'is_active'
            ),
        }),
    )
    
    readonly_fields = [
        'created_at', 'updated_at', 'last_login',
        'kyc_verified_at'
    ]
    
    def kyc_status_badge(self, obj):
        """Display KYC status with color badge"""
        colors = {
            'pending': 'gray',
            'submitted': 'orange',
            'approved': 'green',
            'rejected': 'red',
        }
        color = colors.get(obj.kyc_status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; '
            'color: white; border-radius: 3px;">{}</span>',
            color, obj.kyc_status.upper()
        )
    kyc_status_badge.short_description = 'KYC Status'
    
    def is_verified_badge(self, obj):
        """Display verification status"""
        if obj.is_verified:
            return format_html(
                '<span style="color: green;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Not Verified</span>'
        )
    is_verified_badge.short_description = 'Verified'


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    """User Device admin"""
    
    list_display = [
        'user', 'device_name', 'device_type',
        'biometric_enabled', 'is_trusted',
        'last_login_at', 'created_at'
    ]
    list_filter = [
        'device_type', 'biometric_enabled',
        'is_trusted', 'created_at'
    ]
    search_fields = ['user__email', 'device_id', 'device_name']
    readonly_fields = [
        'device_id', 'created_at', 'updated_at',
        'last_login_at', 'last_login_ip'
    ]
    ordering = ['-last_login_at']
    
    fieldsets = (
        ('Device Info', {
            'fields': (
                'user', 'device_id', 'device_name',
                'device_type', 'os_version', 'app_version'
            )
        }),
        ('Biometric', {
            'fields': (
                'biometric_enabled', 'biometric_public_key',
                'biometric_key_algorithm'
            )
        }),
        ('Security', {
            'fields': (
                'is_trusted', 'last_login_at', 'last_login_ip'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """OTP Verification admin"""
    
    list_display = [
        'user', 'otp_type', 'sent_to',
        'is_used', 'is_expired_display',
        'attempts', 'created_at', 'expires_at'
    ]
    list_filter = [
        'otp_type', 'is_used', 'created_at'
    ]
    search_fields = ['user__email', 'sent_to']
    readonly_fields = [
        'otp_code_hash', 'created_at',
        'expires_at', 'verified_at', 'ip_address'
    ]
    ordering = ['-created_at']
    
    def is_expired_display(self, obj):
        """Display if OTP is expired"""
        if obj.is_expired:
            return format_html('<span style="color: red;">✗ Expired</span>')
        return format_html('<span style="color: green;">✓ Valid</span>')
    is_expired_display.short_description = 'Status'


@admin.register(BiometricChallenge)
class BiometricChallengeAdmin(admin.ModelAdmin):
    """Biometric Challenge admin"""
    
    list_display = [
        'user', 'device', 'challenge_id',
        'is_used', 'created_at', 'expires_at'
    ]
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'challenge_id']
    readonly_fields = [
        'challenge_id', 'challenge_data',
        'created_at', 'expires_at', 'verified_at', 'ip_address'
    ]
    ordering = ['-created_at']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Password Reset Token admin"""
    
    list_display = [
        'user', 'token', 'is_used',
        'created_at', 'expires_at'
    ]
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = [
        'token', 'created_at', 'expires_at',
        'used_at', 'ip_address'
    ]
    ordering = ['-created_at']
