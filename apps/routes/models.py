# apps/routes/models.py

from django.db import models


class Country(models.Model):
    """A country in the transfer network"""
    iso_code = models.CharField(max_length=2, unique=True)  # CM, CI, SN
    name = models.CharField(max_length=100)
    phone_prefix = models.CharField(max_length=5, help_text="+237, +225, etc.")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'routes_country'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.iso_code})"


class PaymentMethodType(models.TextChoices):
    MOBILE_MONEY = 'mobile_money', 'Mobile Money'
    CARD = 'card', 'Card'
    BANK = 'bank', 'Bank'


class MobileMoneyProvider(models.TextChoices):
    # Cameroon
    MTN_CM = 'mtn_cm', 'MTN Mobile Money (Cameroon)'
    ORANGE_CM = 'orange_cm', 'Orange Money (Cameroon)'
    
    # Côte d'Ivoire
    MTN_CI = 'mtn_ci', 'MTN Mobile Money (Côte d\'Ivoire)'
    ORANGE_CI = 'orange_ci', 'Orange Money (Côte d\'Ivoire)'
    MOOV_CI = 'moov_ci', 'Moov Money (Côte d\'Ivoire)'
    WAVE_CI = 'wave_ci', 'Wave (Côte d\'Ivoire)'
    
    # Senegal
    ORANGE_SN = 'orange_sn', 'Orange Money (Senegal)'
    FREE_SN = 'free_sn', 'Free Money (Senegal)'
    WAVE_SN = 'wave_sn', 'Wave (Senegal)'
    
    # Mali
    ORANGE_ML = 'orange_ml', 'Orange Money (Mali)'
    MOOV_ML = 'moov_ml', 'Moov Money (Mali)'
    
    # Burkina Faso
    ORANGE_BF = 'orange_bf', 'Orange Money (Burkina Faso)'
    MOOV_BF = 'moov_bf', 'Moov Money (Burkina Faso)'
    
    # Togo
    TOGOCOM_TG = 'togocom_tg', 'Togocom Money (Togo)'
    MOOV_TG = 'moov_tg', 'Moov Money (Togo)'
    
    # Benin
    MTN_BJ = 'mtn_bj', 'MTN Mobile Money (Benin)'
    MOOV_BJ = 'moov_bj', 'Moov Money (Benin)'


class PaymentMethodIcon:
    """Static class to manage payment method icons and colors"""
    
    ICON_BASE_URL = "http://10.238.85.58:8000/media/payment-icons/"
    
    ICONS = {
        'mtn_cm': 'mtn-logo.png',
        'mtn_ci': 'mtn-logo.png',
        'mtn_bj': 'mtn-logo.png',
        'orange_cm': 'orange-logo.png',
        'orange_ci': 'orange-logo.png',
        'orange_sn': 'orange-logo.png',
        'orange_ml': 'orange-logo.png',
        'orange_bf': 'orange-logo.png',
        'moov_ci': 'moov-money.png',
        'moov_ml': 'moov-money.png',
        'moov_bf': 'moov-money.png',
        'moov_tg': 'moov-money.png',
        'moov_bj': 'moov-money.png',
        'wave_ci': 'wave.png',
        'wave_sn': 'wave.png',
        'free_sn': 'free-money.png',
        'togocom_tg': 'togocom.png',
        'visa': 'visa.png',
        'mastercard': 'mastercard.png',
        'amex': 'amex.png',
        'bank': 'bank.png',
    }
    
    COLORS = {
        'mtn_cm': '#FFCC00',
        'mtn_ci': '#FFCC00',
        'mtn_bj': '#FFCC00',
        'orange_cm': '#FF6600',
        'orange_ci': '#FF6600',
        'orange_sn': '#FF6600',
        'orange_ml': '#FF6600',
        'orange_bf': '#FF6600',
        'moov_ci': '#0066CC',
        'moov_ml': '#0066CC',
        'moov_bf': '#0066CC',
        'moov_tg': '#0066CC',
        'moov_bj': '#0066CC',
        'wave_ci': '#FF1B7C',
        'wave_sn': '#FF1B7C',
        'free_sn': '#E2001A',
        'togocom_tg': '#00A651',
        'visa': '#1A1F71',
        'mastercard': '#EB001B',
        'amex': '#006FCF',
        'bank': '#333333',
    }
    
    @classmethod
    def get_icon_url(cls, provider_code):
        icon_filename = cls.ICONS.get(provider_code, 'default.png')
        return f"{cls.ICON_BASE_URL}{icon_filename}"
    
    @classmethod
    def get_color(cls, provider_code):
        return cls.COLORS.get(provider_code, '#666666')


class PaymentMethod(models.Model):
    """
    ✨ NEW: Payment methods are tied to COUNTRIES, not corridors
    
    Examples:
    - MTN CM (Cameroon)
    - Orange Money Senegal
    - MTN CI (Côte d'Ivoire)
    
    Can be used as funding (sender) or payout (receiver) based on corridor validation
    """
    
    TYPE_CHOICES = [
        ('funding', 'Funding Method (How sender pays)'),
        ('payout', 'Payout Method (How receiver gets money)'),
        ('both', 'Both funding and payout'),
    ]
    
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    type_category = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='both',
        help_text="Whether this method can be used for funding, payout, or both"
    )
    
    method_type = models.CharField(
        max_length=20,
        choices=PaymentMethodType.choices
    )
    
    # For mobile money
    mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
    )
    
    # For cards
    card_scheme = models.CharField(
        max_length=20,
        blank=True,
        help_text="visa, mastercard, amex"
    )
    
    # Configuration
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher = displayed first")
    
    class Meta:
        db_table = 'routes_payment_method'
        # Prevent duplicates
        unique_together = [
            ['country', 'method_type', 'mobile_provider', 'card_scheme']
        ]
        ordering = ['-priority', 'method_type', 'mobile_provider']
    
    def get_icon_url(self):
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return PaymentMethodIcon.get_icon_url(self.mobile_provider)
        elif self.method_type == PaymentMethodType.CARD:
            return PaymentMethodIcon.get_icon_url(self.card_scheme.lower())
        return PaymentMethodIcon.get_icon_url('bank')
    
    def get_brand_color(self):
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return PaymentMethodIcon.get_color(self.mobile_provider)
        elif self.method_type == PaymentMethodType.CARD:
            return PaymentMethodIcon.get_color(self.card_scheme.lower())
        return PaymentMethodIcon.get_color('bank')
    
    def get_display_name(self):
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return self.get_mobile_provider_display()
        elif self.method_type == PaymentMethodType.CARD:
            return f"{self.card_scheme.upper()} Card"
        return self.get_method_type_display()
    
    def __str__(self):
        return f"{self.country.iso_code} - {self.get_display_name()}"


class Corridor(models.Model):
    """
    ✨ REFACTORED: Now just represents a route + fee config
    No longer contains payment methods (those are on Country)
    """
    
    source_country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='outgoing_corridors'
    )
    destination_country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='incoming_corridors'
    )
    
    # Corridor-specific settings
    is_active = models.BooleanField(default=True)
    
    # Fee structure (can be corridor-specific)
    fixed_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Fixed fee in base currency"
    )
    percentage_fee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage fee (e.g., 1.50 for 1.5%)"
    )
    
    # Amount constraints
    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=100,
        help_text="Minimum transfer amount"
    )
    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=10000000,
        help_text="Maximum transfer amount"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'routes_corridor'
        unique_together = ('source_country', 'destination_country')
        ordering = ['source_country', 'destination_country']
    
    def __str__(self):
        return f"{self.source_country.iso_code} → {self.destination_country.iso_code}"
