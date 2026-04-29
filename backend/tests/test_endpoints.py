# real mode(USE_MOCK_MODE=false) 라우터 통합 테스트
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_ready():
    # 외부 네트워크 호출 차단 — CI 환경에서 실제 OpenRouter/Tavily 요청 방지
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    with patch("main.requests.get", return_value=mock_ok):
        res = client.get("/ready")
    assert res.status_code == 200


def test_generate_returns_job_id():
    # create_task mock → run_pipeline 미실행 — OpenRouter/Tavily 호출 없음, 토큰 미소비
    with patch("routers.generate.asyncio.create_task"):
        res = client.post("/generate", json={"user_input": "테스트 아이디어"})
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "processing"


def test_result_not_found():
    # tmp_data_dir에 해당 job 없음 → storage.read_meta가 404 반환
    res = client.get("/result/nonexistent")
    assert res.status_code == 404


def test_history_returns_list():
    # tmp_data_dir은 비어 있으므로 빈 리스트 반환이 정상
    res = client.get("/history")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
