from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from services.pipeline import running_jobs

client = TestClient(app)


def test_stream_job_not_found():
    # job_queues에 없는 job_id → 404
    res = client.get("/stream/nonexistent")
    assert res.status_code == 404


def test_stop_always_returns_stopped():
    # running_jobs에 없어도 항상 stopped: true 반환
    res = client.post("/jobs/nonexistent/stop")
    assert res.status_code == 200
    assert res.json()["stopped"] is True


def test_stop_cancels_running_task(tmp_data_dir):
    with patch("routers.generate.asyncio.create_task"):
        res = client.post("/generate", json={"user_input": "test"})
    job_id = res.json()["job_id"]

    mock_task = MagicMock()
    mock_task.done.return_value = False
    running_jobs[job_id] = mock_task

    res = client.post(f"/jobs/{job_id}/stop")
    assert res.status_code == 200
    mock_task.cancel.assert_called_once()

    running_jobs.pop(job_id, None)
