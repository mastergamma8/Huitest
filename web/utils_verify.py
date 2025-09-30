# -*- coding: utf-8 -*-
import hashlib
import hmac
import urllib.parse

def _parse_init_data(init_data: str):
    # init_data is a URL-encoded query string from Telegram WebApp
    parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
    # flatten single values
    return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

def verify_telegram_init_data(init_data: str, bot_token: str) -> bool:
    """
    Verifies Telegram WebApp initData according to the docs.
    secret_key = HMAC_SHA256("WebAppData", bot_token)
    check_string = "\n".join(sorted([f"{k}={v}" for k!=hash]))
    hash_hex = HMAC_SHA256(secret_key, check_string)
    """
    try:
        data = _parse_init_data(init_data)
        recv_hash = data.pop("hash", None)
        if not recv_hash:
            return False

        # Build data_check_string
        pairs = []
        for k in sorted(data.keys()):
            v = data[k]
            if isinstance(v, list):
                # Not expected, but normalize
                v = ",".join(v)
            pairs.append(f"{k}={v}")
        data_check_string = "\n".join(pairs).encode("utf-8")

        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
        calc_hash = hmac.new(secret_key, data_check_string, hashlib.sha256).hexdigest()

        # Compare in constant time
        return hmac.compare_digest(calc_hash, recv_hash)
    except Exception:
        return False
