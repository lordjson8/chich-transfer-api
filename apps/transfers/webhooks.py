# apps/transfers/webhooks.py

"""
AWDPay callback endpoints for the two-phase transfer flow.

Two endpoints:
  POST /webhooks/awdpay/deposit/     - deposit status callbacks
  POST /webhooks/awdpay/withdrawal/  - withdrawal status callbacks

AWDPay sends callbacks in two possible formats depending on the gateway:

PayDunya format:
  {
    "data": {
      "custom_data": {"trxId": "<reference>"},
      "status": "completed" | "failed"
    }
  }

MTN format:
  {
    "externalId": "<reference>",
    "status": "SUCCESSFUL" | "FAILED"
  }
"""

import json
import logging

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .models import Transfer, TransferStatus, TransferAuditLog
from apps.integrations.awdpay import AwdPayClient, AWDPayAPIError, AWDPayTokenError
from apps.integrations.gateway_mapping import get_gateway_info

logger = logging.getLogger(__name__)


def _parse_callback(payload: dict) -> tuple[str | None, str | None]:
    """
    Extract (reference, status_str) from either PayDunya or MTN callback format.
    Returns (None, None) if the format is unrecognised.
    """
    # PayDunya format
    data_block = payload.get('data')
    if isinstance(data_block, dict):
        custom = data_block.get('custom_data', {})
        ref = custom.get('trxId')
        st = data_block.get('status', '').lower()
        if ref and st:
            return ref, st

    # MTN format
    ref = payload.get('externalId')
    st = payload.get('status', '').upper()
    if ref and st:
        # Normalise MTN statuses
        status_map = {
            'SUCCESSFUL': 'completed',
            'FAILED': 'failed',
            'PENDING': 'pending',
        }
        return ref, status_map.get(st, st.lower())

    return None, None


def _trigger_withdrawal(transfer: Transfer):
    """
    After deposit is confirmed, automatically initiate the withdrawal (payout) phase.
    """
    payout_info = get_gateway_info(transfer.payout_mobile_provider)
    if not payout_info:
        msg = f"No gateway mapping for payout provider: {transfer.payout_mobile_provider}"
        logger.error(msg)
        transfer.mark_failed(msg, code='PAYOUT_GATEWAY_MISSING')
        TransferAuditLog.log(transfer, 'failed', metadata={'error': msg})
        return

    client = AwdPayClient()
    try:
        withdrawal_res = client.initiate_withdrawal(
            amount=str(transfer.destination_amount or transfer.amount),
            currency=payout_info['currency'],
            gateway=payout_info['gateway'],
            phone=transfer.recipient_phone,
            country=payout_info['country'],
            reference=transfer.reference,
            description=f"Payout for {transfer.reference}",
        )
    except (AWDPayAPIError, AWDPayTokenError) as exc:
        logger.error("Withdrawal initiation failed for %s: %s", transfer.reference, exc)
        transfer.mark_failed(str(exc), code='WITHDRAWAL_INIT_ERROR')
        TransferAuditLog.log(transfer, 'withdrawal_failed', metadata={'error': str(exc)})
        return

    withdrawal_ref = withdrawal_res.get('withdrawRef', withdrawal_res.get('ref', transfer.reference))
    transfer.mark_withdrawal_pending(withdrawal_ref, payout_info['gateway'])

    TransferAuditLog.log(
        transfer, 'withdrawal_initiated',
        metadata={
            'withdrawal_ref': withdrawal_ref,
            'gateway': payout_info['gateway'],
            'awdpay_response': withdrawal_res,
        },
    )
    logger.info("Withdrawal initiated for transfer %s, ref=%s", transfer.reference, withdrawal_ref)


@csrf_exempt
@require_POST
def awdpay_deposit_callback(request):
    """Handle deposit (collect) status callbacks from AWDPay."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    logger.info("Deposit callback received: %s", payload)

    ref, callback_status = _parse_callback(payload)
    if not ref or not callback_status:
        logger.warning("Deposit callback: could not parse reference/status from payload")
        return JsonResponse({'error': 'Unrecognised callback format'}, status=400)

    try:
        transfer = Transfer.objects.get(reference=ref)
    except Transfer.DoesNotExist:
        logger.warning("Deposit callback: transfer not found for ref=%s", ref)
        return JsonResponse({'error': 'Transfer not found'}, status=404)

    TransferAuditLog.log(
        transfer, 'webhook_received',
        metadata={'phase': 'deposit', 'callback_status': callback_status, 'raw': payload},
    )

    if callback_status == 'completed':
        if transfer.status == TransferStatus.DEPOSIT_PENDING:
            transfer.mark_deposit_confirmed()
            TransferAuditLog.log(transfer, 'deposit_confirmed', metadata=payload)
            logger.info("Deposit confirmed for %s, triggering withdrawal", transfer.reference)

            # Auto-trigger withdrawal phase
            _trigger_withdrawal(transfer)

    elif callback_status == 'failed':
        if transfer.status == TransferStatus.DEPOSIT_PENDING:
            transfer.mark_deposit_failed(
                message='Deposit failed via callback',
                code='DEPOSIT_CALLBACK_FAILED',
            )
            TransferAuditLog.log(transfer, 'deposit_failed', metadata=payload)
            logger.info("Deposit failed for %s", transfer.reference)

    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def awdpay_withdrawal_callback(request):
    """Handle withdrawal (payout) status callbacks from AWDPay."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    logger.info("Withdrawal callback received: %s", payload)

    ref, callback_status = _parse_callback(payload)
    if not ref or not callback_status:
        logger.warning("Withdrawal callback: could not parse reference/status from payload")
        return JsonResponse({'error': 'Unrecognised callback format'}, status=400)

    try:
        transfer = Transfer.objects.get(reference=ref)
    except Transfer.DoesNotExist:
        logger.warning("Withdrawal callback: transfer not found for ref=%s", ref)
        return JsonResponse({'error': 'Transfer not found'}, status=404)

    TransferAuditLog.log(
        transfer, 'webhook_received',
        metadata={'phase': 'withdrawal', 'callback_status': callback_status, 'raw': payload},
    )

    if callback_status == 'completed':
        if transfer.status == TransferStatus.WITHDRAWAL_PENDING:
            transfer.mark_completed()
            TransferAuditLog.log(transfer, 'completed', metadata=payload)
            logger.info("Transfer %s completed successfully", transfer.reference)

    elif callback_status == 'failed':
        if transfer.status == TransferStatus.WITHDRAWAL_PENDING:
            transfer.mark_failed(
                message='Withdrawal failed via callback',
                code='WITHDRAWAL_CALLBACK_FAILED',
            )
            TransferAuditLog.log(transfer, 'withdrawal_failed', metadata=payload)
            logger.info("Withdrawal failed for %s", transfer.reference)

    return JsonResponse({'success': True})
