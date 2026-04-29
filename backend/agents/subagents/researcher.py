"""
Researcher Agent  (no LLM — Tavily only)
  Input : queries (list[str])
  Output: str  — aggregated search results with URLs preserved
"""
from config import TAVILY_API_KEY


# TavilyClient lazy import — 패키지 미설치 시 호출 시점에 명확한 에러 발생
def _get_tavily():
    try:
        from tavily import TavilyClient  # type: ignore
    except ImportError as exc:
        raise ImportError("tavily-python is required: pip install tavily-python") from exc
    return TavilyClient(api_key=TAVILY_API_KEY)


# 쿼리 목록을 Tavily로 검색, URL을 보존해 하나의 문자열로 반환
def researcher_agent(queries: list) -> str:
    if not queries:
        return "검색 쿼리 없음"

    client = _get_tavily()
    blocks: list[str] = []

    for query in queries:
        try:
            resp = client.search(query=query, max_results=3)
            for r in resp.get("results", []):
                title = r.get("title", "")
                url = r.get("url", "")
                snippet = r.get("content", "")[:400]
                blocks.append(f"### {title}\nURL: {url}\n{snippet}")
        except Exception as exc:
            blocks.append(f"[검색 실패] query={query!r} | {exc}")

    return "\n\n".join(blocks) if blocks else "검색 결과 없음"
