import { useEffect, useRef, useState } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import ChatBubble from '../components/ChatBubble'
import './Analyze.css'

export default function Analyze() {
  const { jobId } = useParams()
  const location = useLocation()
  const idea = location.state?.idea || ''

  const [messages, setMessages] = useState(() => {
    if (!idea) return []
    return [{ id: 'user-msg', role: 'user', content: idea }]
  })
  const [sessionStatus, setSessionStatus] = useState('connecting') // 'connecting' | 'running' | 'done' | 'stopped' | 'error'
  const chatEndRef = useRef(null)
  const esRef = useRef(null)
  const agentBubblesRef = useRef({})
  const firstEventRef = useRef(false)

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

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
          {sessionStatus === 'connecting' && (
            <div className="connecting-msg">AI 에이전트에 연결 중...</div>
          )}
          {displayMessages.map(msg => (
            <ChatBubble key={msg.id} message={msg} jobId={jobId} />
          ))}
          {getStatusMessage() && (
            <div className="session-status-msg">{getStatusMessage()}</div>
          )}
          <div ref={chatEndRef} />
        </div>

      </div>

      {(sessionStatus === 'running' || sessionStatus === 'connecting') && (
        <div className="stop-bar">
          <button className="btn-stop" onClick={handleStop}>세션 멈추기</button>
        </div>
      )}
    </div>
  )
}
