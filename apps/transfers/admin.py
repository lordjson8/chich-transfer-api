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
        'sender_phone',
        'recipient_phone',
        'funding_mobile_provider',
        'payout_mobile_provider',
        'created_at',
    ]
    list_filter = ['status', 'currency', 'funding_mobile_provider', 'payout_mobile_provider', 'created_at']
    search_fields = [
        'reference',
        'deposit_reference',
        'withdrawal_reference',
        'user__email',
        'sender_phone',
        'sender_name',
        'recipient_name',
        'recipient_phone',
        'provider_id',
    ]
    readonly_fields = [
        'id',
        'reference',
        'provider_id',
        'deposit_reference',
        'deposit_status',
        'deposit_gateway',
        'deposit_initiated_at',
        'deposit_confirmed_at',
        'withdrawal_reference',
        'withdrawal_status',
        'withdrawal_gateway',
        'withdrawal_initiated_at',
        'withdrawal_confirmed_at',
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
        ('Sender', {
            'fields': (
                'sender_name',
                'sender_phone',
                'sender_email',
                'funding_mobile_provider',
            )
        }),
        ('Recipient', {
            'fields': (
                'recipient_name',
                'recipient_phone',
                'recipient_email',
                'payout_mobile_provider',
            )
        }),
        ('Source Amount', {
            'fields': (
                'amount',
                'currency',
                'service_fee',
                'total_amount',
            )
        }),
        ('Destination Amount', {
            'fields': (
                'destination_amount',
                'destination_currency',
            )
        }),
        ('Deposit Phase (AWDPay)', {
            'fields': (
                'deposit_reference',
                'deposit_status',
                'deposit_gateway',
                'deposit_initiated_at',
                'deposit_confirmed_at',
            ),
            'classes': ('collapse',),
        }),
        ('Withdrawal Phase (AWDPay)', {
            'fields': (
                'withdrawal_reference',
                'withdrawal_status',
                'withdrawal_gateway',
                'withdrawal_initiated_at',
                'withdrawal_confirmed_at',
            ),
            'classes': ('collapse',),
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
            'deposit_pending': '#2196F3',
            'deposit_confirmed': '#4CAF50',
            'deposit_failed': '#f44336',
            'withdrawal_pending': '#FF9800',
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
        'transfer__deposit_reference',
        'transfer__withdrawal_reference',
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
        return False

    def has_delete_permission(self, request, obj=None):
        return False
