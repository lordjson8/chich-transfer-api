# integrations/awdpay.py

import requests
from django.conf import settings


class AwdPayClient:
    base_url: str
    api_key: str

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or settings.AWDPAY_API_URL
        self.api_key = api_key or settings.AWDPAY_API_KEY

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def create_transfer(self, *, reference: str, amount: str, currency: str,
                        recipient_phone: str, recipient_name: str, description: str | None = None) -> dict:
        payload = {
            'reference_id': reference,
            'amount': amount,
            'currency': currency,
            'recipient_phone': recipient_phone,
            'recipient_name': recipient_name,
            'description': description or '',
        }
        resp = requests.post(
            f"{self.base_url}/transfers/",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        data = resp.json()
        if resp.status_code not in (200, 201):
            return {'success': False, 'error': data.get('error', 'Transfer failed')}
        return {'success': True, 'provider_id': data.get('id'), 'raw': data}


    def collect_mobile_money(self, *, amount: str, currency: str,msisdn: str, provider: str, reference: str, description: str = "") -> dict:
        payload = {
            "reference_id": reference,
            "amount": amount,
            "currency": currency,
            "msisdn": msisdn,
            "provider": provider,  # e.g. "mtn_cm", "orange_cm"
            "description": description,
        }
        resp = requests.post(
            f"{self.base_url}/collections/mobile_money/",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        data = resp.json()
        if resp.status_code not in (200, 201):
            return {"success": False, "error": data.get("error", "Collection failed")}
        return {"success": True, "provider_id": data.get("id"), "raw": data}

    def payout_mobile_money(self, *, amount: str, currency: str,
                            msisdn: str, provider: str, reference: str, description: str = "") -> dict:
        payload = {
            "reference_id": reference,
            "amount": amount,
            "currency": currency,
            "msisdn": msisdn,
            "provider": provider,  # e.g. "mtn_ci"
            "description": description,
        }
        resp = requests.post(
            f"{self.base_url}/payouts/mobile_money/",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        data = resp.json()
        if resp.status_code not in (200, 201):
            return {"success": False, "error": data.get("error", "Payout failed")}
        return {"success": True, "provider_id": data.get("id"), "raw": data}
