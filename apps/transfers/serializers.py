# apps/transfers/serializers.py

from rest_framework import serializers
from django.utils import timezone

from .models import Transfer, TransferLimitSnapshot, Currency
from apps.kyc.models import KYCProfile


class CreateTransferSerializer(serializers.Serializer):
    recipient_name = serializers.CharField(max_length=255)
    recipient_phone = serializers.CharField(max_length=20)
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=100)
    currency = serializers.ChoiceField(choices=Currency.choices, default=Currency.XAF)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    device_id = serializers.CharField(max_length=255)

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        amount = attrs['amount']

        # Require KYC profile
        try:
            kyc_profile = user.kyc_profile
        except KYCProfile.DoesNotExist:
            raise serializers.ValidationError("Complete your KYC profile to send money.")

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

        attrs['kyc_profile'] = kyc_profile
        attrs['snapshot'] = snapshot
        attrs['limits'] = limits
        return attrs


class TransferSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transfer
        fields = [
            'id',
            'status',
            'status_display',
            'amount',
            'currency',
            'service_fee',
            'total_amount',
            'recipient_name',
            'recipient_phone',
            'recipient_email',
            'reference',
            'provider',
            'provider_id',
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
