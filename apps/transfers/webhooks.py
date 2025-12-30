# apps/transfers/webhooks.py

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
import json
import hmac
import hashlib

from .models import Transfer, TransferStatus, TransferAuditLog


def _verify_signature(request) -> bool:
    secret = settings.AWDPAY_WEBHOOK_SECRET.encode()
    received = request.META.get('HTTP_X_AWDPAY_SIGNATURE', '')
    computed = hmac.new(secret, request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received, computed)


@csrf_exempt
@require_POST
def awdpay_webhook(request):
    if not _verify_signature(request):
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event = payload.get('event')
    data = payload.get('data', {})
    ref = data.get('reference_id')

    try:
        transfer = Transfer.objects.get(reference=ref)
    except Transfer.DoesNotExist:
        return JsonResponse({'error': 'Transfer not found'}, status=404)

    TransferAuditLog.log(transfer, 'webhook_received', metadata={'event': event, 'raw': data})

    if event == 'transfer.completed':
        transfer.mark_completed()
        TransferAuditLog.log(transfer, 'completed', metadata=data)
    elif event == 'transfer.failed':
        transfer.mark_failed(
            data.get('error', 'Transfer failed'),
            code=data.get('error_code'),
        )
        TransferAuditLog.log(transfer, 'failed', metadata=data)
    elif event == 'transfer.reversed':
        transfer.status = TransferStatus.REVERSED
        transfer.save(update_fields=['status'])
        TransferAuditLog.log(transfer, 'webhook_processed', metadata=data)

    return JsonResponse({'success': True})
