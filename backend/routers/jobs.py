# 완료된 job 조회 및 개별 조작 라우터 (real mode)
#
# 엔드포인트:
#   GET    /result/{job_id}/prd.md  — PRD 마크다운 파일 다운로드
#   GET    /result/{job_id}         — PRD·loop_history·events JSON 반환 (파이프라인 완료 후)
#   PATCH  /jobs/{job_id}/favorite  — 즐겨찾기 토글
#   POST   /jobs/{job_id}/stop      — 실행 중 파이프라인 중단 (task.cancel → CancelledError)
#   DELETE /jobs/{job_id}           — 소프트 삭제 (meta.json의 deleted 플래그만 변경, 파일 보존)
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.pipeline import running_jobs
from services.storage import DATA_DIR, read_meta, write_meta

router = APIRouter()


@router.get("/result/{job_id}/prd.md")
# prd.md 파일을 첨부 형식(attachment)으로 반환
async def download_prd(job_id: str):
    prd_path = DATA_DIR / job_id / "prd.md"
    if not prd_path.exists():
        raise HTTPException(status_code=404, detail="PRD not found")
    return FileResponse(prd_path, media_type="text/markdown", filename=f"prd_{job_id}.md")


@router.get("/result/{job_id}")
async def result(job_id: str):
    """파이프라인 완료 전 요청 시 result.json 없으므로 404."""
    job_dir = DATA_DIR / job_id
    result_path = job_dir / "result.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Job not found or not yet complete")
    data = json.loads(result_path.read_text(encoding="utf-8"))
    return {
        "prd": data.get("prd", ""),
        "loop_history": data.get("loop_history", []),
        "events": data.get("events", []),
    }


@router.patch("/jobs/{job_id}/favorite")
# meta.json의 favorite 필드 갱신
async def toggle_favorite(job_id: str, body: dict):
    favorite = body.get("favorite", False)
    meta = read_meta(job_id)
    meta["favorite"] = favorite
    write_meta(job_id, meta)
    return {"favorite": favorite}


@router.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    """task.cancel() → pipeline.py의 CancelledError 핸들러가 status를 'stopped'로 갱신."""
    task = running_jobs.get(job_id)
    if task and not task.done():
        task.cancel()
    return {"stopped": True}


@router.delete("/jobs/{job_id}")
# meta.json의 deleted 플래그를 true로 설정 (물리 삭제 없음)
async def delete_job(job_id: str):
    meta = read_meta(job_id)
    meta["deleted"] = True
    write_meta(job_id, meta)
    return {"deleted": True}
