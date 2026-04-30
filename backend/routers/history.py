# GET /history — job 목록 조회 (real mode)
#
# storage.load_history()로 data/jobs/ 전체 스캔 후 삭제·검색·즐겨찾기·정렬 필터 적용해 반환.
# mock 모드에서는 routers/mock.py가 이 함수에 위임.
from fastapi import APIRouter, Query

from services.storage import load_history

router = APIRouter()


@router.get("/history")
# 삭제되지 않은 job 목록 반환 — 검색·정렬·즐겨찾기 필터 적용
async def history(
    search: str = "",
    sort: str = "newest",
    favorite: bool | None = Query(default=None),
):
    items = [i for i in load_history() if not i.get("deleted", False)]
    if search:
        q = search.lower()
        items = [i for i in items if
                 q in (i.get("title") or "").lower() or
                 q in (i.get("input_preview") or "").lower()]
    if favorite is not None:
        items = [i for i in items if i.get("favorite", False) == favorite]
    if sort == "oldest":
        items = list(reversed(items))  # load_history()는 이미 newest 기준 정렬
    return items
