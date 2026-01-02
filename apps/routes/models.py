from django.db import models


class Country(models.Model):
    """A country that can be a source or destination."""
    iso_code = models.CharField(max_length=2, unique=True)  # CM, CI, SN
    name = models.CharField(max_length=100)
    phone_prefix = models.CharField(max_length=5, help_text="+237, +225, etc.")

    def __str__(self):
        return self.name


class PaymentMethodType(models.TextChoices):
    MOBILE_MONEY = 'mobile_money', 'Mobile Money'
    CARD = 'card', 'Card'
    BANK = 'bank', 'Bank'


class MobileMoneyProvider(models.TextChoices):
    MTN_CM = 'mtn_cm', 'MTN Cameroon'
    ORANGE_CM = 'orange_cm', 'Orange Money Cameroon'
    WAVE_SN = 'wave_sn', 'Wave Senegal'
    MTN_CI = 'mtn_ci', 'MTN Côte d’Ivoire'
    ORANGE_CI = 'orange_ci', 'Orange Money Côte d’Ivoire'
    # extend as needed


class Corridor(models.Model):
    """
    Represents a corridor from one country to another.
    Example: CM -> CI, CM -> SN
    """
    source_country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name='outgoing_corridors'
    )
    destination_country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name='incoming_corridors'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('source_country', 'destination_country')

    def __str__(self):
        return f"{self.source_country.iso_code} → {self.destination_country.iso_code}"


# class CorridorFundingMethod(models.Model):
#     """
#     Payment methods the SENDER can use in a given source country.
#     e.g. CM: MTN, Orange, Visa, Mastercard.
#     """
#     corridor = models.ForeignKey(
#         Corridor, on_delete=models.CASCADE, related_name='funding_methods'
#     )
#     method_type = models.CharField(
#         max_length=20, choices=PaymentMethodType.choices
#     )
#     mobile_provider = models.CharField(
#         max_length=50,
#         choices=MobileMoneyProvider.choices,
#         blank=True,
#     )
#     card_scheme = models.CharField(
#         max_length=20,
#         blank=True,
#         help_text="visa, mastercard, etc.",
#     )
#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         if self.method_type == PaymentMethodType.MOBILE_MONEY:
#             return f"{self.corridor.source_country.iso_code} {self.get_mobile_provider_display()}"
#         if self.method_type == PaymentMethodType.CARD:
#             return f"{self.corridor.source_country.iso_code} {self.card_scheme.upper()} card"
#         return f"{self.corridor.source_country.iso_code} {self.method_type}"


# class CorridorPayoutMethod(models.Model):
#     """
#     How the RECIPIENT can receive money in destination country.
#     e.g. CI: MTN CI wallet, ORANGE CI wallet, bank.
#     """
#     corridor = models.ForeignKey(
#         Corridor, on_delete=models.CASCADE, related_name='payout_methods'
#     )
#     method_type = models.CharField(
#         max_length=20, choices=PaymentMethodType.choices
#     )
#     mobile_provider = models.CharField(
#         max_length=50,
#         choices=MobileMoneyProvider.choices,
#         blank=True,
#     )
#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         if self.method_type == PaymentMethodType.MOBILE_MONEY:
#             return f"{self.corridor.destination_country.iso_code} {self.get_mobile_provider_display()}"
#         return f"{self.corridor.destination_country.iso_code} {self.method_type}"




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
    """Static class to manage payment method icons"""
    
    # Base URL for icons (can be CDN or local)
    ICON_BASE_URL = "https://your-cdn.com/payment-icons/"  # Change to your CDN
    
    # Icon mappings
    ICONS = {
        # Mobile Money Providers
        'mtn_cm': 'mtn-momo.png',
        'mtn_ci': 'mtn-momo.png',
        'mtn_bj': 'mtn-momo.png',
        
        'orange_cm': 'orange-money.png',
        'orange_ci': 'orange-money.png',
        'orange_sn': 'orange-money.png',
        'orange_ml': 'orange-money.png',
        'orange_bf': 'orange-money.png',
        
        'moov_ci': 'moov-money.png',
        'moov_ml': 'moov-money.png',
        'moov_bf': 'moov-money.png',
        'moov_tg': 'moov-money.png',
        'moov_bj': 'moov-money.png',
        
        'wave_ci': 'wave.png',
        'wave_sn': 'wave.png',
        
        'free_sn': 'free-money.png',
        'togocom_tg': 'togocom.png',
        
        # Cards
        'visa': 'visa.png',
        'mastercard': 'mastercard.png',
        'amex': 'amex.png',
        
        # Banks
        'bank': 'bank.png',
    }
    
    # Brand colors
    COLORS = {
        # MTN - Yellow
        'mtn_cm': '#FFCC00',
        'mtn_ci': '#FFCC00',
        'mtn_bj': '#FFCC00',
        
        # Orange - Orange
        'orange_cm': '#FF6600',
        'orange_ci': '#FF6600',
        'orange_sn': '#FF6600',
        'orange_ml': '#FF6600',
        'orange_bf': '#FF6600',
        
        # Moov - Blue
        'moov_ci': '#0066CC',
        'moov_ml': '#0066CC',
        'moov_bf': '#0066CC',
        'moov_tg': '#0066CC',
        'moov_bj': '#0066CC',
        
        # Wave - Purple/Pink
        'wave_ci': '#FF1B7C',
        'wave_sn': '#FF1B7C',
        
        # Free - Red
        'free_sn': '#E2001A',
        
        # Togocom - Green
        'togocom_tg': '#00A651',
        
        # Cards
        'visa': '#1A1F71',
        'mastercard': '#EB001B',
        'amex': '#006FCF',
        
        # Default
        'bank': '#333333',
    }
    
    @classmethod
    def get_icon_url(cls, provider_code):
        """Get full icon URL for a provider"""
        icon_filename = cls.ICONS.get(provider_code, 'default.png')
        return f"{cls.ICON_BASE_URL}{icon_filename}"
    
    @classmethod
    def get_color(cls, provider_code):
        """Get brand color for a provider"""
        return cls.COLORS.get(provider_code, '#666666')


