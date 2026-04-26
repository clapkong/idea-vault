import { useEffect, useRef, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import ChatBubble from '../components/ChatBubble'
import './Analyze.css'

export default function Analyze() {
  const { jobId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const idea = location.state?.idea || ''

  const [messages, setMessages] = useState(() => {
    if (!idea) return []
    return [{ id: 'user-msg', role: 'user', content: idea }]
  })
  const [sessionStatus, setSessionStatus] = useState('connecting') // 'connecting' | 'running' | 'done' | 'stopped' | 'error'
  const [prdReady, setPrdReady] = useState(false)
  const chatEndRef = useRef(null)
  const esRef = useRef(null)
  const agentBubblesRef = useRef({})
  const firstEventRef = useRef(false)

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
      if (data.agent === 'prd_writer') {
        setPrdReady(true)
      }
    } else if (data.type === 'done') {
      setSessionStatus('done')
      if (esRef.current) esRef.current.close()
      setTimeout(() => navigate(`/result/${jobId}`), 1500)
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

  function getStatusMessage() {
    if (sessionStatus === 'stopped') return '세션이 사용자의 요청으로 종료되었습니다.'
    if (sessionStatus === 'error') return '세션이 에러로 인해 종료되었습니다.'
    if (sessionStatus === 'done') return 'PRD가 완성되었습니다. 결과 페이지로 이동합니다...'
    return null
  }

  return (
    <div className="analyze-page">
      <div className="chat-area">
        <div className="chat-messages">
          {sessionStatus === 'connecting' && (
            <div className="connecting-msg">AI 에이전트에 연결 중...</div>
          )}
          {messages.map(msg => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {getStatusMessage() && (
            <div className="session-status-msg">{getStatusMessage()}</div>
          )}
          <div ref={chatEndRef} />
        </div>

        {prdReady && (
          <div className="prd-ready-banner">
            <button className="btn-primary" onClick={() => navigate(`/result/${jobId}`)}>
              완성된 PRD 보기
            </button>
          </div>
        )}
      </div>

      {(sessionStatus === 'running' || sessionStatus === 'connecting') && (
        <div className="stop-bar">
          <button className="btn-stop" onClick={handleStop}>세션 멈추기</button>
        </div>
      )}
    </div>
  )
}
