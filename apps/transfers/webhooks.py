# apps/transfers/webhooks.py

"""
AWDPay callback endpoints for the two-phase transfer flow.

Two endpoints:
  POST /webhooks/awdpay/deposit/     - deposit status callbacks
  POST /webhooks/awdpay/withdrawal/  - withdrawal status callbacks

AWDPay deposit webhook payload (top-level fields):
  {
    "event": "deposit.completed" | "deposit.failed" | "deposit.expired" | "deposit.pending",
    "reference": "<awdpay deposit reference>",
    "status": "completed" | "failed" | "expired" | "pending",
    "amount": 1000,
    "currency": "XOF",
    "fees": 0,
    "gatewayName": "...",
    "customerEmail": "...",
    "customerPhone": "...",
    "customerName": "...",
    "createdAt": "...",
    "completedAt": "...",
    "metadata": {"order_id": "<our transfer reference>", ...},
    "signature": "HMAC_SHA256(webhook_secret, reference + status + amount)"
  }

AWDPay withdrawal webhook payload (nested under 'data'):
  {
    "event": "withdrawal.success" | "withdrawal.failed" | "withdrawal.processing" | "withdrawal.pending",
    "timestamp": "...",
    "data": {
      "reference": "<awdpay withdrawal reference>",
      "status": "success" | "failed" | "processing" | "pending",
      "amount": 1000,
      "currency": "XOF",
      "beneficiaryPhone": "...",
      "gatewayName": "...",
      "externalReference": "...",
      "failureReason": "...",
      "failureMessage": "...",
      "metadata": {"withdrawal_id": "<our transfer reference>", ...},
      ...
    }
  }
  Headers: X-AWDPay-Signature, X-AWDPay-Timestamp
"""

import hashlib
import hmac
import json
import logging
import time

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .models import Transfer, TransferStatus, TransferAuditLog
from apps.integrations.awdpay import AwdPayClient, AWDPayAPIError, AWDPayTokenError
from apps.integrations.gateway_mapping import get_gateway_info

logger = logging.getLogger(__name__)

SIGNATURE_TOLERANCE_SECONDS = 300  # 5 minutes


# ------------------------------------------------------------------
# Signature verification
# ------------------------------------------------------------------

def _verify_deposit_signature(payload: dict) -> bool:
    """
    Verify HMAC-SHA256 signature for deposit webhooks.
    Signature = HMAC_SHA256(webhook_secret, reference + status + amount)
    """
    secret = getattr(settings, 'AWDPAY_WEBHOOK_SECRET', '')
    if not secret:
        logger.warning("AWDPAY_WEBHOOK_SECRET not configured, skipping signature verification")
        return True

    signature = payload.get('signature', '')
    if not signature:
        logger.warning("Deposit webhook missing signature field")
        return False

    reference = payload.get('reference', '')
    status = payload.get('status', '')
    amount = str(payload.get('amount', ''))

    message = f"{reference}{status}{amount}"
    expected = hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def _verify_withdrawal_signature(request) -> bool:
    """
    Verify HMAC-SHA256 signature for withdrawal webhooks.
    Uses X-AWDPay-Signature and X-AWDPay-Timestamp headers.
    Timestamp must be within 5 minutes.
    """
    secret = getattr(settings, 'AWDPAY_WEBHOOK_SECRET', '')
    if not secret:
        logger.warning("AWDPAY_WEBHOOK_SECRET not configured, skipping signature verification")
        return True

    signature = request.headers.get('X-AWDPay-Signature', '')
    timestamp = request.headers.get('X-AWDPay-Timestamp', '')

    if not signature or not timestamp:
        logger.warning("Withdrawal webhook missing signature headers")
        return False

    # Verify timestamp is within tolerance
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            ts = int(dt.timestamp())
        except (ValueError, TypeError):
            logger.warning("Withdrawal webhook invalid timestamp: %s", timestamp)
            return False

    if abs(time.time() - ts) > SIGNATURE_TOLERANCE_SECONDS:
        logger.warning("Withdrawal webhook timestamp too old: %s", timestamp)
        return False

    # Verify signature against raw body
    message = f"{timestamp}.{request.body.decode()}"
    expected = hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ------------------------------------------------------------------
# Payload parsing
# ------------------------------------------------------------------

def _parse_deposit_callback(payload: dict) -> tuple[str | None, str | None, str | None]:
    """
    Extract (transfer_reference, status, awdpay_reference) from deposit webhook.
    The transfer reference is stored in metadata.order_id during initiation.
    Returns (None, None, None) if the format is unrecognised.
    """
    event = payload.get('event', '')
    status = payload.get('status', '').lower()
    awdpay_ref = payload.get('reference', '')

    # Extract our transfer reference from metadata
    metadata = payload.get('metadata', {})
    transfer_ref = metadata.get('order_id', '') if isinstance(metadata, dict) else ''

    if not transfer_ref or not status:
        logger.warning("Deposit callback: missing transfer ref or status. event=%s", event)
        return None, None, None

    return transfer_ref, status, awdpay_ref


def _parse_withdrawal_callback(payload: dict) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """
    Extract (transfer_reference, status, awdpay_reference, failure_reason, failure_message)
    from withdrawal webhook.
    The transfer reference is stored in data.metadata.withdrawal_id during initiation.
    Returns (None, None, None, None, None) if the format is unrecognised.
    """
    data = payload.get('data', {})
    if not isinstance(data, dict):
        return None, None, None, None, None

    status = data.get('status', '').lower()
    awdpay_ref = data.get('reference', '')

    # Extract our transfer reference from metadata
    metadata = data.get('metadata', {})
    transfer_ref = metadata.get('withdrawal_id', '') if isinstance(metadata, dict) else ''

    failure_reason = data.get('failureReason', '')
    failure_message = data.get('failureMessage', '')

    if not transfer_ref or not status:
        logger.warning("Withdrawal callback: missing transfer ref or status")
        return None, None, None, None, None

    return transfer_ref, status, awdpay_ref, failure_reason, failure_message


