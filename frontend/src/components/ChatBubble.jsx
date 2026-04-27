import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './ChatBubble.css'

const AGENT_LABELS = {
  planner: 'Planner',
  researcher: 'Researcher',
  analyst: 'Analyst',
  critic: 'Critic',
  writer: 'Writer',
  gate: 'Gate',
  prd_writer: 'PRD Writer',
  user: 'User',
}

const AGENT_ICON_MAP = {
  analyst: 'critic', // fallback to critic icon if analyst.png not available
}

function LoadingDots() {
  return (
    <span className="loading-dots">
      <span className="dot" />
      <span className="dot" />
      <span className="dot" />
      <span className="dot empty" />
      <span className="dot empty" />
      <span className="dot empty" />
    </span>
  )
}

function formatTime(ts) {
  if (!ts) return ''
  if (/^\d{2}:\d{2}:\d{2}$/.test(ts)) {
    const [h, m] = ts.split(':')
    const hour = parseInt(h, 10)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const h12 = hour % 12 || 12
    return `${h12}:${m} ${ampm}`
  }
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  } catch {
    return ts
  }
}

export default function ChatBubble({ message, jobId }) {
  const navigate = useNavigate()
  const { role, agent, content, timestamp, tokens, loading, progressMessage } = message
  const isUser = role === 'user'
  const label = isUser ? 'User' : (AGENT_LABELS[agent] || agent)
  const iconAgent = AGENT_ICON_MAP[agent] || agent
  const iconSrc = isUser ? '/agents/user.png' : `/agents/${iconAgent}.png`

  return (
    <div className={`chat-bubble-row ${isUser ? 'user-row' : 'agent-row'}`}>
      {!isUser && (
        <div className="agent-avatar">
          <img src={iconSrc} alt={label} onError={e => { e.target.style.display = 'none' }} />
        </div>
      )}
      <div className="bubble-wrapper">
        {!isUser && <span className="bubble-label">{label}</span>}
        <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-agent'} ${loading ? 'bubble-loading' : ''}`}>
          {loading ? (
            <div className="bubble-loading-content">
              <LoadingDots />
              {progressMessage && <span className="progress-msg">{progressMessage}</span>}
            </div>
          ) : agent === 'prd_writer' && jobId ? (
            <button className="prd-view-btn" onClick={() => navigate(`/result/${jobId}`)}>
              IdeaVault가 만들어준 나만의 PRD 보기!
            </button>
          ) : isUser ? (
            <pre className="bubble-text">{content}</pre>
          ) : (
            <div className="bubble-text bubble-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
        </div>
        {!isUser && (timestamp || typeof tokens === 'number') && (
          <div className="bubble-meta">
            {timestamp && <span>{formatTime(timestamp)}</span>}
            {typeof tokens === 'number' && <span>{tokens.toLocaleString()} tokens</span>}
          </div>
        )}
      </div>
      {isUser && (
        <div className="agent-avatar">
          <img src="/agents/user.png" alt="User" onError={e => { e.target.style.display = 'none' }} />
        </div>
      )}
    </div>
  )
}
