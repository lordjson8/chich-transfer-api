# apps/transfers/serializers.py

from decimal import Decimal

from rest_framework import serializers
from django.utils import timezone

from .models import Transfer, TransferLimitSnapshot, Currency
from apps.kyc.models import KYCProfile
from apps.routes.models import Corridor, MobileMoneyProvider
from apps.integrations.gateway_mapping import get_gateway_info


class CreateTransferSerializer(serializers.Serializer):
    # Sender info
    sender_phone = serializers.CharField(max_length=20)
    sender_name = serializers.CharField(max_length=255)

    # Recipient info
    recipient_name = serializers.CharField(max_length=255)
    recipient_phone = serializers.CharField(max_length=20)
    recipient_email = serializers.EmailField(required=False, allow_blank=True)

    # Transfer details
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=100)
    currency = serializers.ChoiceField(choices=Currency.choices, default=Currency.XAF)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    # Providers
    funding_provider = serializers.ChoiceField(choices=MobileMoneyProvider.choices)
    payout_provider = serializers.ChoiceField(choices=MobileMoneyProvider.choices)

    device_id = serializers.CharField(max_length=255)

    def validate_funding_provider(self, value):
        info = get_gateway_info(value)
        if not info:
            raise serializers.ValidationError(f"Unsupported funding provider: {value}")
        return value

    def validate_payout_provider(self, value):
        info = get_gateway_info(value)
        if not info:
            raise serializers.ValidationError(f"Unsupported payout provider: {value}")
        return value

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        amount = attrs['amount']

        # Require KYC profile
        try:
            kyc_profile = user.kyc_profile
        except KYCProfile.DoesNotExist:
            raise serializers.ValidationError("Complete your KYC profile to send money.")

        # Resolve gateway info for both providers
        funding_info = get_gateway_info(attrs['funding_provider'])
        payout_info = get_gateway_info(attrs['payout_provider'])

        # Look up corridor from source country -> destination country
        try:
            corridor = Corridor.objects.get(
                source_country__iso_code=funding_info['country'],
                destination_country__iso_code=payout_info['country'],
                is_active=True,
            )
        except Corridor.DoesNotExist:
            raise serializers.ValidationError(
                f"No active corridor from {funding_info['country']} to {payout_info['country']}."
            )

        # Corridor amount constraints
        if amount < corridor.min_amount:
            raise serializers.ValidationError({
                'amount': f"Minimum amount for this corridor is {corridor.min_amount}."
            })
        if amount > corridor.max_amount:
            raise serializers.ValidationError({
                'amount': f"Maximum amount for this corridor is {corridor.max_amount}."
            })

        # Get limits based on KYC
        limits = kyc_profile.get_transaction_limit()
        snapshot = TransferLimitSnapshot.for_user(user)

        # Per transaction
        if amount > limits['transaction_limit']:
            raise serializers.ValidationError({
                'amount': f"Max per transaction for your KYC level is {limits['transaction_limit']} {attrs['currency']}."
            })

        # Daily
        if snapshot.daily_sent + amount > limits['daily_limit']:
            remaining = max(limits['daily_limit'] - snapshot.daily_sent, 0)
            raise serializers.ValidationError({
                'amount': f"Daily limit exceeded. Remaining today: {remaining} {attrs['currency']}."
            })

        # Monthly
        if snapshot.total_sent + amount > limits['monthly_limit']:
            remaining = max(limits['monthly_limit'] - snapshot.total_sent, 0)
            raise serializers.ValidationError({
                'amount': f"Monthly limit exceeded. Remaining this month: {remaining} {attrs['currency']}."
            })

        # Compute corridor-based fee
        fee = corridor.fixed_fee + (amount * corridor.percentage_fee / Decimal('100'))

        attrs['kyc_profile'] = kyc_profile
        attrs['snapshot'] = snapshot
        attrs['limits'] = limits
        attrs['corridor'] = corridor
        attrs['service_fee'] = fee.quantize(Decimal('0.01'))
        attrs['funding_info'] = funding_info
        attrs['payout_info'] = payout_info
        return attrs


class TransferSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transfer
        fields = [
            'id',
            'status',
            'status_display',
            # Sender
            'sender_phone',
            'sender_name',
            'sender_email',
            'funding_mobile_provider',
            # Source amount
            'amount',
            'currency',
            'service_fee',
            'total_amount',
            # Destination amount
            'destination_amount',
            'destination_currency',
            # Payout
            'payout_mobile_provider',
            # Recipient
            'recipient_name',
            'recipient_phone',
            'recipient_email',
            # Reference
            'reference',
            'provider',
            'provider_id',
            # Deposit phase
            'deposit_reference',
            'deposit_status',
            'deposit_gateway',
            'deposit_initiated_at',
            'deposit_confirmed_at',
            # Withdrawal phase
            'withdrawal_reference',
            'withdrawal_status',
            'withdrawal_gateway',
            'withdrawal_initiated_at',
            'withdrawal_confirmed_at',
            # Other
            'description',
            'created_at',
            'completed_at',
            'error_code',
            'error_message',
        ]
        read_only_fields = fields


class TransferHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transfer
        fields = [
            'id',
            'status',
            'status_display',
            'amount',
            'currency',
            'destination_amount',
            'destination_currency',
            'funding_mobile_provider',
            'payout_mobile_provider',
            'sender_phone',
            'recipient_name',
            'recipient_phone',
            'created_at',
        ]


class TransferLimitSerializer(serializers.ModelSerializer):
    remaining_limits = serializers.SerializerMethodField()
    kyc_level = serializers.SerializerMethodField()
    kyc_verified = serializers.SerializerMethodField()

    class Meta:
        model = TransferLimitSnapshot
        fields = [
            'kyc_level',
            'kyc_verified',
            'total_sent',
            'transfer_count',
            'daily_sent',
            'daily_count',
            'remaining_limits',
        ]

    def get_kyc_level(self, obj):
        try:
            return obj.user.kyc_profile.get_kyc_level_display()
        except KYCProfile.DoesNotExist:
            return 'Basic'

    def get_kyc_verified(self, obj):
        try:
            return obj.user.kyc_profile.is_verified()
        except KYCProfile.DoesNotExist:
            return False

    def get_remaining_limits(self, obj):
        try:
            kyc_profile = obj.user.kyc_profile
        except KYCProfile.DoesNotExist:
            return {}
        return obj.remaining_limits(kyc_profile)
