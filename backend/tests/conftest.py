# real mode(USE_MOCK_MODE=false) 테스트 공통 픽스처
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path):
    # DATA_DIR을 tmp_path로 리다이렉트 — 실제 data/jobs/ 건드리지 않음
    # from services.storage import DATA_DIR 형태로 바인딩된 이름도 모두 패치
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    with patch("services.storage.DATA_DIR", jobs_dir), \
         patch("routers.generate.DATA_DIR", jobs_dir), \
         patch("routers.jobs.DATA_DIR", jobs_dir), \
         patch("routers.analytics.DATA_DIR", jobs_dir), \
         patch("services.pipeline.DATA_DIR", jobs_dir):
        yield jobs_dir
