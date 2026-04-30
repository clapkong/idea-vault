import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_generate_returns_job_id():
    with patch("routers.generate.asyncio.create_task"):
        res = client.post("/generate", json={"user_input": "테스트 아이디어"})
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "processing"


def test_generate_creates_meta_and_input(tmp_data_dir):
    with patch("routers.generate.asyncio.create_task"):
        res = client.post("/generate", json={"user_input": "테스트 아이디어"})
    job_id = res.json()["job_id"]
    job_dir = tmp_data_dir / job_id

    assert (job_dir / "input.txt").read_text() == "테스트 아이디어"

    meta = json.loads((job_dir / "meta.json").read_text())
    assert meta["status"] == "processing"
    assert meta["favorite"] is False
    assert meta["deleted"] is False
