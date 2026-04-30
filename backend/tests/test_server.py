from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_ready_ok():
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    with patch("main.requests.get", return_value=mock_ok):
        res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert "openrouter" in data
    assert "tavily" in data


def test_ready_degraded():
    # 외부 연결 실패 시 degraded 반환
    with patch("main.requests.get", side_effect=Exception("timeout")):
        res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["openrouter"] == "degraded"
    assert data["tavily"] == "degraded"
