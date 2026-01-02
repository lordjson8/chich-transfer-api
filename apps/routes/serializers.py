# apps/routes/serializers.py

from rest_framework import serializers

from rest_framework import serializers
from .models import (
    Country,
    Corridor,
    CorridorFundingMethod,
    CorridorPayoutMethod,
    PaymentMethodIcon,
)


class FundingMethodSerializer(serializers.ModelSerializer):
    """Serialize funding methods with icons"""
    
    method_type_display = serializers.CharField(
        source='get_method_type_display',
        read_only=True
    )
    mobile_provider_display = serializers.CharField(
        source='get_mobile_provider_display',
        read_only=True
    )
    icon_url = serializers.SerializerMethodField()
    brand_color = serializers.SerializerMethodField()
    
    class Meta:
        model = CorridorFundingMethod
        fields = [
            'id',
            'method_type',
            'method_type_display',
            'mobile_provider',
            'mobile_provider_display',
            'card_scheme',
            'icon_url',
            'brand_color',
            'is_active',
        ]
    
    def get_icon_url(self, obj):
        return obj.get_icon_url()
    
    def get_brand_color(self, obj):
        return obj.get_brand_color()


class PayoutMethodSerializer(serializers.ModelSerializer):
    """Serialize payout methods with icons"""
    
    method_type_display = serializers.CharField(
        source='get_method_type_display',
        read_only=True
    )
    mobile_provider_display = serializers.CharField(
        source='get_mobile_provider_display',
        read_only=True
    )
    icon_url = serializers.SerializerMethodField()
    brand_color = serializers.SerializerMethodField()
    
    class Meta:
        model = CorridorPayoutMethod
        fields = [
            'id',
            'method_type',
            'method_type_display',
            'mobile_provider',
            'mobile_provider_display',
            'icon_url',
            'brand_color',
            'is_active',
        ]
    
    def get_icon_url(self, obj):
        return obj.get_icon_url()
    
    def get_brand_color(self, obj):
        return obj.get_brand_color()


class CountrySerializer(serializers.ModelSerializer):
    """Serialize country data"""
    
    class Meta:
        model = Country
        fields = ['iso_code', 'name', 'phone_prefix']


# class FundingMethodSerializer(serializers.ModelSerializer):
#     """Serialize funding methods"""
    
#     method_type_display = serializers.CharField(
#         source='get_method_type_display',
#         read_only=True
#     )
#     mobile_provider_display = serializers.CharField(
#         source='get_mobile_provider_display',
#         read_only=True
#     )
    
#     class Meta:
#         model = CorridorFundingMethod
#         fields = [
#             'id',
#             'method_type',
#             'method_type_display',
#             'mobile_provider',
#             'mobile_provider_display',
#             'card_scheme',
#             'is_active',
#         ]


# class PayoutMethodSerializer(serializers.ModelSerializer):
#     """Serialize payout methods"""
    
#     method_type_display = serializers.CharField(
#         source='get_method_type_display',
#         read_only=True
#     )
#     mobile_provider_display = serializers.CharField(
#         source='get_mobile_provider_display',
#         read_only=True
#     )
    
#     class Meta:
#         model = CorridorPayoutMethod
#         fields = [
#             'id',
#             'method_type',
#             'method_type_display',
#             'mobile_provider',
#             'mobile_provider_display',
#             'is_active',
#         ]


class CorridorSerializer(serializers.ModelSerializer):
    """Serialize corridor with payment methods"""
    
    source_country = CountrySerializer(read_only=True)
    destination_country = CountrySerializer(read_only=True)
    funding_methods = FundingMethodSerializer(many=True, read_only=True)
    payout_methods = PayoutMethodSerializer(many=True, read_only=True)
    
    class Meta:
        model = Corridor
        fields = [
            'id',
            'source_country',
            'destination_country',
            'is_active',
            'funding_methods',
            'payout_methods',
        ]


class CorridorListSerializer(serializers.ModelSerializer):
    """Lightweight corridor list without nested methods"""
    
    source_country_code = serializers.CharField(source='source_country.iso_code', read_only=True)
    source_country_name = serializers.CharField(source='source_country.name', read_only=True)
    destination_country_code = serializers.CharField(source='destination_country.iso_code', read_only=True)
    destination_country_name = serializers.CharField(source='destination_country.name', read_only=True)
    destination_country_flag = serializers.SerializerMethodField()
    
    class Meta:
        model = Corridor
        fields = [
            'id',
            'source_country_code',
            'source_country_name',
            'destination_country_code',
            'destination_country_name',
            'destination_country_flag',
            'is_active',
        ]
    
    def get_destination_country_flag(self, obj):
        """Return emoji flag for destination country"""
        flags = {
            'CM': '🇨🇲',
            'CI': '🇨🇮',
            'SN': '🇸🇳',
            'ML': '🇲🇱',
            'BF': '🇧🇫',
            'TG': '🇹🇬',
            'BJ': '🇧🇯',
            'NE': '🇳🇪',
        }
        return flags.get(obj.destination_country.iso_code, '🌍')
