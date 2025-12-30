# apps/transfers/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Transfer, TransferLimitSnapshot, TransferAuditLog


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = [
        'reference',
        'user',
        'status_colored',
        'amount',
        'currency',
        'recipient_name',
        'recipient_phone',
        'created_at',
    ]
    list_filter = ['status', 'currency', 'provider', 'created_at']
    search_fields = [
        'reference',
        'user__email',
        'recipient_name',
        'recipient_phone',
        'provider_id',
    ]
    readonly_fields = [
        'id',
        'reference',
        'provider_id',
        'created_at',
        'updated_at',
        'completed_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transfer Info', {
            'fields': (
                'id',
                'user',
                'reference',
                'status',
                'corridor',
            )
        }),
        ('Amount Details', {
            'fields': (
                'amount',
                'currency',
                'service_fee',
                'total_amount',
            )
        }),
        ('Recipient', {
            'fields': (
                'recipient_name',
                'recipient_phone',
                'recipient_email',
            )
        }),
        ('Payment Methods', {
            'fields': (
                'funding_method_type',
                'funding_mobile_provider',
                'funding_card_scheme',
                'payout_method_type',
                'payout_mobile_provider',
            )
        }),
        ('Provider', {
            'fields': (
                'provider',
                'provider_id',
            )
        }),
        ('Status & Errors', {
            'fields': (
                'error_code',
                'error_message',
                'description',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'completed_at',
                'deleted_at',
            )
        }),
    )
    
    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
            'reversed': 'purple',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'


@admin.register(TransferLimitSnapshot)
class TransferLimitSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'total_sent',
        'transfer_count',
        'daily_sent',
        'daily_count',
        'period_start',
        'period_end',
    ]
    search_fields = ['user__email']
    readonly_fields = [
        'period_start',
        'period_end',
        'daily_date',
        'updated_at',
    ]
    ordering = ['-updated_at']


@admin.register(TransferAuditLog)
class TransferAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'transfer_reference',
        'event',
        'created_at',
        'ip_address',
    ]
    list_filter = ['event', 'created_at']
    search_fields = [
        'transfer__reference',
        'transfer__user__email',
    ]
    readonly_fields = [
        'transfer',
        'event',
        'metadata',
        'ip_address',
        'created_at',
    ]
    ordering = ['-created_at']
    
    def transfer_reference(self, obj):
        return obj.transfer.reference
    transfer_reference.short_description = 'Transfer'
    transfer_reference.admin_order_field = 'transfer__reference'
    
    def has_add_permission(self, request):
        """Prevent manual creation"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion for audit purposes"""
        return False
