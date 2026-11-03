"""Mock of the GSMA QoD API gateway (docs/SPEC.md §6, V4 `mock_apigw_contract.json`)."""

import hashlib
import os
import random
import secrets
import time

from app.models import now
from app.services import config


def _unit(key: str, n: int) -> float:
    """Deterministic pseudo-random number in [0, 1) so the demo is repeatable."""
    digest = hashlib.sha256(f"{key}:{n}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 2**32


def _measure(signature: dict, profile: dict, overrides: dict) -> dict:
    key = ":".join(
        str(x)
        for x in (
            signature.get("ipv4"),
            signature.get("port"),
            signature.get("protocol"),
            profile.get("code"),
        )
    )
    # what the network can deliver depends on the priority class, not on the promised target
    capability = 100 / max(profile.get("priority_level") or 1, 1)
    values = {
        "latency_ms": round(capability * (0.45 + 0.35 * _unit(key, 0)), 1),
        "jitter_ms": round(1 + 4 * _unit(key, 1), 1),
        "packet_loss_pct": round(0.05 + 0.30 * _unit(key, 2), 2),
        "throughput_mbps": round(profile.get("bitrate_mbps", 0) * (0.93 + 0.06 * _unit(key, 3)), 1),
    }
    values.update(overrides)
    return values


def _norms(profile: dict, thresholds: dict) -> dict:
    return {
        "latency_ms": profile.get("latency_ms") or 100,
        "jitter_ms": thresholds["jitter_ms"],
        "packet_loss_pct": thresholds["packet_loss_pct"],
        "throughput_mbps": round(
            profile.get("bitrate_mbps", 0) * thresholds["throughput_ratio"], 1
        ),
    }


LABELS = {
    "latency_ms": "Задержка",
    "jitter_ms": "Джиттер",
    "packet_loss_pct": "Потери",
    "throughput_mbps": "Скорость",
}
UNITS = {"latency_ms": "мс", "jitter_ms": "мс", "packet_loss_pct": "%", "throughput_mbps": "Мбит/с"}


def _violations(values: dict, norms: dict) -> list[str]:
    bad = [k for k in ("latency_ms", "jitter_ms", "packet_loss_pct") if values[k] > norms[k]]
    if values["throughput_mbps"] < norms["throughput_mbps"]:
        bad.append("throughput_mbps")
    return bad


def validate(request: dict) -> dict:
    """POST /mock-gsma/validate: technical metrics, verdict by thresholds, `error` with HTTP 200."""
    cfg = config.load("mock_rules")
    rules = cfg["validate"]
    if rules.get("latency_ms") and not os.getenv("MOCK_NO_LATENCY"):
        time.sleep(random.uniform(*rules["latency_ms"]) / 1000)
    checked = {"checked_at": now().isoformat()}
    signature, profile = request.get("signature", {}), request.get("qos_profile", {})
    overrides: dict = {}
    for rule in rules.get("rules", []):
        if all(signature.get(key) == value for key, value in rule["match"].items()):
            if rule.get("result") == "error":
                return {
                    "result": "error",
                    "error_code": rule.get("error_code"),
                    "error_message": rule.get("message"),
                    "metrics": None,
                    **checked,
                }
            overrides.update(rule.get("metrics", {}))
    values = _measure(signature, profile, overrides)
    norms = _norms(profile, cfg["metrics"]["thresholds"])
    bad = _violations(values, norms)
    body = {"metrics": values, "norms": norms, "violations": bad, **checked}
    if bad:
        reasons = "; ".join(
            f"{LABELS[k]} {values[k]} {UNITS[k]} {'ниже' if k == 'throughput_mbps' else 'выше'} "
            f"нормы {norms[k]} {UNITS[k]}"
            for k in bad
        )
        return {
            "result": "error",
            "error_code": "METRIC_THRESHOLD",
            "error_message": reasons,
            **body,
        }
    return {**rules["default"], "error_code": None, "error_message": None, **body}


def create_session(request: dict) -> dict:
    """POST /mock-gsma/qod/sessions → 201. The session lives until it is deleted."""
    return {
        "session_id": f"qod-session-{secrets.token_hex(3)}",
        "status": "ACTIVE",
        "started_at": now().isoformat(),
        "qos_profile": request["qos_profile"]["code"],
    }


def delete_session(session_id: str) -> dict:
    """DELETE /mock-gsma/qod/sessions/{id}: the priority is switched off."""
    return {"session_id": session_id, "status": "TERMINATED", "terminated_at": now().isoformat()}
