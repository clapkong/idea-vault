// 히스토리 페이지 — 좌측 세션 목록(검색·정렬·즐겨찾기·삭제) + 우측 채팅 미리보기
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ChatBubble from '../components/ChatBubble'
import { getHistory, getResult, toggleFavorite, deleteJob } from '../api/client'
import './History.css'

// 날짜 문자열 → 한국어 형식 변환 (예: 2024. 1. 15.)
function formatDate(str) {
  if (!str) return ''
  const d = new Date(str)
  return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' })
}

// 실행 시간(초) → 읽기 쉬운 문자열 (예: 2분 34초)
function formatDuration(sec) {
  if (!sec) return ''
  if (sec < 60) return `${Math.round(sec)}초`
  return `${Math.floor(sec / 60)}분 ${Math.round(sec % 60)}초`
}

// loop_history 또는 events에서 ChatBubble용 메시지 배열 생성
function buildChatFromResult(data, inputPreview) {
  const msgs = []
  if (inputPreview) msgs.push({ id: 'user', role: 'user', content: inputPreview })

  const lh = (data.loop_history || []).filter(e => e.agent && e.output)
  if (lh.length > 0) {
    lh.forEach((entry, i) => {
      msgs.push({
        id: `lh-${i}`,
        role: 'agent',
        agent: entry.agent,
        content: entry.output,
        timestamp: entry.timestamp,
        tokens: entry.tokens,
      })
    })
  } else if (data.events) {
    data.events
      .filter(e => e.type === 'agent_done' && e.output)
      .forEach((e, i) => {
        msgs.push({
          id: `ev-${i}`,
          role: 'agent',
          agent: e.agent,
          content: e.output,
          timestamp: e.timestamp,
          tokens: e.tokens,
        })
      })
  }

  // prd_writer가 여러 번 등장하면 마지막 것만 표시
  const lastPrdIdx = msgs.reduce((acc, m, i) => m.agent === 'prd_writer' ? i : acc, -1)
  return lastPrdIdx === -1
    ? msgs
    : msgs.filter((m, i) => m.agent !== 'prd_writer' || i === lastPrdIdx)
}

// 즐겨찾기 하트 아이콘 SVG
function HeartIcon({ filled }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  )
}

