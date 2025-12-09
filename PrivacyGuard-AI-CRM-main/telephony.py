import os
import json
from typing import Dict, Any, Tuple

import requests


class TelephonyError(Exception):
    pass


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def initiate_vapi_call(to_phone: str, caller_id: str | None = None, payload: Dict[str, Any] | None = None) -> Tuple[bool, Dict[str, Any]]:
    base = os.getenv("VAPI_BASE_URL")
    token = os.getenv("VAPI_API_KEY")
    flow_id = os.getenv("VAPI_FLOW_ID")
    if not base or not token or not flow_id:
        return False, {"error": "Missing VAPI_BASE_URL/VAPI_API_KEY/VAPI_FLOW_ID"}
    body = {
        "to": to_phone,
        "from": caller_id or os.getenv("VAPI_CALLER_ID", ""),
        "flowId": flow_id,
        "variables": payload or {},
        "webhookUrl": os.getenv("VOICE_WEBHOOK_URL", "")
    }
    try:
        res = requests.post(f"{base.rstrip('/')}/calls", headers=_headers(token), data=json.dumps(body), timeout=15)
        if res.status_code >= 300:
            return False, {"error": f"Vapi HTTP {res.status_code}", "body": res.text}
        data = res.json()
        return True, data
    except Exception as e:
        return False, {"error": str(e)}


def initiate_sensy_call(to_phone: str, caller_id: str | None = None, payload: Dict[str, Any] | None = None) -> Tuple[bool, Dict[str, Any]]:
    base = os.getenv("SENSY_BASE_URL")
    token = os.getenv("SENSY_API_KEY")
    campaign = os.getenv("SENSY_CAMPAIGN_ID")
    if not base or not token or not campaign:
        return False, {"error": "Missing SENSY_BASE_URL/SENSY_API_KEY/SENSY_CAMPAIGN_ID"}
    body = {
        "campaignId": campaign,
        "to": to_phone,
        "callerId": caller_id or os.getenv("SENSY_CALLER_ID", ""),
        "meta": payload or {},
        "webhookUrl": os.getenv("VOICE_WEBHOOK_URL", "")
    }
    try:
        res = requests.post(f"{base.rstrip('/')}/outbound", headers=_headers(token), data=json.dumps(body), timeout=15)
        if res.status_code >= 300:
            return False, {"error": f"Sensy HTTP {res.status_code}", "body": res.text}
        data = res.json()
        return True, data
    except Exception as e:
        return False, {"error": str(e)}


def initiate_outbound_call(provider: str, to_phone: str, caller_id: str | None = None, payload: Dict[str, Any] | None = None) -> Tuple[bool, Dict[str, Any]]:
    provider = (provider or "").lower()
    if provider == "vapi":
        return initiate_vapi_call(to_phone, caller_id, payload)
    if provider in ("sensy", "ai_sensy", "aisensy"):
        return initiate_sensy_call(to_phone, caller_id, payload)
    return False, {"error": "Unknown provider"}


def normalize_webhook(provider: str, body: Dict[str, Any]) -> Dict[str, Any]:
    provider = (provider or "").lower()
    if provider == "vapi":
        return {
            "call_id": body.get("id") or body.get("callId"),
            "status": body.get("status"),
            "event": body.get("event"),
            "transcript": body.get("transcript"),
            "raw": body,
        }
    if provider in ("sensy", "ai_sensy", "aisensy"):
        return {
            "call_id": body.get("call_id") or body.get("id"),
            "status": body.get("status"),
            "event": body.get("event_type") or body.get("event"),
            "transcript": body.get("transcript"),
            "raw": body,
        }
    return {"raw": body}




