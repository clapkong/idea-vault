import './ChatBubble.css'

const AGENT_LABELS = {
  planner: 'Planner',
  researcher: 'Researcher',
  critic: 'Critic',
  writer: 'Writer',
  gate: 'Gate',
  prd_writer: 'PRD Writer',
  user: 'User',
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

export default function ChatBubble({ message }) {
  const { role, agent, content, timestamp, tokens, loading, progressMessage } = message
  const isUser = role === 'user'
  const label = isUser ? 'User' : (AGENT_LABELS[agent] || agent)
  const iconSrc = isUser ? '/agents/user.png' : `/agents/${agent}.png`

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
          ) : (
            <pre className="bubble-text">{content}</pre>
          )}
        </div>
        {!isUser && (timestamp || tokens) && (
          <div className="bubble-meta">
            {timestamp && <span>{formatTime(timestamp)}</span>}
            {tokens && <span>{tokens.toLocaleString()} tokens</span>}
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
