# apps/integrations/awdpay.py

"""
AWDPay API client with OAuth2 (Keycloak client_credentials) authentication.
Supports two-phase transfers: deposit (collect from sender) then withdrawal (payout to receiver).
"""

import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AWDPayTokenError(Exception):
    """Raised when OAuth2 token acquisition fails."""


class AWDPayAPIError(Exception):
    """Raised when an AWDPay API call fails."""

    def __init__(self, message: str, status_code: int | None = None, response_data: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class AwdPayClient:
    """
    AWDPay REST client.

    - Authenticates via Keycloak client_credentials grant
    - Caches the access token in memory, refreshes 60s before expiry
    - Provides methods for deposit, withdrawal, status checks, and info queries
    """

    _token: str | None = None
    _token_expires_at: float = 0.0

    def __init__(self):
        self.base_url = settings.AWDPAY_BASE_URL.rstrip('/')
        self.api_version = settings.AWDPAY_API_VERSION.strip('/')
        self.keycloak_base_url = settings.AWDPAY_KEYCLOAK_BASE_URL.rstrip('/')
        self.keycloak_realm = settings.AWDPAY_KEYCLOAK_REALM
        self.keycloak_client_id = settings.AWDPAY_KEYCLOAK_CLIENT_ID
        self.keycloak_client_secret = settings.AWDPAY_KEYCLOAK_CLIENT_SECRET
        self.callback_base_url = settings.AWDPAY_CALLBACK_BASE_URL.rstrip('/')

    # ------------------------------------------------------------------
    # OAuth2 token management
    # ------------------------------------------------------------------

    def _get_token_url(self) -> str:
        return (
            f"{self.keycloak_base_url}/realms/{self.keycloak_realm}"
            f"/protocol/openid-connect/token"
        )

    def _ensure_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        now = time.time()
        if self._token and now < self._token_expires_at:
            return self._token

        token_url = self._get_token_url()
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.keycloak_client_id,
            'client_secret': self.keycloak_client_secret,
        }

        try:
            resp = requests.post(token_url, data=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("AWDPay token request failed: %s", exc)
            raise AWDPayTokenError(f"Failed to obtain access token: {exc}") from exc

        self._token = data['access_token']
        expires_in = data.get('expires_in', 300)
        # Refresh 60s before actual expiry
        self._token_expires_at = now + expires_in - 60
        logger.info("AWDPay token acquired, expires_in=%s", expires_in)
        return self._token

    def _headers(self) -> dict:
        token = self._ensure_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _api_url(self, path: str) -> str:
        """Build full URL: base_url / api_version / path."""
        return f"{self.base_url}/{self.api_version}/{path.lstrip('/')}"

    def _public_url(self, path: str) -> str:
        """Build full URL for public endpoints (no api version prefix)."""
        return f"{self.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """Execute an HTTP request and return parsed JSON."""
        print(f"AWDPay API request: {method} {url} with kwargs: {kwargs.get('json') or kwargs.get('params')}")
        kwargs.setdefault('headers', self._headers())
        kwargs.setdefault('timeout', 30)

        try:
            resp = requests.request(method, url,**kwargs)
        except requests.RequestException as exc:
            logger.error("AWDPay request error: %s %s -> %s", method, url, exc)
            raise AWDPayAPIError(f"Request failed: {exc}") from exc

        try:
            data = resp.json()
        except ValueError:
            data = {}

        if resp.status_code >= 400:
            logger.warning(
                "AWDPay API error: %s %s -> %s %s",
                method, url, resp.status_code, data,
            )
            raise AWDPayAPIError(
                data.get('message', f"HTTP {resp.status_code}"),
                status_code=resp.status_code,
                response_data=data,
            )

        return data

    # ------------------------------------------------------------------
    # Deposit (collect money from sender)
    # ------------------------------------------------------------------

    def initiate_deposit(
        self,
        *,
        amount: str,
        currency: str,
        gateway: str,
        phone: str,
        country: str,
        reference: str,
        description: str = '',
    ) -> dict:
        """
        POST /api/v2/classic/deposit/initiate

        Initiates a deposit (collect) from the sender's mobile money account.
        The sender will receive a USSD prompt on their phone.

        Returns the AWDPay response dict (contains depositRef, etc.).
        """
        callback_url = f"{self.callback_base_url}/webhooks/awdpay/deposit/"
        payload = {
            "amount": 200,
            "currency": currency,
            "gatewayName": gateway,
            "customerName": phone,  # AWDPay uses customerName but we only have phone, so we put phone here
            "customerEmail": "aaa@aa.com",  # AWDPay requires customerEmail but we don't have it, so we put a dummy email
            "customerPhone": phone,
            "country": country,
            # "trxId": reference,
            "callbackUrl": callback_url,
            "metadata": { 
                "order_id": reference,
                "description": description or f'Deposit {reference}',
            }
        }

    
        print("AWDPay initiate_deposit payload:", payload)
        logger.info("AWDPay initiate_deposit: ref=%s gateway=%s amount=%s", reference, gateway, amount)
        return self._request('POST', self._api_url('classic/deposit/initiate'), json=payload)

    def get_deposit_status(self, deposit_ref: str) -> dict:
        """
        GET /api/v2/deposit/deposits/{ref}

        Checks the status of an existing deposit.
        """
        return self._request('GET', self._api_url(f'deposit/deposits/{deposit_ref}'))

    # ------------------------------------------------------------------
    # Withdrawal (payout to receiver)
    # ------------------------------------------------------------------

    def initiate_withdrawal(
        self,
        *,
        amount: str,
        currency: str,
        gateway: str,
        phone: str,
        country: str,
        reference: str,
        description: str = '',
    ) -> dict:
        """
        POST /api/v2/withdraw/initiate

        Initiates a withdrawal (payout) to the receiver's mobile money account.

        Returns the AWDPay response dict (contains withdrawRef, etc.).
        """
        callback_url = f"{self.callback_base_url}/webhooks/awdpay/withdrawal/"
        payload = {
            "amount": amount,
            "currency": currency,
            "gatewayName": gateway,
            "beneficiaryPhone": phone,
            "country": country,
            "trxId": reference,
            "callbackUrl": callback_url,
            "metadata": { 
                "withdrawal_id": reference,
                "description": description or f'Withdrawal {reference}',
            }
        }
        logger.info("AWDPay initiate_withdrawal: ref=%s gateway=%s amount=%s", reference, gateway, amount)
        return self._request('POST', self._api_url('withdraw/initiate'), json=payload)

    def get_withdrawal_status(self, withdrawal_ref: str) -> dict:
        """
        GET /api/v2/withdraw/withdrawals/{ref}

        Checks the status of an existing withdrawal.
        """
        return self._request('GET', self._api_url(f'withdraw/withdrawals/{withdrawal_ref}'))

    # ------------------------------------------------------------------
    # Info / utility endpoints
    # ------------------------------------------------------------------

    def list_deposit_gateways(self) -> dict:
        """GET /public/gateways/deposit/list"""
        return self._request('GET', self._public_url('public/gateways/deposit/list'))

    def list_withdrawal_gateways(self) -> dict:
        """GET /api/v2/withdraw/list"""
        return self._request('GET', self._api_url('withdraw/list'))

    def get_wallet_balance(self) -> dict:
        """GET /api/v2/wallet/balance"""
        return self._request('GET', self._api_url('wallet/balance'))
