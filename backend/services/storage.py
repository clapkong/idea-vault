# real mode 파일 I/O 레이어 — data/jobs/ 기반 job 영속화
# USE_MOCK_MODE 상수도 여기서 관리 (main.py에서 분기 판단용)
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()  # main.py가 config.py보다 storage.py를 먼저 import하므로 여기서 직접 로드

# .env의 USE_MOCK_MODE 값으로 결정; 기본값 true (API 키 없이도 앱 실행 가능)
USE_MOCK_MODE = os.getenv("USE_MOCK_MODE", "true").lower() == "true"

# 프로젝트 루트/data/jobs/{job_id}/ — real 모드 런타임 데이터 (.gitignore 대상)
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "jobs"


def read_meta(job_id: str) -> dict:
    """data/jobs/{job_id}/meta.json 읽기. 없으면 404."""
    path = DATA_DIR / job_id / "meta.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(path.read_text(encoding="utf-8"))


def write_meta(job_id: str, meta: dict) -> None:
    """data/jobs/{job_id}/meta.json 덮어쓰기."""
    path = DATA_DIR / job_id / "meta.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_title(job_dir: Path) -> str:
    """result.json의 prd 필드 첫 번째 '# ' 줄에서 제목 추출. PRD 미완성이면 빈 문자열 반환."""
    result_path = job_dir / "result.json"
    if not result_path.exists():
        return ""
    try:
        prd = json.loads(result_path.read_text(encoding="utf-8")).get("prd", "")
        for line in prd.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except Exception:
        pass
    return ""


def load_history() -> list[dict]:
    """data/jobs/ 전체 스캔 → meta.json 기반 history 항목 구성, created_at 내림차순.
    DB 없이 파일 시스템만으로 목록을 제공하는 방식이므로 job 수가 많아지면 느려질 수 있음.
    """
    if not DATA_DIR.exists():
        return []

    items = []
    for job_dir in DATA_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        meta_path = job_dir / "meta.json"
        if not meta_path.exists():
            continue

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        input_preview = ""
        input_path = job_dir / "input.txt"
        if input_path.exists():
            input_preview = input_path.read_text(encoding="utf-8")

        items.append({
            "job_id": meta.get("job_id", job_dir.name),
            "created_at": meta.get("created_at", ""),
            "title": extract_title(job_dir),
            "input_preview": input_preview,
            "favorite": meta.get("favorite", False),
            "deleted": meta.get("deleted", False),
            "duration_sec": meta.get("duration_sec", 0),
            "status": meta.get("status", ""),
            "tokens": meta.get("tokens", 0),
            "cost": meta.get("cost", 0.0),
        })

    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items
