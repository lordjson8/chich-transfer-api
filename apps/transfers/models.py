# apps/transfers/models.py

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models import Sum, Q
import uuid
from apps.routes.models import Corridor, PaymentMethodType, MobileMoneyProvider

from apps.authentication.models import User
from apps.kyc.models import KYCProfile, KYCLevel
from apps.core.models import TimeStampedModel, SoftDeleteModel


class TransferStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    DEPOSIT_PENDING = 'deposit_pending', 'Deposit Pending'
    DEPOSIT_CONFIRMED = 'deposit_confirmed', 'Deposit Confirmed'
    DEPOSIT_FAILED = 'deposit_failed', 'Deposit Failed'
    WITHDRAWAL_PENDING = 'withdrawal_pending', 'Withdrawal Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    REVERSED = 'reversed', 'Reversed'


class Currency(models.TextChoices):
    XAF = 'XAF', 'Central African Franc'
    XOF = 'XOF', 'West African Franc'
    USD = 'USD', 'US Dollar'
    EUR = 'EUR', 'Euro'
    GBP = 'GBP', 'British Pound'



class Transfer(TimeStampedModel, SoftDeleteModel):
    """
    Two-phase money transfer: deposit (collect from sender) then withdrawal (payout to receiver).
    Uses AWDPay as the payment provider.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='transfers',
    )

    status = models.CharField(
        max_length=25,
        choices=TransferStatus.choices,
        default=TransferStatus.PENDING,
        db_index=True,
    )

    # --- Sender info ---
    sender_phone = models.CharField(max_length=20, blank=True, db_index=True)
    sender_name = models.CharField(max_length=255, blank=True)
    sender_email = models.EmailField(blank=True)

    # --- Funding & payout providers ---
    funding_mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
        help_text="Sender's mobile money provider (e.g. mtn_cm).",
    )
    payout_mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
        help_text="Receiver's mobile money provider (e.g. wave_ci).",
    )

    # --- Corridor ---
    corridor = models.ForeignKey(
        Corridor,
        on_delete=models.PROTECT,
        related_name='corridor_transfers',
        null=True,
        blank=True,
        help_text="Source -> destination corridor used for this transfer.",
    )

    # --- Source amount (what the sender pays) ---
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(100)],  # 100 XAF min
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.XAF,
    )

    # --- Destination amount (what the receiver gets) ---
    destination_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount the receiver gets in destination currency.",
    )
    destination_currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        blank=True,
        help_text="Currency the receiver gets (e.g. XOF).",
    )

    service_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="amount + service_fee",
    )

    # --- Recipient info ---
    recipient_name = models.CharField(max_length=255)
    recipient_phone = models.CharField(max_length=20, db_index=True)
    recipient_email = models.EmailField(blank=True)

    # --- External provider metadata ---
    provider = models.CharField(max_length=50, default='awdpay')
    reference = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Internal reference used with provider.",
    )
    provider_id = models.CharField(
        max_length=128,
        blank=True,
        db_index=True,
        help_text="ID returned by provider (AwdPay).",
    )

    # --- AWDPay Deposit (phase 1: collect from sender) ---
    deposit_reference = models.CharField(max_length=128, blank=True, db_index=True)
    deposit_status = models.CharField(max_length=50, blank=True)
    deposit_gateway = models.CharField(max_length=50, blank=True)
    deposit_initiated_at = models.DateTimeField(null=True, blank=True)
    deposit_confirmed_at = models.DateTimeField(null=True, blank=True)

    # --- AWDPay Withdrawal (phase 2: payout to receiver) ---
    withdrawal_reference = models.CharField(max_length=128, blank=True, db_index=True)
    withdrawal_status = models.CharField(max_length=50, blank=True)
    withdrawal_gateway = models.CharField(max_length=50, blank=True)
    withdrawal_initiated_at = models.DateTimeField(null=True, blank=True)
    withdrawal_confirmed_at = models.DateTimeField(null=True, blank=True)

    description = models.TextField(blank=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reference']),
            models.Index(fields=['provider_id']),
            models.Index(fields=['deposit_reference']),
            models.Index(fields=['withdrawal_reference']),
        ]

    def save(self, *args, **kwargs):
        if not self.total_amount:
            self.total_amount = (self.amount or 0) + (self.service_fee or 0)
        super().save(*args, **kwargs)

    # --- State machine helpers ---

    def mark_deposit_pending(self, deposit_ref: str, gateway: str):
        self.status = TransferStatus.DEPOSIT_PENDING
        self.deposit_reference = deposit_ref
        self.deposit_gateway = gateway
        self.deposit_status = 'pending'
        self.deposit_initiated_at = timezone.now()
        self.save(update_fields=[
            'status', 'deposit_reference', 'deposit_gateway',
            'deposit_status', 'deposit_initiated_at', 'updated_at',
        ])

    def mark_deposit_confirmed(self):
        self.status = TransferStatus.DEPOSIT_CONFIRMED
        self.deposit_status = 'completed'
        self.deposit_confirmed_at = timezone.now()
        self.save(update_fields=[
            'status', 'deposit_status', 'deposit_confirmed_at', 'updated_at',
        ])

    def mark_deposit_failed(self, message: str = '', code: str = ''):
        self.status = TransferStatus.DEPOSIT_FAILED
        self.deposit_status = 'failed'
        self.error_message = message
        self.error_code = code
        self.save(update_fields=[
            'status', 'deposit_status', 'error_message', 'error_code', 'updated_at',
        ])

    def mark_withdrawal_pending(self, withdrawal_ref: str, gateway: str):
        self.status = TransferStatus.WITHDRAWAL_PENDING
        self.withdrawal_reference = withdrawal_ref
        self.withdrawal_gateway = gateway
        self.withdrawal_status = 'pending'
        self.withdrawal_initiated_at = timezone.now()
        self.save(update_fields=[
            'status', 'withdrawal_reference', 'withdrawal_gateway',
            'withdrawal_status', 'withdrawal_initiated_at', 'updated_at',
        ])

    def mark_completed(self):
        self.status = TransferStatus.COMPLETED
        self.withdrawal_status = 'completed'
        self.withdrawal_confirmed_at = timezone.now()
        self.completed_at = timezone.now()
        self.save(update_fields=[
            'status', 'withdrawal_status', 'withdrawal_confirmed_at',
            'completed_at', 'updated_at',
        ])

    def mark_failed(self, message: str, code: str | None = None):
        self.status = TransferStatus.FAILED
        self.error_message = message
        if code:
            self.error_code = code
        self.save(update_fields=['status', 'error_message', 'error_code', 'updated_at'])

    def __str__(self):
        return f"{self.user.email} -> {self.recipient_phone} ({self.amount} {self.currency})"


class TransferLimitSnapshot(models.Model):
    """
    Aggregate usage for a user for the current day/month,
    used to enforce KYC-based limits.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='transfer_limits',
    )

    period_start = models.DateField()
    period_end = models.DateField()

    total_sent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transfer_count = models.IntegerField(default=0)

    daily_date = models.DateField()
    daily_sent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    daily_count = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    corridor = models.ForeignKey(
        Corridor,
        on_delete=models.PROTECT,
        related_name='limit_snapshots',
        null=True,
        blank=True,
        help_text="Source → destination corridor used for this transfer.",
    )

    funding_method_type = models.CharField(
        max_length=20,
        choices=PaymentMethodType.choices,
        help_text="How sender pays: mobile money, card, etc.",
    )
    funding_mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
    )
    funding_card_scheme = models.CharField(
        max_length=20,
        blank=True,
    )

    payout_method_type = models.CharField(
        max_length=20,
        choices=PaymentMethodType.choices,
        help_text="How recipient receives: mobile money, bank, etc.",
    )
    payout_mobile_provider = models.CharField(
        max_length=50,
        choices=MobileMoneyProvider.choices,
        blank=True,
    )

    class Meta:
        verbose_name = "Transfer Limit Snapshot"
        verbose_name_plural = "Transfer Limit Snapshots"

    @classmethod
    def for_user(cls, user: User) -> "TransferLimitSnapshot":
        """Return a snapshot for today/month, resetting windows if necessary."""
        today = timezone.now().date()
        from datetime import date, timedelta

        month_start = date(today.year, today.month, 1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)

        obj, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'period_start': month_start,
                'period_end': month_end,
                'daily_date': today,
            },
        )

        # reset month window
        if obj.period_start != month_start:
            obj.period_start = month_start
            obj.period_end = month_end
            obj.total_sent = 0
            obj.transfer_count = 0

        # reset day window
        if obj.daily_date != today:
            obj.daily_date = today
            obj.daily_sent = 0
            obj.daily_count = 0

        if created or obj.period_start != month_start or obj.daily_date != today:
            obj.save()

        return obj

    def remaining_limits(self, kyc_profile: KYCProfile) -> dict:
        """
        Return remaining limits based on KYC level:
        - per_transaction
        - daily
        - monthly
        """
        limits = kyc_profile.get_transaction_limit()

        monthly_used = self.total_sent
        daily_used = self.daily_sent

        return {
            'per_transaction_limit': limits['transaction_limit'],
            'daily': {
                'limit': limits['daily_limit'],
                'used': monthly_used if False else daily_used,  # daily_used
                'remaining': limits['daily_limit'] - daily_used,
            },
            'monthly': {
                'limit': limits['monthly_limit'],
                'used': monthly_used,
                'remaining': limits['monthly_limit'] - monthly_used,
            },
        }


class TransferAuditLog(models.Model):
    """Low-level audit events for a transfer."""

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name='audit_logs',
    )
    event = models.CharField(
        max_length=50,
        choices=[
            ('created', 'Created'),
            ('provider_init', 'Provider Initiated'),
            ('deposit_initiated', 'Deposit Initiated'),
            ('deposit_confirmed', 'Deposit Confirmed'),
            ('deposit_failed', 'Deposit Failed'),
            ('withdrawal_initiated', 'Withdrawal Initiated'),
            ('withdrawal_confirmed', 'Withdrawal Confirmed'),
            ('withdrawal_failed', 'Withdrawal Failed'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('webhook_received', 'Webhook Received'),
            ('webhook_processed', 'Webhook Processed'),
        ],
    )
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def log(cls, transfer: Transfer, event: str, metadata=None, ip=None):
        return cls.objects.create(
            transfer=transfer,
            event=event,
            metadata=metadata or {},
            ip_address=ip,
        )
