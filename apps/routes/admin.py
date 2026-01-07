# apps/routes/admin.py - COMPLETE FILE

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import Country, PaymentMethod, Corridor

class PriorityFilter(admin.SimpleListFilter):
    title = 'priority'
    parameter_name = 'priority'

    def lookups(self, request, model_admin):
        return (
            ('high', 'High (>= 10)'),
            ('medium', 'Medium (5–9)'),
            ('low', 'Low (< 5)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'high':
            return queryset.filter(priority__gte=10)
        if self.value() == 'medium':
            return queryset.filter(priority__range=(5, 9))
        if self.value() == 'low':
            return queryset.filter(priority__lt=5)
        return queryset



@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """Admin for Country model with stats and badges"""
    
    list_display = [
        'iso_code',
        'name',
        'phone_prefix',
        'payment_methods_count',
        'outgoing_corridors_count',
        'incoming_corridors_count',
        'is_active_badge',
    ]
    
    list_filter = ['is_active', 'name']
    search_fields = ['iso_code', 'name', 'phone_prefix']
    ordering = ['name']
    
    fieldsets = (
        ('Country Information', {
            'fields': ('iso_code', 'name', 'phone_prefix'),
            'description': 'Basic country details'
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            payment_methods_count=Count('payment_methods'),
            outgoing_corridors_count=Count('outgoing_corridors'),
            incoming_corridors_count=Count('incoming_corridors'),
        )
        return queryset
    
    def payment_methods_count(self, obj):
        count = obj.payment_methods_count
        return format_html(
            '<span style="background-color: #e3f2fd; color: #1976d2; padding: 4px 10px; border-radius: 4px; font-weight: bold;">{} methods</span>',
            count
        )
    payment_methods_count.short_description = 'Payment Methods'
    payment_methods_count.admin_order_field = 'payment_methods_count'
    
    def outgoing_corridors_count(self, obj):
        count = obj.outgoing_corridors_count
        return format_html(
            '<span style="background-color: #c8e6c9; color: #388e3c; padding: 4px 10px; border-radius: 4px; font-weight: bold;">📤 {}</span>',
            count
        )
    outgoing_corridors_count.short_description = 'Sending To'
    outgoing_corridors_count.admin_order_field = 'outgoing_corridors_count'
    
    def incoming_corridors_count(self, obj):
        count = obj.incoming_corridors_count
        return format_html(
            '<span style="background-color: #ffe0b2; color: #e65100; padding: 4px 10px; border-radius: 4px; font-weight: bold;">📥 {}</span>',
            count
        )
    incoming_corridors_count.short_description = 'Receiving From'
    incoming_corridors_count.admin_order_field = 'incoming_corridors_count'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: white; background-color: #4caf50; padding: 4px 10px; border-radius: 4px; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: white; background-color: #f44336; padding: 4px 10px; border-radius: 4px; font-weight: bold;">✕ Inactive</span>'
            )
    is_active_badge.short_description = 'Status'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin for PaymentMethod model with method type indicators"""
    
    list_display = [
        'id',
        'country',
        'display_name',
        'method_type_badge',
        'type_category_badge',
        'priority',
        'is_active_badge',
    ]
    
    list_filter = [
        'is_active',
        'country',
        'method_type',
        'type_category',
        PriorityFilter,
    ]
    
    search_fields = [
        'country__name',
        'country__iso_code',
        'mobile_provider',
        'card_scheme',
    ]
    
    fieldsets = (
        ('Country & Method Type', {
            'fields': ('country', 'method_type', 'type_category'),
        }),
        ('Payment Method Details', {
            'fields': ('mobile_provider', 'card_scheme'),
            'description': 'Fill in based on the method type selected above'
        }),
        ('Configuration', {
            'fields': ('priority', 'is_active'),
            'description': 'Higher priority = displayed first. Active = available for transfers'
        }),
    )
    
    readonly_fields = []
    ordering = ['country', '-priority', 'method_type']
    
    def display_name(self, obj):
        return obj.get_display_name()
    display_name.short_description = 'Display Name'
    
    def method_type_badge(self, obj):
        colors = {
            'mobile_money': '#2196F3',
            'card': '#FF9800',
            'bank': '#4CAF50',
        }
        icons = {
            'mobile_money': '📱',
            'card': '💳',
            'bank': '🏦',
        }
        color = colors.get(obj.method_type, '#999')
        icon = icons.get(obj.method_type, '')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_method_type_display()
        )
    method_type_badge.short_description = 'Type'
    method_type_badge.admin_order_field = 'method_type'
    
    def type_category_badge(self, obj):
        colors = {
            'funding': '#81C784',
            'payout': '#64B5F6',
            'both': '#9575CD',
        }
        icons = {
            'funding': '💸',
            'payout': '📥',
            'both': '⇄',
        }
        color = colors.get(obj.type_category, '#999')
        icon = icons.get(obj.type_category, '')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_type_category_display()
        )
    type_category_badge.short_description = 'Usage'
    type_category_badge.admin_order_field = 'type_category'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: white; background-color: #4caf50; padding: 4px 10px; border-radius: 4px;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: white; background-color: #f44336; padding: 4px 10px; border-radius: 4px;">✕ Inactive</span>'
            )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    actions = ['activate_methods', 'deactivate_methods', 'increase_priority', 'decrease_priority']
    
    def activate_methods(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'✓ {updated} payment method(s) activated')
    activate_methods.short_description = '✓ Activate selected methods'
    
    def deactivate_methods(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'✕ {updated} payment method(s) deactivated')
    deactivate_methods.short_description = '✕ Deactivate selected methods'
    
    def increase_priority(self, request, queryset):
        for obj in queryset:
            obj.priority += 1
            obj.save()
        self.message_user(request, f'Priority increased for {queryset.count()} method(s)')
    increase_priority.short_description = '⬆ Increase priority (display higher)'
    
    def decrease_priority(self, request, queryset):
        for obj in queryset:
            obj.priority -= 1
            obj.save()
        self.message_user(request, f'Priority decreased for {queryset.count()} method(s)')
    decrease_priority.short_description = '⬇ Decrease priority (display lower)'


@admin.register(Corridor)
class CorridorAdmin(admin.ModelAdmin):
    """Admin for Corridor model with route validation and fee management"""
    
    list_display = [
        'corridor_arrow',
        'is_active_badge',
        'fee_display',
        'amount_limits',
        'source_methods_count',
        'destination_methods_count',
        'created_at',
    ]
    
    list_filter = [
        'is_active',
        'source_country',
        'destination_country',
        'created_at',
    ]
    
    search_fields = [
        'source_country__name',
        'source_country__iso_code',
        'destination_country__name',
        'destination_country__iso_code',
    ]
    
    fieldsets = (
        ('Route Configuration', {
            'fields': ('source_country', 'destination_country', 'is_active'),
            'description': 'Define the transfer route'
        }),
        ('Fee Structure', {
            'fields': ('fixed_fee', 'percentage_fee'),
            'description': 'Configure fees - users pay both fixed + percentage fees'
        }),
        ('Amount Constraints', {
            'fields': ('min_amount', 'max_amount'),
            'description': 'Minimum and maximum transfer amounts allowed'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['source_country', 'destination_country']
    
    def corridor_arrow(self, obj):
        return format_html(
            '<strong style="font-size: 14px; color: #1976d2;">{}</strong> ➜ <strong style="font-size: 14px; color: #388e3c;">{}</strong>',
            obj.source_country.iso_code,
            obj.destination_country.iso_code
        )
    corridor_arrow.short_description = 'Route'
    corridor_arrow.admin_order_field = 'source_country'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: white; background-color: #4caf50; padding: 4px 10px; border-radius: 4px; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: white; background-color: #f44336; padding: 4px 10px; border-radius: 4px; font-weight: bold;">✕ Inactive</span>'
            )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def fee_display(self, obj):
        return format_html(
            '<span style="background-color: #fff3e0; color: #e65100; padding: 4px 8px; border-radius: 4px;"><strong>Fixed:</strong> {}<br><strong>%:</strong> {}%</span>',
            obj.fixed_fee,
            obj.percentage_fee
        )
    fee_display.short_description = 'Fees'
    
    def amount_limits(self, obj):
        return format_html(
            '<span style="background-color: #f3e5f5; color: #512da8; padding: 4px 8px; border-radius: 4px;"><strong>Min:</strong> {}<br><strong>Max:</strong> {}</span>',
            obj.min_amount,
            obj.max_amount
        )
    amount_limits.short_description = 'Limits'
    
    def source_methods_count(self, obj):
        count = obj.source_country.payment_methods.filter(
            is_active=True
        ).filter(
            Q(type_category='funding') | Q(type_category='both')
        ).count()
        return format_html(
            '<span style="background-color: #c8e6c9; color: #388e3c; padding: 4px 8px; border-radius: 4px; font-weight: bold;">💸 {}</span>',
            count
        )
    source_methods_count.short_description = 'Funding Methods'
    
    def destination_methods_count(self, obj):
        count = obj.destination_country.payment_methods.filter(
            is_active=True
        ).filter(
            Q(type_category='payout') | Q(type_category='both')
        ).count()
        return format_html(
            '<span style="background-color: #ffe0b2; color: #e65100; padding: 4px 8px; border-radius: 4px; font-weight: bold;">📥 {}</span>',
            count
        )
    destination_methods_count.short_description = 'Payout Methods'
    
    actions = ['activate_corridors', 'deactivate_corridors']
    
    def activate_corridors(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'✓ {updated} corridor(s) activated')
    activate_corridors.short_description = '✓ Activate selected corridors'
    
    def deactivate_corridors(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'✕ {updated} corridor(s) deactivated')
    deactivate_corridors.short_description = '✕ Deactivate selected corridors'
