import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_job(tmp_data_dir: Path, job_id: str, title: str = "", **meta_kwargs) -> None:
    job_dir = tmp_data_dir / job_id
    job_dir.mkdir()
    meta = {
        "job_id": job_id, "status": "done",
        "favorite": False, "deleted": False,
        "created_at": "2026-01-01T00:00:00", "tokens": 0,
        **meta_kwargs,
    }
    (job_dir / "meta.json").write_text(json.dumps(meta))
    if title:
        (job_dir / "result.json").write_text(json.dumps({
            "prd": f"# {title}", "loop_history": [], "events": [], "duration_sec": 1.0,
        }))


def test_history_empty():
    res = client.get("/history")
    assert res.status_code == 200
    assert res.json() == []


def test_history_returns_jobs(tmp_data_dir):
    _make_job(tmp_data_dir, "job1", title="아이디어 A")
    _make_job(tmp_data_dir, "job2", title="아이디어 B")
    res = client.get("/history")
    assert len(res.json()) == 2


def test_history_excludes_deleted(tmp_data_dir):
    _make_job(tmp_data_dir, "job1", title="살아있는 job")
    _make_job(tmp_data_dir, "job2", deleted=True)
    res = client.get("/history")
    assert len(res.json()) == 1


def test_history_search(tmp_data_dir):
    _make_job(tmp_data_dir, "job1", title="헬스케어 앱")
    _make_job(tmp_data_dir, "job2", title="교육 플랫폼")
    res = client.get("/history?search=헬스")
    result = res.json()
    assert len(result) == 1
    assert result[0]["job_id"] == "job1"


def test_history_favorite_filter(tmp_data_dir):
    _make_job(tmp_data_dir, "job1", favorite=True)
    _make_job(tmp_data_dir, "job2", favorite=False)
    res = client.get("/history?favorite=true")
    result = res.json()
    assert len(result) == 1
    assert result[0]["job_id"] == "job1"


def test_history_sort_oldest(tmp_data_dir):
    _make_job(tmp_data_dir, "job1", created_at="2026-01-01T00:00:00")
    _make_job(tmp_data_dir, "job2", created_at="2026-06-01T00:00:00")
    res = client.get("/history?sort=oldest")
    ids = [i["job_id"] for i in res.json()]
    assert ids == ["job1", "job2"]
