import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ChatBubble from '../components/ChatBubble'
import './History.css'

function formatDate(str) {
  if (!str) return ''
  const d = new Date(str)
  return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' })
}

function buildChatFromResult(data, inputPreview) {
  const msgs = []
  if (inputPreview) msgs.push({ id: 'user', role: 'user', content: inputPreview })

  // Use loop_history if populated, otherwise reconstruct from events
  const lh = data.loop_history || []
  if (lh.length > 0) {
    lh.forEach((entry, i) => {
      if (entry.agent && entry.output) {
        msgs.push({
          id: `lh-${i}`,
          role: 'agent',
          agent: entry.agent,
          content: entry.output,
          timestamp: entry.timestamp,
          tokens: entry.tokens,
        })
      }
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
  return msgs
}

function HeartIcon({ filled }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  )
}

export default function History() {
  const [jobs, setJobs] = useState([])
  const [filtered, setFiltered] = useState([])
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('newest')
  const [favOnly, setFavOnly] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [loadingChat, setLoadingChat] = useState(false)
  const navigate = useNavigate()
  const chatEndRef = useRef(null)

  useEffect(() => {
    fetch('/history')
      .then(r => r.json())
      .then(data => {
        setJobs(data)
        if (data.length > 0) selectJob(data[0].job_id, data[0].input_preview)
      })
      .catch(() => {})
  }, [])

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

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  function selectJob(jobId, inputPreview) {
    setSelectedId(jobId)
    setLoadingChat(true)
    setChatMessages([])
    fetch(`/result/${jobId}`)
      .then(r => r.json())
      .then(data => {
        setChatMessages(buildChatFromResult(data, inputPreview))
      })
      .catch(() => setChatMessages([]))
      .finally(() => setLoadingChat(false))
  }

  function handleFavorite(e, jobId, current) {
    e.stopPropagation()
    fetch(`/jobs/${jobId}/favorite`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ favorite: !current }),
    })
      .then(r => r.json())
      .then(data => {
        setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, favorite: data.favorite } : j))
      })
      .catch(() => {})
  }

  function handleDelete(e, jobId) {
    e.stopPropagation()
    if (!window.confirm('정말 이 항목을 삭제하시겠습니까?')) return
    fetch(`/jobs/${jobId}`, { method: 'DELETE' })
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
          {filtered.length === 0 && <p className="empty-list">항목이 없습니다.</p>}
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
              <div className="job-card-date">{formatDate(job.created_at)}</div>
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
        {loadingChat && <div className="chat-loading">불러오는 중...</div>}
        {!loadingChat && selectedId && (
          <>
            <div className="chat-messages-history">
              {chatMessages.map(msg => <ChatBubble key={msg.id} message={msg} />)}
              <div ref={chatEndRef} />
            </div>
            <div className="history-chat-footer">
              <button className="btn-primary" onClick={() => navigate(`/result/${selectedId}`)}>
                완성된 PRD 보기
              </button>
            </div>
          </>
        )}
        {!loadingChat && !selectedId && (
          <div className="no-selection">히스토리 항목을 선택하세요.</div>
        )}
      </div>
    </div>
  )
}
