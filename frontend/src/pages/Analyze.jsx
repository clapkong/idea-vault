// 실시간 에이전트 채팅 UI — SSE 이벤트 수신, 세션 중단 지원
import { useEffect, useRef, useState } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import ChatBubble from '../components/ChatBubble'
import './Analyze.css'

// 분석 페이지 — 에이전트 파이프라인 진행 상황을 채팅 버블로 표시
export default function Analyze() {
  // useParams: URL의 :jobId 파라미터 추출
  const { jobId } = useParams()
  // useLocation: 이전 페이지(Home)가 navigate 시 state로 넘긴 idea 텍스트 접근
  const location = useLocation()
  const idea = location.state?.idea || ''

  // 채팅 버블 목록 — lazy init: idea 있으면 user 버블로 시작
  const [messages, setMessages] = useState(() => {
    if (!idea) return []
    return [{ id: 'user-msg', role: 'user', content: idea }]
  })
  // 세션 상태 ('connecting' | 'running' | 'done' | 'stopped' | 'error')
  const [sessionStatus, setSessionStatus] = useState('connecting')
  // useRef: 렌더링 없이 값·DOM 노드 보관 — 자동 스크롤 대상 DOM 노드
  const chatEndRef = useRef(null)
  // EventSource 인스턴스 — 언마운트·중단 시 close() 호출용
  const esRef = useRef(null)
  // 에이전트명 → 버블 id 매핑 — agent_done 시 해당 버블 찾기용
  const agentBubblesRef = useRef({})
  // 첫 SSE 이벤트 수신 여부 — connecting → running 전환 트리거
  const firstEventRef = useRef(false)

  // 브라우저 기본 단축키(ctrl+s 등) 차단 — SSE 수신 중 의도치 않은 페이지 이탈 방지
  useEffect(() => {
    function handleKeyDown(e) {
      // Prevent browser shortcuts (ctrl+s, ctrl+p, etc.) from interfering
      if (e.ctrlKey || e.metaKey) {
        const blocked = ['s', 'p', 'r', 'u', 'd', 'f', 'g', 'j', 'k', 'l']
        if (blocked.includes(e.key.toLowerCase())) {
          e.preventDefault()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // EventSource: 서버와 단방향 SSE 연결 — jobId 기반 스트림 구독, 언마운트 시 자동 close
  useEffect(() => {
    const es = new EventSource(`/stream/${jobId}`)
    esRef.current = es

    es.onmessage = (event) => {
      if (!firstEventRef.current) {
        firstEventRef.current = true
        setSessionStatus('running')
      }
      try {
        const data = JSON.parse(event.data)
        handleSSE(data)
      } catch {
        // ignore parse errors
      }
    }

    es.onerror = () => {
      if (sessionStatus === 'connecting') {
        setSessionStatus('error')
      }
      es.close()
    }

    return () => {
      es.close()
    }
  }, [jobId])

  // SSE 이벤트 타입별 메시지 상태 업데이트
  function handleSSE(data) {
    if (data.type === 'agent_start') {
      const id = `${data.agent}-${Date.now()}`
      agentBubblesRef.current[data.agent] = id
      setMessages(prev => [...prev, {
        id,
        role: 'agent',
        agent: data.agent,
        timestamp: data.timestamp,
        loading: true,
        progressMessage: '',
        content: '',
      }])
    } else if (data.type === 'agent_progress') {
      const id = agentBubblesRef.current[data.agent]
      setMessages(prev => prev.map(m =>
        m.id === id ? { ...m, progressMessage: data.message } : m
      ))
    } else if (data.type === 'agent_done') {
      const id = agentBubblesRef.current[data.agent]
      setMessages(prev => prev.map(m =>
        m.id === id
          ? { ...m, loading: false, content: data.output || '', tokens: data.tokens }
          : m
      ))
    } else if (data.type === 'done') {
      setSessionStatus('done')
      if (esRef.current) esRef.current.close()
    }
  }

  // 메시지 추가 시 채팅 맨 아래로 자동 스크롤 — scrollIntoView: 지정 DOM 노드를 뷰포트에 표시
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 세션 중단 — API 호출 후 SSE 연결 종료
  async function handleStop() {
    try {
      await fetch(`/jobs/${jobId}/stop`, { method: 'POST' })
    } catch {
      // ignore
    }
    if (esRef.current) esRef.current.close()
    setSessionStatus('stopped')
  }

  // prd_writer가 여러 번 등장하면 마지막 것만 표시
  const lastPrdIdx = messages.reduce((acc, m, i) => m.agent === 'prd_writer' ? i : acc, -1)
  const displayMessages = messages.filter((m, i) => m.agent !== 'prd_writer' || i === lastPrdIdx)

  // 세션 상태별 안내 문구 반환
  function getStatusMessage() {
    if (sessionStatus === 'stopped') return '세션이 사용자의 요청으로 종료되었습니다.'
    if (sessionStatus === 'error') return '세션이 에러로 인해 종료되었습니다.'
    if (sessionStatus === 'done') return 'PRD가 완성되었습니다!'
    return null
  }

  return (
    <div className="analyze-page">
      <div className="chat-area">
        <div className="chat-messages">
          {/* 연결 중 안내 */}
          {sessionStatus === 'connecting' && (
            <div className="connecting-msg">AI 에이전트에 연결 중...</div>
          )}
          {/* 채팅 버블 목록 */}
          {displayMessages.map(msg => (
            <ChatBubble key={msg.id} message={msg} jobId={jobId} />
          ))}
          {/* 세션 종료 안내 */}
          {getStatusMessage() && (
            <div className="session-status-msg">{getStatusMessage()}</div>
          )}
          <div ref={chatEndRef} />
        </div>
      </div>

      {/* running/connecting 중에만 멈추기 버튼 표시 */}
      {(sessionStatus === 'running' || sessionStatus === 'connecting') && (
        <div className="stop-bar">
          <button className="btn-stop" onClick={handleStop}>세션 멈추기</button>
        </div>
      )}
    </div>
  )
}
