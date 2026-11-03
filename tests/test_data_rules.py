"""P4: signature validation against V1 `invalid_signatures.json`."""

import json
from pathlib import Path

from tests.conftest import login_as

CASES = json.loads((Path(__file__).parent / "fixtures" / "invalid_signatures.json").read_text())[
    "cases"
]
SVC = "/cabinet/services/svc-vcs"


def test_invalid_signature_cases(client):
    login_as(client)
    for case in CASES:
        payload = case["payload"]
        if case["expected_http"] == 404:
            r = client.post("/cabinet/services/nonexistent-service-id/signatures", data={})
            assert r.status_code == 404, case["id"]
            continue
        data = {k: str(v) for k, v in payload.items() if k != "service_id"}
        r = client.post(f"{SVC}/signatures", data=data)
        # a rejected attempt is shown as a form error (422) and never adds a row
        assert r.status_code == 422, case["id"]
    page = client.get(f"{SVC}?tab=data").text
    assert page.count("vcs.mts-link.ru") == 1  # nothing was added by the invalid attempts


def test_delete_service_cascades(client):
    login_as(client)
    assert "Услуга удалена" in client.post("/cabinet/services/svc-chat/delete").text
    assert client.get("/cabinet/services/svc-chat").status_code == 404
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import Signature

    with Session(engine) as db:
        assert not db.exec(select(Signature).where(Signature.service_id == "svc-chat")).all()
