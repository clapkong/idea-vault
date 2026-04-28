// 백엔드 API 호출 중앙화 — 모든 fetch/EventSource 생성은 이 파일에서만 수행
// Vite 개발 서버가 /api/* 를 localhost:8000으로 프록시하므로 baseURL 별도 설정 불필요

// POST /generate → { job_id, status }
// 아이디어 텍스트를 서버에 전달하고 파이프라인 실행을 요청
export async function generateIdea(userInput) {
  const res = await fetch('/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_input: userInput }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || '서버 오류가 발생했습니다.')
  }
  return res.json()
}

// GET /stream/{jobId} → EventSource
// SSE 연결 생성 — 반환된 EventSource를 컴포넌트에서 직접 구독·close 관리
export function createEventStream(jobId) {
  return new EventSource(`/stream/${jobId}`)
}

// POST /jobs/{jobId}/stop
// 실행 중인 파이프라인 중단 요청 — 응답값 불필요, 오류는 호출부에서 무시
export async function stopJob(jobId) {
  await fetch(`/jobs/${jobId}/stop`, { method: 'POST' })
}

// GET /result/{jobId} → { prd, loop_history, events }
// PRD 뷰어 및 히스토리 미리보기에서 사용
export async function getResult(jobId) {
  const res = await fetch(`/result/${jobId}`)
  if (!res.ok) throw new Error('결과를 불러올 수 없습니다.')
  return res.json()
}

// GET /history?search=...&sort=newest|oldest&favorite=true → Job[]
// deleted=true 항목은 서버에서 이미 제외된 상태로 반환
export async function getHistory({ search = '', sort = 'newest', favorite } = {}) {
  const params = new URLSearchParams({ sort })
  if (search) params.set('search', search)
  if (favorite !== undefined) params.set('favorite', String(favorite))
  const res = await fetch(`/history?${params}`)
  if (!res.ok) throw new Error('히스토리를 불러올 수 없습니다.')
  return res.json()
}

// PATCH /jobs/{jobId}/favorite → { favorite: bool }
// 낙관적 업데이트: 컴포넌트에서 UI를 먼저 반영하고 이 함수로 서버 동기화
export async function toggleFavorite(jobId, favorite) {
  const res = await fetch(`/jobs/${jobId}/favorite`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ favorite }),
  })
  if (!res.ok) throw new Error('즐겨찾기 변경에 실패했습니다.')
  return res.json()
}

// DELETE /jobs/{jobId} → { deleted: true }
// 소프트 삭제 — 서버는 deleted 플래그만 설정, 물리 삭제 없음
export async function deleteJob(jobId) {
  const res = await fetch(`/jobs/${jobId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('삭제에 실패했습니다.')
  return res.json()
}

// GET /ready → { openrouter: "ok"/"degraded", tavily: "ok"/"degraded" }
// 외부 서비스 접속 가능 여부 확인 — 홈 진입 시 호출
export async function getReady() {
  const res = await fetch('/ready')
  if (!res.ok) throw new Error('연결 상태를 확인할 수 없습니다.')
  return res.json()
}

// GET /analytics?range=all|today|7days|30days → { summary, data }
// range 기본값 'all' — 파라미터 없이 호출 시 전체 기간 집계
export async function getAnalytics(range = 'all') {
  const res = await fetch(`/analytics?range=${range}`)
  if (!res.ok) throw new Error('통계를 불러올 수 없습니다.')
  return res.json()
}
