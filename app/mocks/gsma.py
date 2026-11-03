"""Mock of the GSMA QoD API gateway (docs/SPEC.md §6, V4 `mock_apigw_contract.json`)."""

import os
import random
import secrets
import time
from datetime import timedelta

from app.models import now
from app.services import config


def validate(request: dict) -> dict:
    """POST /mock-gsma/validate: result by mock_rules.yaml; `error` also comes with HTTP 200."""
    rules = config.load("mock_rules")["validate"]
    if rules.get("latency_ms") and not os.getenv("MOCK_NO_LATENCY"):
        time.sleep(random.uniform(*rules["latency_ms"]) / 1000)
    checked = {"checked_at": now().isoformat()}
    signature = request.get("signature", {})
    for rule in rules.get("rules", []):
        if all(signature.get(key) == value for key, value in rule["match"].items()):
            return {
                "result": rule["result"],
                "error_code": rule.get("error_code"),
                "error_message": rule.get("message"),
                **checked,
            }
    return {**rules["default"], **checked}


def create_session(request: dict) -> dict:
    """POST /mock-gsma/qod/sessions → 201."""
    started = now()
    expires = started + timedelta(hours=request["duration"]["hours"])
    return {
        "session_id": f"qod-session-{secrets.token_hex(3)}",
        "status": "ACTIVE",
        "started_at": started.isoformat(),
        "expires_at": expires.isoformat(),
        "qos_profile": request["qos_profile"]["code"],
    }


def create_assignment(request: dict) -> dict:
    """POST /mock-gsma/qos-assignments (CAMARA QoS Provisioning subset) → 201."""
    return {
        "assignmentId": f"asg-{secrets.token_hex(2)}",
        "device": request["device"],
        "qosProfile": request["qosProfile"],
        "status": "REQUESTED",
    }


def get_assignment(assignment_id: str) -> dict:
    """GET /mock-gsma/qos-assignments/{id}: the mock network confirms immediately."""
    return {"assignmentId": assignment_id, "status": "AVAILABLE"}
