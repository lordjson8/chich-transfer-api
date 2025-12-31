from django.contrib import admin
from django.utils.html import format_html
from .models import KYCProfile, KYCDocument, KYCVerificationLog


@admin.register(KYCProfile)
class KYCProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'full_name',
        'kyc_level',
        'verification_status',
        'is_verified_status',
        'submitted_at',
        'verified_at',
    ]
    list_filter = ['kyc_level', 'verification_status', 'gender', 'country']
    search_fields = ['user__email', 'first_name', 'last_name', 'user__phone_number']
    readonly_fields = [
        'submitted_at',
        'verified_at',
        'rejected_at',
        'created_at',
        'updated_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': (
                'first_name',
                'last_name',
                'middle_name',
                'date_of_birth',
                'gender',
                'nationality',
            )
        }),
        ('Address', {
            'fields': (
                'address_line_1',
                'address_line_2',
                'city',
                'state_province',
                'postal_code',
                'country',
            )
        }),
        ('Verification Status', {
            'fields': (
                'kyc_level',
                'verification_status',
                'rejection_reason',
                'submitted_at',
                'verified_at',
                'rejected_at',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'
    
    def is_verified_status(self, obj):
        if obj.is_verified():
            return format_html('<span style="color: green; font-weight: bold;">✓ Verified</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    is_verified_status.short_description = 'Verified'
    
    def get_transaction_limits_display(self, obj):
        limits = obj.get_transaction_limit()
        return format_html(
            '<strong>Monthly:</strong> {}<br>'
            '<strong>Daily:</strong> {}<br>'
            '<strong>Per Transaction:</strong> {}',
            limits['monthly_limit'],
            limits['daily_limit'],
            limits['transaction_limit']
        )
    get_transaction_limits_display.short_description = 'Transaction Limits'


from django.contrib import admin
from .models import KYCProfile, KYCDocument
from django.utils import timezone

@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user_email',
        'document_type',
        'document_side',  # NEW
        'document_number',
        'status',
        'is_expired_status',
        'created_at',
    ]
    def user_email(self, obj):
        return obj.kyc_profile.user.email

    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"

    def is_expired_status(self, obj):
        if not obj.expiry_date:
            return False
        return obj.expiry_date < timezone.now().date()

    is_expired_status.short_description = "Expired"
    is_expired_status.boolean = True

    list_filter = ['document_type', 'document_side', 'status', 'created_at']  # Added document_side
    search_fields = [
        'kyc_profile__user__email',
        'kyc_profile__first_name',
        'kyc_profile__last_name',
        'document_number',
    ]
    readonly_fields = [
        'id',
        'file_size',
        'file_hash',
        'created_at',
        'updated_at',
        'verified_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Document Info', {
            'fields': (
                'id',
                'kyc_profile',
                'document_type',
                'document_side',  # NEW
                'document_file',
                'document_number',
                'issue_date',
                'expiry_date',
            )
        }),
        ('Verification', {
            'fields': (
                'status',
                'verified_at',
                'verification_notes',
            )
        }),
        ('File Metadata', {
            'fields': (
                'file_size',
                'file_hash',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )


@admin.register(KYCVerificationLog)
class KYCVerificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'kyc_profile',
        'action',
        'performed_by',
        'created_at',
    ]
    list_filter = ['action', 'created_at']
    search_fields = [
        'kyc_profile__user__email',
        'reason',
    ]
    readonly_fields = [
        'kyc_profile',
        'action',
        'performed_by',
        'reason',
        'ip_address',
        'user_agent',
        'created_at',
    ]
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Prevent manual creation"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion for audit purposes"""
        return False
