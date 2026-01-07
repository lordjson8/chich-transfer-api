# apps/routes/serializers.py

from rest_framework import serializers
from .models import Country, PaymentMethod, Corridor


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['iso_code', 'name', 'phone_prefix', 'is_active']


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serialize payment methods with icons and colors"""
    
    method_type_display = serializers.CharField(
        source='get_method_type_display',
        read_only=True
    )
    mobile_provider_display = serializers.CharField(
        source='get_mobile_provider_display',
        read_only=True
    )
    type_category_display = serializers.CharField(
        source='get_type_category_display',
        read_only=True
    )
    display_name = serializers.CharField(
        source='get_display_name',
        read_only=True
    )
    icon_url = serializers.SerializerMethodField()
    brand_color = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id',
            'country',
            'type_category',
            'type_category_display',
            'method_type',
            'method_type_display',
            'mobile_provider',
            'mobile_provider_display',
            'card_scheme',
            'display_name',
            'icon_url',
            'brand_color',
            'priority',
            'is_active',
        ]
    
    def get_icon_url(self, obj):
        return obj.get_icon_url()
    
    def get_brand_color(self, obj):
        return obj.get_brand_color()


class CountryWithPaymentMethodsSerializer(serializers.ModelSerializer):
    """Country with its available payment methods"""
    
    payment_methods = PaymentMethodSerializer(many=True, read_only=True)
    
    class Meta:
        model = Country
        fields = [
            'iso_code',
            'name',
            'phone_prefix',
            'is_active',
            'payment_methods',
        ]


class CorridorSerializer(serializers.ModelSerializer):
    """Serialize corridor route with fee info"""
    
    source_country = CountrySerializer(read_only=True)
    destination_country = CountrySerializer(read_only=True)
    
    class Meta:
        model = Corridor
        fields = [
            'id',
            'source_country',
            'destination_country',
            'is_active',
            'fixed_fee',
            'percentage_fee',
            'min_amount',
            'max_amount',
            'created_at',
            'updated_at',
        ]


class CorridorListSerializer(serializers.ModelSerializer):
    """Lightweight corridor list"""
    
    source_country_code = serializers.CharField(
        source='source_country.iso_code',
        read_only=True
    )
    source_country_name = serializers.CharField(
        source='source_country.name',
        read_only=True
    )
    destination_country_code = serializers.CharField(
        source='destination_country.iso_code',
        read_only=True
    )
    destination_country_name = serializers.CharField(
        source='destination_country.name',
        read_only=True
    )
    
    class Meta:
        model = Corridor
        fields = [
            'id',
            'source_country_code',
            'source_country_name',
            'destination_country_code',
            'destination_country_name',
            'is_active',
        ]


class TransferFlowSerializer(serializers.Serializer):
    """
    ✨ NEW: Complete transfer flow response
    Shows:
    1. Funding methods for source country
    2. Payout methods for destination country
    3. Corridor info (fees, limits)
    """
    
    source_country = CountrySerializer()
    destination_country = CountrySerializer()
    
    funding_methods = PaymentMethodSerializer(many=True)
    payout_methods = PaymentMethodSerializer(many=True)
    
    corridor = CorridorSerializer()
    
    available = serializers.BooleanField()
    message = serializers.CharField(required=False)
