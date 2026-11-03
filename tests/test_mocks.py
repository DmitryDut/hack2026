"""P3: GSMA QoD API mock contracts (V4 `mock_apigw_contract.json`)."""

import json
from pathlib import Path

CONTRACT = json.loads((Path(__file__).parent / "fixtures" / "mock_apigw_contract.json").read_text())


def test_validate_success_and_error_with_http_200(client):
    ok = client.post("/mock-gsma/validate", json=CONTRACT["validate"]["request"])
    assert ok.status_code == 200 and ok.json()["result"] == "success"
    bad = {
        "signature": {
            "ipv4": "10.10.1.8",
            "uri": "media2.mts-link.ru",
            "port": 5005,
            "protocol": "RTP",
        }
    }
    err = client.post("/mock-gsma/validate", json=bad)
    assert err.status_code == 200 and err.json()["result"] == "error"
    assert (
        err.json()["error_code"] == "BEARER_TIMEOUT"
        and "RTP-поток не отвечает" in err.json()["error_message"]
    )
    fixed = {"signature": {**bad["signature"], "port": 5006}}
    assert client.post("/mock-gsma/validate", json=fixed).json()["result"] == "success"


def test_session_contract(client):
    r = client.post("/mock-gsma/qod/sessions", json=CONTRACT["create_session"]["request"])
    body = r.json()
    assert (
        r.status_code == 201
        and body["status"] == "ACTIVE"
        and body["session_id"].startswith("qod-session-")
    )
    assert body["qos_profile"] == "PLATINUM" and body["expires_at"] > body["started_at"]
