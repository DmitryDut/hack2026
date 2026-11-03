"""P5: technical test metrics (latency, jitter, packet loss, throughput) against tariff norms."""

import copy

from app.services import config
from tests.conftest import login_as

SVC = "/cabinet/services/svc-vcs"


def start_test(client, tariff="PLATINUM"):
    login_as(client)
    client.post(f"{SVC}/tariff", data={"tariff_code": tariff, "duration_code": "12H"})
    client.post(f"{SVC}/confirm-price")
    client.post(f"{SVC}/test/start")


def test_metrics_are_shown_and_within_norms(client):
    start_test(client)
    for sig in ("sig-1", "sig-2", "sig-3"):
        client.post(f"{SVC}/test/check/{sig}")
    page = client.get(f"{SVC}?tab=test").text
    for text in ("Задержка", "Джиттер", "Потери пакетов", "Скорость", "норма ≤ 30", "норма ≥ 90"):
        assert text in page
    assert "Измерено сигнатур: 3 из 4" in page and "Все измеренные значения в норме" in page
    assert page.count("В норме") == 3


def test_metrics_are_deterministic(client):
    start_test(client)
    client.post(f"{SVC}/test/check/sig-1")
    first = client.get(f"{SVC}?tab=test").text
    client.post(f"{SVC}/test/back")
    start_test(client)
    client.post(f"{SVC}/test/check/sig-1")
    again = client.get(f"{SVC}?tab=test").text
    cut = lambda html: html[html.index("Измерено сигнатур") : html.index("Измерено сигнатур") + 40]  # noqa: E731
    assert cut(first) == cut(again)


def test_timeout_rule_has_no_metrics_but_a_reason(client):
    start_test(client)
    client.post(f"{SVC}/test/check/sig-4")
    page = client.get(f"{SVC}?tab=test").text
    assert "BEARER_TIMEOUT" in page and "Измерено сигнатур" not in page


def test_threshold_violation_fails_the_test_with_reason(client, monkeypatch):
    original = config.load

    def patched(name):
        data = copy.deepcopy(original(name))
        if name == "mock_rules":
            data["validate"]["rules"].append(
                {"match": {"uri": "vcs.mts-link.ru"}, "metrics": {"latency_ms": 180}}
            )
        return data

    monkeypatch.setattr(config, "load", patched)
    start_test(client)
    client.post(f"{SVC}/test/check/sig-1")
    page = client.get(f"{SVC}?tab=test").text
    assert "METRIC_THRESHOLD" in page and "Задержка 180" in page and "выше нормы 30" in page
    assert "Тест не пройден" in page


def test_target_latency_comes_from_the_tariff(client):
    login_as(client, "operator")
    client.post(
        "/admin/data/tariff/PLATINUM",
        data={
            "name": "Платина",
            "bitrate_mbps": "100",
            "priority_level": "4",
            "price_multiplier": "3",
            "sla_percent": "99.95",
            "latency_ms": "5",
            "status": "ACTIVE",
        },
    )
    start_test(client)
    client.post(f"{SVC}/test/check/sig-1")
    page = client.get(f"{SVC}?tab=test").text
    assert "METRIC_THRESHOLD" in page and "нормы 5" in page


def test_launch_panel_shows_test_results(client):
    start_test(client)
    for sig in ("sig-1", "sig-2", "sig-3"):
        client.post(f"{SVC}/test/check/{sig}")
        client.post(f"{SVC}/test/confirm/{sig}")
    client.post(f"{SVC}/test/check/sig-4")
    client.post(f"{SVC}/test/back")
    client.post(
        f"{SVC}/signatures/sig-4",
        data={"ipv4": "10.10.1.8", "uri": "media2.mts-link.ru", "port": "5006", "protocol": "RTP"},
    )
    client.post(f"{SVC}/test/start")
    for sig in ("sig-1", "sig-2", "sig-3", "sig-4"):
        client.post(f"{SVC}/test/check/{sig}")
        client.post(f"{SVC}/test/confirm/{sig}")
    client.post(f"{SVC}/apply")
    panel = client.get(f"{SVC}?tab=launch").text
    assert "Результаты теста" in panel and "задержка в среднем" in panel