# ------------------------------------------------------------------
# Withdrawal trigger (after deposit confirmed)
# ------------------------------------------------------------------

def _trigger_withdrawal(transfer: Transfer):

    print("triggering withdrawal for transfer:", transfer.reference)
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


# ------------------------------------------------------------------
# Webhook endpoints
# ------------------------------------------------------------------

@csrf_exempt
@require_POST
def awdpay_deposit_callback(request):
    """Handle deposit (collect) status callbacks from AWDPay."""
    
    print("AWDPay deposit callback received, body:", request.body)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    logger.info("Deposit callback received: %s", payload)

    # Verify signature
    if not _verify_deposit_signature(payload):
        logger.warning("Deposit callback: invalid signature")
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    transfer_ref, callback_status, awdpay_ref = _parse_deposit_callback(payload)
    if not transfer_ref or not callback_status:
        logger.warning("Deposit callback: could not parse reference/status from payload")
        return JsonResponse({'error': 'Unrecognised callback format'}, status=400)

    try:
        transfer = Transfer.objects.get(reference=transfer_ref)
    except Transfer.DoesNotExist:
        logger.warning("Deposit callback: transfer not found for ref=%s", transfer_ref)
        return JsonResponse({'error': 'Transfer not found'}, status=404)

    TransferAuditLog.log(
        transfer, 'webhook_received',
        metadata={
            'phase': 'deposit',
            'event': payload.get('event', ''),
            'callback_status': callback_status,
            'awdpay_reference': awdpay_ref,
            'raw': payload,
        },
    )

    # Idempotency: only process if transfer is still in deposit_pending
    if transfer.status != TransferStatus.DEPOSIT_PENDING:
        logger.info(
            "Deposit callback for %s ignored: transfer status is %s (not deposit_pending)",
            transfer_ref, transfer.status,
        )
        return JsonResponse({'success': True, 'message': 'Already processed'})

    if callback_status == 'completed':
        transfer.deposit_reference = awdpay_ref or transfer.deposit_reference
        transfer.save(update_fields=['deposit_reference', 'updated_at'])
        transfer.mark_deposit_confirmed()
        TransferAuditLog.log(transfer, 'deposit_confirmed', metadata=payload)
        logger.info("Deposit confirmed for %s, triggering withdrawal", transfer.reference)

        # Auto-trigger withdrawal phase
        _trigger_withdrawal(transfer)

    elif callback_status in ('failed', 'expired'):
        reason = 'Deposit expired via callback' if callback_status == 'expired' else 'Deposit failed via callback'
        code = 'DEPOSIT_CALLBACK_EXPIRED' if callback_status == 'expired' else 'DEPOSIT_CALLBACK_FAILED'
        transfer.mark_deposit_failed(message=reason, code=code)
        TransferAuditLog.log(transfer, 'deposit_failed', metadata=payload)
        logger.info("Deposit %s for %s", callback_status, transfer.reference)

    # 'pending' status is informational, no state change needed

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

    # Verify signature
    if not _verify_withdrawal_signature(request):
        logger.warning("Withdrawal callback: invalid signature")
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    parsed = _parse_withdrawal_callback(payload)
    transfer_ref, callback_status, awdpay_ref, failure_reason, failure_message = parsed

    if not transfer_ref or not callback_status:
        logger.warning("Withdrawal callback: could not parse reference/status from payload")
        return JsonResponse({'error': 'Unrecognised callback format'}, status=400)

    try:
        transfer = Transfer.objects.get(reference=transfer_ref)
    except Transfer.DoesNotExist:
        logger.warning("Withdrawal callback: transfer not found for ref=%s", transfer_ref)
        return JsonResponse({'error': 'Transfer not found'}, status=404)

    TransferAuditLog.log(
        transfer, 'webhook_received',
        metadata={
            'phase': 'withdrawal',
            'event': payload.get('event', ''),
            'callback_status': callback_status,
            'awdpay_reference': awdpay_ref,
            'failure_reason': failure_reason,
            'failure_message': failure_message,
            'raw': payload,
        },
    )

    # Idempotency: only process if transfer is still in withdrawal_pending
    if transfer.status != TransferStatus.WITHDRAWAL_PENDING:
        logger.info(
            "Withdrawal callback for %s ignored: transfer status is %s (not withdrawal_pending)",
            transfer_ref, transfer.status,
        )
        return JsonResponse({'success': True, 'message': 'Already processed'})

    if callback_status == 'success':
        transfer.withdrawal_reference = awdpay_ref or transfer.withdrawal_reference
        transfer.save(update_fields=['withdrawal_reference', 'updated_at'])
        transfer.mark_completed()
        TransferAuditLog.log(transfer, 'completed', metadata=payload)
        logger.info("Transfer %s completed successfully", transfer.reference)

    elif callback_status == 'failed':
        error_msg = failure_message or 'Withdrawal failed via callback'
        error_code = failure_reason or 'WITHDRAWAL_CALLBACK_FAILED'
        transfer.mark_failed(message=error_msg, code=error_code)
        TransferAuditLog.log(transfer, 'withdrawal_failed', metadata=payload)
        logger.info("Withdrawal failed for %s: %s", transfer.reference, error_msg)

    # 'pending' and 'processing' statuses are informational, no state change needed

    return JsonResponse({'success': True})
