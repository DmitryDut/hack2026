import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from scripts import seed  # noqa: E402


@pytest.fixture
def client():
    seed.main()
    with TestClient(app) as c:
        yield c


def login_as(client: TestClient, login: str = "mts-link-1"):
    r = client.post("/login", data={"login": login, "password": "demo"}, follow_redirects=False)
    assert r.status_code == 303
    return client
