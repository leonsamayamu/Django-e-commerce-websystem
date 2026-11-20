"""Minimal PayHero API client (https://docs.payhero.co.ke). Standard library only; easy to mock in tests."""
import base64
import json
import re
import urllib.error
import urllib.request
from decimal import ROUND_UP, Decimal

API = "https://backend.payhero.co.ke/api/v2"
TIMEOUT = 20


class PayHeroError(Exception):
    pass


def normalize_phone(raw):
    """Kenyan mobile -> 2547XXXXXXXX / 2541XXXXXXXX, or None if it does not look valid."""
    digits = re.sub(r"[^\d]", "", raw or "")
    if digits.startswith("254"):
        local = digits[3:]
    elif digits.startswith("0"):
        local = digits[1:]
    else:
        local = digits
    return "254" + local if re.fullmatch(r"[71]\d{8}", local) else None


def http_json(method, url, *, headers, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode()).get("error_message") or exc.reason
        except Exception:  # noqa: BLE001
            detail = exc.reason
        raise PayHeroError(f"PayHero rejected the request ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise PayHeroError(f"Could not reach PayHero: {exc}") from exc


def _auth(gateway):
    if not gateway.has_credentials:
        raise PayHeroError("This gateway has no API credentials.")
    token = base64.b64encode(f"{gateway.api_username}:{gateway.api_password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def initiate_stk(gateway, *, amount, phone, reference, customer_name, callback_url):
    body = {
        "amount": int(Decimal(amount).quantize(Decimal("1"), rounding=ROUND_UP)),  # whole shillings
        "phone_number": phone, "channel_id": gateway.channel_id, "provider": gateway.provider_code,
        "external_reference": reference, "customer_name": customer_name[:60], "callback_url": callback_url,
    }
    if gateway.provider_code == "sasapay":
        body["network_code"] = "63902"
    if gateway.credential_id:
        body["credential_id"] = gateway.credential_id
    data = http_json("POST", f"{API}/payments", headers=_auth(gateway), body=body)
    if not data.get("success", True) or not data.get("reference"):
        raise PayHeroError(f"PayHero did not accept the payment: {data}")
    return data


def transaction_status(gateway, provider_reference):
    """-> {'status': 'QUEUED' | 'SUCCESS' | 'FAILED', ...}"""
    return http_json("GET", f"{API}/transaction-status?reference={provider_reference}", headers=_auth(gateway))
