import json
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_completed_job(tmp_data_dir: Path, job_id: str, date: str, tokens: int, model: str) -> None:
    job_dir = tmp_data_dir / job_id
    job_dir.mkdir()
    (job_dir / "meta.json").write_text(json.dumps({
        "job_id": job_id, "status": "done",
        "favorite": False, "deleted": False,
        "created_at": f"{date}T00:00:00", "tokens": tokens,
    }))
    (job_dir / "result.json").write_text(json.dumps({
        "prd": "# Test", "loop_history": [], "duration_sec": 5.0,
        "events": [{"type": "agent_done", "agent": "planner", "model": model, "tokens": tokens}],
    }))


def test_analytics_empty():
    res = client.get("/analytics")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total_jobs"] == 0
    assert data["summary"]["total_tokens"] == 0


def test_analytics_with_data(tmp_data_dir):
    _make_completed_job(tmp_data_dir, "job1", "2026-01-01", 1000, "anthropic/claude-sonnet-4-5")
    res = client.get("/analytics")
    data = res.json()
    assert data["summary"]["total_jobs"] == 1
    assert data["summary"]["total_tokens"] == 1000
    assert len(data["modelAggregates"]) == 1


def test_analytics_range_today(tmp_data_dir):
    today = datetime.now().strftime("%Y-%m-%d")
    _make_completed_job(tmp_data_dir, "job1", today, 500, "anthropic/claude-sonnet-4-5")
    _make_completed_job(tmp_data_dir, "job2", "2020-01-01", 1000, "anthropic/claude-sonnet-4-5")
    res = client.get("/analytics?range=today")
    assert res.json()["summary"]["total_tokens"] == 500


def test_analytics_range_7days(tmp_data_dir):
    today = datetime.now().strftime("%Y-%m-%d")
    _make_completed_job(tmp_data_dir, "job1", today, 300, "anthropic/claude-haiku-4-5")
    _make_completed_job(tmp_data_dir, "job2", "2020-01-01", 9999, "anthropic/claude-haiku-4-5")
    res = client.get("/analytics?range=7days")
    assert res.json()["summary"]["total_tokens"] == 300


def test_analytics_csv(tmp_data_dir):
    _make_completed_job(tmp_data_dir, "job1", "2026-01-01", 1000, "anthropic/claude-sonnet-4-5")
    res = client.get("/analytics/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
