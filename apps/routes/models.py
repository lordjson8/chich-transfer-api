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


class CorridorFundingMethod(models.Model):
    """
    Payment methods the SENDER can use in a given source country.
    e.g. CM: MTN, Orange, Visa, Mastercard.
    """
    corridor = models.ForeignKey(
        Corridor, on_delete=models.CASCADE, related_name='funding_methods'
    )
    method_type = models.CharField(
        max_length=20, choices=PaymentMethodType.choices
    )
    mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
    )
    card_scheme = models.CharField(
        max_length=20,
        blank=True,
        help_text="visa, mastercard, etc.",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return f"{self.corridor.source_country.iso_code} {self.get_mobile_provider_display()}"
        if self.method_type == PaymentMethodType.CARD:
            return f"{self.corridor.source_country.iso_code} {self.card_scheme.upper()} card"
        return f"{self.corridor.source_country.iso_code} {self.method_type}"


class CorridorPayoutMethod(models.Model):
    """
    How the RECIPIENT can receive money in destination country.
    e.g. CI: MTN CI wallet, ORANGE CI wallet, bank.
    """
    corridor = models.ForeignKey(
        Corridor, on_delete=models.CASCADE, related_name='payout_methods'
    )
    method_type = models.CharField(
        max_length=20, choices=PaymentMethodType.choices
    )
    mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.method_type == PaymentMethodType.MOBILE_MONEY:
            return f"{self.corridor.destination_country.iso_code} {self.get_mobile_provider_display()}"
        return f"{self.corridor.destination_country.iso_code} {self.method_type}"
