from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_ready():
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    with patch("main.requests.get", return_value=mock_ok):
        res = client.get("/ready")
    assert res.status_code == 200
