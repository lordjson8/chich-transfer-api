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
        return obj.user.email

    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"

    def is_expired_status(self, obj):
        if not obj.expires_at:
            return "—"
        return obj.expires_at < timezone.now().date()

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
