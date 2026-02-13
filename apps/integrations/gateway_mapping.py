# apps/integrations/gateway_mapping.py

"""
Maps internal MobileMoneyProvider codes to AWDPay gateway names,
country ISO codes, and currencies.
"""

# Each entry: internal_code -> (awdpay_gateway_name, country_iso, currency)
GATEWAY_MAP = {
    # Cameroon (XAF)
    'mtn_cm':      ('mtn', 'CM', 'XAF'),
    'orange_cm':   ('orange-cm', 'CM', 'XAF'),

    # Cote d'Ivoire (XOF)
    'mtn_ci':      ('mtn-ci', 'CI', 'XOF'),
    'orange_ci':   ('orange-ci', 'CI', 'XOF'),
    'moov_ci':     ('moov-ci', 'CI', 'XOF'),
    'wave_ci':     ('wave-ci', 'CI', 'XOF'),

    # Senegal (XOF)
    'orange_sn':   ('orange-sn', 'SN', 'XOF'),
    'free_sn':     ('free-sn', 'SN', 'XOF'),
    'wave_sn':     ('wave-sn', 'SN', 'XOF'),

    # Mali (XOF)
    'orange_ml':   ('orange-ml', 'ML', 'XOF'),
    'moov_ml':     ('moov-ml', 'ML', 'XOF'),

    # Burkina Faso (XOF)
    'orange_bf':   ('orange-bf', 'BF', 'XOF'),
    'moov_bf':     ('moov-bf', 'BF', 'XOF'),

    # Togo (XOF)
    'togocom_tg':  ('togocom-tg', 'TG', 'XOF'),
    'moov_tg':     ('moov-tg', 'TG', 'XOF'),

    # Benin (XOF)
    'mtn_bj':      ('mtn-bj', 'BJ', 'XOF'),
    'moov_bj':     ('moov-bj', 'BJ', 'XOF'),
}


def get_gateway_info(provider_code: str) -> dict | None:
    """
    Return AWDPay gateway info for an internal provider code.
    Returns dict with keys: gateway, country, currency — or None if unmapped.
    """
    entry = GATEWAY_MAP.get(provider_code)
    if entry is None:
        return None
    return {
        'gateway': entry[0],
        'country': entry[1],
        'currency': entry[2],
    }


def get_gateway_name(provider_code: str) -> str | None:
    """Return just the AWDPay gateway name, or None."""
    entry = GATEWAY_MAP.get(provider_code)
    return entry[0] if entry else None