class CorridorFundingMethod(models.Model):
    """Payment methods the SENDER can use"""
    
    corridor = models.ForeignKey(
        Corridor,
        on_delete=models.CASCADE,
        related_name='funding_methods'
    )
    method_type = models.CharField(
        max_length=20,
        choices=PaymentMethodType.choices
    )
    mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
    )
    card_scheme = models.CharField(
        max_length=20,
        blank=True,
        help_text="visa, mastercard, amex",
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [['corridor', 'method_type', 'mobile_provider', 'card_scheme']]
    
    def get_icon_url(self):
        """Get icon URL for this payment method"""
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return PaymentMethodIcon.get_icon_url(self.mobile_provider)
        elif self.method_type == PaymentMethodType.CARD:
            return PaymentMethodIcon.get_icon_url(self.card_scheme.lower())
        return PaymentMethodIcon.get_icon_url('bank')
    
    def get_brand_color(self):
        """Get brand color for this payment method"""
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return PaymentMethodIcon.get_color(self.mobile_provider)
        elif self.method_type == PaymentMethodType.CARD:
            return PaymentMethodIcon.get_color(self.card_scheme.lower())
        return PaymentMethodIcon.get_color('bank')
    
    def __str__(self):
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return f"{self.corridor.source_country.iso_code} {self.get_mobile_provider_display()}"
        if self.method_type == PaymentMethodType.CARD:
            return f"{self.corridor.source_country.iso_code} {self.card_scheme.upper()} card"
        return f"{self.corridor.source_country.iso_code} {self.method_type}"


class CorridorPayoutMethod(models.Model):
    """How the RECIPIENT receives money"""
    
    corridor = models.ForeignKey(
        Corridor,
        on_delete=models.CASCADE,
        related_name='payout_methods'
    )
    method_type = models.CharField(
        max_length=20,
        choices=PaymentMethodType.choices
    )
    mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [['corridor', 'method_type', 'mobile_provider']]
    
    def get_icon_url(self):
        """Get icon URL for this payment method"""
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return PaymentMethodIcon.get_icon_url(self.mobile_provider)
        return PaymentMethodIcon.get_icon_url('bank')
    
    def get_brand_color(self):
        """Get brand color for this payment method"""
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return PaymentMethodIcon.get_color(self.mobile_provider)
        return PaymentMethodIcon.get_color('bank')
    
    def __str__(self):
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return f"{self.corridor.destination_country.iso_code} {self.get_mobile_provider_display()}"
        return f"{self.corridor.destination_country.iso_code} {self.method_type}"
