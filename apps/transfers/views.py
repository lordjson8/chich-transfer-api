# apps/transfers/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework import status
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings
import uuid

from .models import Transfer, TransferLimitSnapshot, TransferAuditLog, TransferStatus
from .serializers import (
    CreateTransferSerializer,
    TransferSerializer,
    TransferHistorySerializer,
    TransferLimitSerializer,
)
from apps.integrations.awdpay import AwdPayClient
from apps.core.utils import get_client_ip  # you likely already have something like this
from decimal import Decimal

class TransferThrottle(UserRateThrottle):
    scope = 'transaction'  # matches your DRF throttle rates


class CreateTransferView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TransferThrottle]

    @db_transaction.atomic
    def post(self, request):
        serializer = CreateTransferSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = request.user
        snapshot: TransferLimitSnapshot = data['snapshot']

        reference = f"TRF-{uuid.uuid4().hex[:12].upper()}"

        transfer = Transfer.objects.create(
            user=user,
            amount=data['amount'],
            currency=data['currency'],
            recipient_name=data['recipient_name'],
            recipient_phone=data['recipient_phone'],
            recipient_email=data.get('recipient_email', ''),
            description=data.get('description', ''),
            service_fee=self._calc_fee(data['amount']),
            reference=reference,
            provider='awdpay',
        )
        transfer.total_amount = transfer.amount + transfer.service_fee
        transfer.save(update_fields=['total_amount'])

        TransferAuditLog.log(
            transfer,
            'created',
            metadata={
                'device_id': data['device_id'],
                'kyc_level': data['kyc_profile'].kyc_level,
            },
            ip=get_client_ip(request),
        )

        client = AwdPayClient()
        provider_res = client.create_transfer(
            reference=reference,
            amount=str(transfer.amount),
            currency=transfer.currency,
            recipient_phone=transfer.recipient_phone,
            recipient_name=transfer.recipient_name,
            description=transfer.description,
        )

        if not provider_res['success']:
            transfer.mark_failed(provider_res['error'], code='PROVIDER_ERROR')
            TransferAuditLog.log(
                transfer,
                'failed',
                metadata={'provider_error': provider_res['error']},
                ip=get_client_ip(request),
            )
            return Response(
                {
                    'success': False,
                    'error': provider_res['error'],
                    'error_code': 'TRANSFER_FAILED',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        transfer.status = TransferStatus.PROCESSING
        transfer.provider_id = provider_res['provider_id']
        transfer.save(update_fields=['status', 'provider_id'])

        snapshot.total_sent += transfer.amount
        snapshot.transfer_count += 1
        snapshot.daily_sent += transfer.amount
        snapshot.daily_count += 1
        snapshot.save()

        TransferAuditLog.log(
            transfer,
            'provider_init',
            metadata={'provider_id': transfer.provider_id},
            ip=get_client_ip(request),
        )

        out = TransferSerializer(transfer)
        return Response(
            {
                'success': True,
                'message': 'Transfer initiated successfully.',
                'data': out.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _calc_fee(self, amount, currency='XAF'):

        # fee_rate = Decimal('0.01')  # 1%
        # min_fee = Decimal('50')
        # max_fee = Decimal('500')
        
        # # Calculate fee
        # fee = amount * fee_rate
        
        # # Apply min/max bounds
        # if fee < min_fee:
        #     fee = min_fee
        # elif fee > max_fee:
        #     fee = max_fee
        
        # return fee

        amount = Decimal(str(amount))  # Ensure Decimal
        
        # Fee tiers
        if amount <= Decimal('10000'):
            return Decimal('50')
        
        elif amount <= Decimal('50000'):
            fee = amount * Decimal('0.01')  # 1%
            return max(Decimal('100'), min(fee, Decimal('500')))
        
        elif amount <= Decimal('200000'):
            fee = amount * Decimal('0.008')  # 0.8%
            return max(Decimal('500'), min(fee, Decimal('1500')))
        
        else:  # > 200,000
            fee = amount * Decimal('0.005')  # 0.5%
            return max(Decimal('1500'), min(fee, Decimal('5000')))
        

class TransferHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Transfer.objects.filter(user=request.user, deleted_at__isnull=True)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))

        total = qs.count()
        items = qs[offset:offset + limit]
        ser = TransferHistorySerializer(items, many=True)

        return Response(
            {
                'success': True,
                'data': ser.data,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total,
                },
            },
            status=status.HTTP_200_OK,
        )


class TransferDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            transfer = Transfer.objects.get(id=pk, user=request.user)
        except Transfer.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Transfer not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        ser = TransferSerializer(transfer)
        logs = transfer.audit_logs.values('event', 'metadata', 'created_at')
        return Response(
            {
                'success': True,
                'data': {
                    **ser.data,
                    'audit_logs': list(logs),
                },
            },
            status=status.HTTP_200_OK,
        )


class TransferLimitsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        snapshot = TransferLimitSnapshot.for_user(request.user)
        ser = TransferLimitSerializer(snapshot)
        return Response({'success': True, 'data': ser.data}, status=status.HTTP_200_OK)
