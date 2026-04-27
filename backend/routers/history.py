# GET /history — 삭제되지 않은 job 목록 반환 (real mode)
from fastapi import APIRouter

from services.storage import load_history

router = APIRouter()


@router.get("/history")
async def history():
    return [item for item in load_history() if not item.get("deleted", False)]
