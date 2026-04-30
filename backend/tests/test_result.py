import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_job(tmp_data_dir: Path, job_id: str = "test1234", **meta_kwargs) -> Path:
    job_dir = tmp_data_dir / job_id
    job_dir.mkdir()
    meta = {
        "job_id": job_id, "status": "done",
        "favorite": False, "deleted": False,
        "created_at": "2026-01-01T00:00:00", "tokens": 0,
        **meta_kwargs,
    }
    (job_dir / "meta.json").write_text(json.dumps(meta))
    return job_dir


def test_result_not_found():
    res = client.get("/result/nonexistent")
    assert res.status_code == 404


def test_result_found(tmp_data_dir):
    job_dir = _make_job(tmp_data_dir)
    (job_dir / "result.json").write_text(json.dumps({
        "prd": "# 테스트 PRD", "loop_history": [], "events": [], "duration_sec": 5.0,
    }))
    res = client.get("/result/test1234")
    assert res.status_code == 200
    assert res.json()["prd"] == "# 테스트 PRD"


def test_download_prd_not_found():
    res = client.get("/result/nonexistent/prd.md")
    assert res.status_code == 404


def test_download_prd(tmp_data_dir):
    job_dir = _make_job(tmp_data_dir)
    (job_dir / "prd.md").write_text("# 테스트 PRD 내용")
    res = client.get("/result/test1234/prd.md")
    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]


def test_toggle_favorite(tmp_data_dir):
    _make_job(tmp_data_dir)
    res = client.patch("/jobs/test1234/favorite", json={"favorite": True})
    assert res.status_code == 200
    assert res.json()["favorite"] is True


def test_delete_job(tmp_data_dir):
    _make_job(tmp_data_dir)
    res = client.delete("/jobs/test1234")
    assert res.status_code == 200
    assert res.json()["deleted"] is True
    meta = json.loads((tmp_data_dir / "test1234" / "meta.json").read_text())
    assert meta["deleted"] is True
