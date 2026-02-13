# apps/transfers/views.py

import logging
import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework import status
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import Transfer, TransferLimitSnapshot, TransferAuditLog, TransferStatus
from .serializers import (
    CreateTransferSerializer,
    TransferSerializer,
    TransferHistorySerializer,
    TransferLimitSerializer,
)
from apps.integrations.awdpay import AwdPayClient, AWDPayAPIError, AWDPayTokenError
from apps.core.utils import get_client_ip

logger = logging.getLogger(__name__)


class TransferThrottle(UserRateThrottle):
    scope = 'transaction'


class CreateTransferView(APIView):
    permission_classes = [IsAuthenticated]

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
        corridor = data['corridor']
        funding_info = data['funding_info']
        payout_info = data['payout_info']

        reference = f"TRF-{uuid.uuid4().hex[:12].upper()}"

        transfer = Transfer.objects.create(
            user=user,
            # Sender
            sender_phone=data['sender_phone'],
            sender_name=data['sender_name'],
            sender_email=user.email,
            funding_mobile_provider=data['funding_provider'],
            # Recipient
            recipient_name=data['recipient_name'],
            recipient_phone=data['recipient_phone'],
            recipient_email=data.get('recipient_email', ''),
            # Payout
            payout_mobile_provider=data['payout_provider'],
            # Corridor
            corridor=corridor,
            # Source amount
            amount=data['amount'],
            currency=data['currency'],
            service_fee=data['service_fee'],
            # Destination (same amount for now; exchange logic can be added later)
            destination_amount=data['amount'],
            destination_currency=payout_info['currency'],
            # Meta
            description=data.get('description', ''),
            reference=reference,
            provider='awdpay',
            # Gateways (store for reference)
            deposit_gateway=funding_info['gateway'],
            withdrawal_gateway=payout_info['gateway'],
        )
        transfer.total_amount = transfer.amount + transfer.service_fee
        transfer.save(update_fields=['total_amount'])

        TransferAuditLog.log(
            transfer,
            'created',
            metadata={
                'device_id': data['device_id'],
                'kyc_level': data['kyc_profile'].kyc_level,
                'funding_provider': data['funding_provider'],
                'payout_provider': data['payout_provider'],
            },
            ip=get_client_ip(request),
        )

        # Initiate deposit (phase 1: collect from sender)
        client = AwdPayClient()
        try:
            deposit_res = client.initiate_deposit(
                amount=str(transfer.total_amount),
                currency=funding_info['currency'],
                gateway=funding_info['gateway'],
                phone=transfer.sender_phone,
                country=funding_info['country'],
                reference=reference,
                description=transfer.description or f"Transfer {reference}",
            )
        except (AWDPayAPIError, AWDPayTokenError) as exc:
            transfer.mark_failed(str(exc), code='DEPOSIT_INIT_ERROR')
            TransferAuditLog.log(
                transfer, 'failed',
                metadata={'error': str(exc)},
                ip=get_client_ip(request),
            )
            return Response(
                {
                    'success': False,
                    'error': str(exc),
                    'error_code': 'DEPOSIT_INIT_ERROR',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark deposit pending
        deposit_ref = deposit_res.get('depositRef', deposit_res.get('ref', reference))
        transfer.mark_deposit_pending(deposit_ref, funding_info['gateway'])

        # Update user limits
        snapshot.total_sent += transfer.amount
        snapshot.transfer_count += 1
        snapshot.daily_sent += transfer.amount
        snapshot.daily_count += 1
        snapshot.save()

        TransferAuditLog.log(
            transfer, 'deposit_initiated',
            metadata={
                'deposit_ref': deposit_ref,
                'gateway': funding_info['gateway'],
                'awdpay_response': deposit_res,
            },
            ip=get_client_ip(request),
        )

        out = TransferSerializer(transfer)
        return Response(
            {
                'success': True,
                'message': (
                    'Transfer initiated. A USSD prompt has been sent to the sender\'s phone. '
                    'Please confirm the payment on your mobile device.'
                ),
                'data': out.data,
            },
            status=status.HTTP_201_CREATED,
        )


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