// 히스토리 메인 컴포넌트
export default function History() {
  // 전체 세션 목록 (API 원본)
  const [jobs, setJobs] = useState([])
  // 필터·정렬 적용된 목록
  const [filtered, setFiltered] = useState([])
  // 검색어
  const [search, setSearch] = useState('')
  // 정렬 기준 ('newest' | 'oldest')
  const [sort, setSort] = useState('newest')
  // 즐겨찾기만 보기 필터
  const [favOnly, setFavOnly] = useState(false)
  // 우측 미리보기에 표시 중인 세션 ID
  const [selectedId, setSelectedId] = useState(null)
  // 우측 채팅 미리보기 메시지 목록
  const [chatMessages, setChatMessages] = useState([])
  // 채팅 미리보기 로딩 상태
  const [loadingChat, setLoadingChat] = useState(false)
  // useNavigate: 프로그래밍 방식으로 페이지 이동 (PRD 결과 페이지)
  const navigate = useNavigate()
  // 자동 스크롤 대상 DOM 노드
  const chatEndRef = useRef(null)

  // 초기 세션 목록 로드 + 첫 항목 자동 선택
  useEffect(() => {
    getHistory()
      .then(data => {
        setJobs(data)
        if (data.length > 0) selectJob(data[0].job_id, data[0].input_preview)
      })
      .catch(() => {})
  }, [])

  // 검색어·정렬·즐겨찾기 필터 적용
  useEffect(() => {
    let result = jobs.filter(j => {
      const q = search.toLowerCase()
      const matchSearch = (j.title || '').toLowerCase().includes(q) ||
        (j.input_preview || '').toLowerCase().includes(q)
      return matchSearch && (!favOnly || j.favorite)
    })
    if (sort === 'newest') result = [...result].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    else result = [...result].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    setFiltered(result)
  }, [jobs, search, sort, favOnly])

  // 채팅 메시지 추가 시 맨 아래로 자동 스크롤
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // 세션 선택 + 채팅 미리보기 로드
  function selectJob(jobId, inputPreview) {
    setSelectedId(jobId)
    setLoadingChat(true)
    setChatMessages([])
    getResult(jobId)
      .then(data => {
        setChatMessages(buildChatFromResult(data, inputPreview))
      })
      .catch(() => setChatMessages([]))
      .finally(() => setLoadingChat(false))
  }

  // 즐겨찾기 토글 — e.stopPropagation: 부모 카드의 onClick 전파 차단
  function handleFavorite(e, jobId, current) {
    e.stopPropagation()
    toggleFavorite(jobId, !current)
      .then(data => {
        setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, favorite: data.favorite } : j))
      })
      .catch(() => {})
  }

  // 소프트 삭제 + 다음 항목 자동 선택
  function handleDelete(e, jobId) {
    e.stopPropagation()
    if (!window.confirm('정말 이 항목을 삭제하시겠습니까?')) return
    deleteJob(jobId)
      .then(() => {
        setJobs(prev => {
          const next = prev.filter(j => j.job_id !== jobId)
          if (selectedId === jobId && next.length > 0) selectJob(next[0].job_id, next[0].input_preview)
          else if (next.length === 0) { setSelectedId(null); setChatMessages([]) }
          return next
        })
      })
      .catch(() => {})
  }

  return (
    <div className="history-page">
      <div className="history-sidebar">
        <div className="sidebar-top">
          <input
            className="search-input"
            placeholder="검색..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <div className="sidebar-controls">
            <select className="sort-select" value={sort} onChange={e => setSort(e.target.value)}>
              <option value="newest">최신순</option>
              <option value="oldest">오래된순</option>
            </select>
            <button
              className={`fav-filter-btn ${favOnly ? 'active' : ''}`}
              onClick={() => setFavOnly(v => !v)}
              title="즐겨찾기만 보기"
            >
              <HeartIcon filled={favOnly} />
            </button>
          </div>
        </div>
        <div className="job-list">
          {/* 빈 목록 안내 */}
          {filtered.length === 0 && <p className="empty-list">항목이 없습니다.</p>}
          {/* 세션 카드 목록 */}
          {filtered.map(job => (
            <div
              key={job.job_id}
              className={`job-card ${selectedId === job.job_id ? 'selected' : ''}`}
              onClick={() => selectJob(job.job_id, job.input_preview)}
            >
              <div className="job-card-header">
                <span className="job-title">{job.title || '제목 없음'}</span>
                <button
                  className={`fav-btn ${job.favorite ? 'fav-active' : ''}`}
                  onClick={e => handleFavorite(e, job.job_id, job.favorite)}
                  title={job.favorite ? '즐겨찾기 해제' : '즐겨찾기'}
                >
                  <HeartIcon filled={job.favorite} />
                </button>
              </div>
              <div className="job-card-date">
                {formatDate(job.created_at)}
                {job.duration_sec > 0 && <span className="job-duration"> · {formatDuration(job.duration_sec)}</span>}
              </div>
              <div className="job-card-preview">{(job.input_preview || '').slice(0, 100)}</div>
              <div className="job-card-footer">
                <button
                  className="delete-btn"
                  onClick={e => handleDelete(e, job.job_id)}
                >
                  삭제
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="history-chat">
        {/* 채팅 로딩 중 */}
        {loadingChat && <div className="chat-loading">불러오는 중...</div>}
        {/* 채팅 미리보기 */}
        {!loadingChat && selectedId && (
          <>
            <div className="chat-messages-history">
              {chatMessages.map(msg => <ChatBubble key={msg.id} message={msg} jobId={selectedId} />)}
              <div ref={chatEndRef} />
            </div>
            <div className="history-chat-footer">
              <button className="btn-primary" onClick={() => navigate(`/result/${selectedId}`)}>
                완성된 PRD 보기
              </button>
            </div>
          </>
        )}
        {/* 항목 미선택 안내 */}
        {!loadingChat && !selectedId && (
          <div className="no-selection">히스토리 항목을 선택하세요.</div>
        )}
      </div>
    </div>
  )
}
