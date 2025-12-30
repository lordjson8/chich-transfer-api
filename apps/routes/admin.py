# apps/routes/admin.py

from django.contrib import admin
from .models import Country, Corridor, CorridorFundingMethod, CorridorPayoutMethod


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['iso_code', 'name', 'phone_prefix']
    search_fields = ['name', 'iso_code']
    ordering = ['name']


@admin.register(Corridor)
class CorridorAdmin(admin.ModelAdmin):
    list_display = [
        'source_country',
        'destination_country',
        'is_active',
        'funding_methods_count',
        'payout_methods_count',
    ]
    list_filter = ['is_active', 'source_country', 'destination_country']
    search_fields = [
        'source_country__name',
        'destination_country__name',
    ]
    ordering = ['source_country', 'destination_country']
    
    def funding_methods_count(self, obj):
        return obj.funding_methods.filter(is_active=True).count()
    funding_methods_count.short_description = 'Funding Methods'
    
    def payout_methods_count(self, obj):
        return obj.payout_methods.filter(is_active=True).count()
    payout_methods_count.short_description = 'Payout Methods'


@admin.register(CorridorFundingMethod)
class CorridorFundingMethodAdmin(admin.ModelAdmin):
    list_display = [
        'corridor',
        'method_type',
        'mobile_provider',
        'card_scheme',
        'is_active',
    ]
    list_filter = ['method_type', 'is_active', 'corridor__source_country']
    search_fields = [
        'corridor__source_country__name',
        'mobile_provider',
        'card_scheme',
    ]
    ordering = ['corridor', 'method_type']


@admin.register(CorridorPayoutMethod)
class CorridorPayoutMethodAdmin(admin.ModelAdmin):
    list_display = [
        'corridor',
        'method_type',
        'mobile_provider',
        'is_active',
    ]
    list_filter = ['method_type', 'is_active', 'corridor__destination_country']
    search_fields = [
        'corridor__destination_country__name',
        'mobile_provider',
    ]
    ordering = ['corridor', 'method_type']
