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

const AGENT_MESSAGES = {
  planner: { progress: '주제를 발굴하고 있습니다...', done: '주제 발굴을 완료했습니다! 결과를 보여드릴게요.' },
  researcher: { progress: '관련 자료를 검색하고 있습니다...', done: '자료 검색을 완료했습니다! 결과를 보여드릴게요.' },
  critic: { progress: '추가로 필요한 정보를 확인하고 있습니다...', done: '추가 정보 확인을 완료했습니다!' },
  gate: { progress: '프로젝트 검증 중입니다...', done: '검증을 완료했습니다!' },
  analyst: { progress: '프로젝트 정보를 분석하고 있습니다...', done: '분석을 완료했습니다! 내부 검토 사항을 확인했어요.' },
  prd_writer: { progress: '최종 PRD를 작성하고 있습니다...', done: 'PRD 작성이 완료되었습니다!' },
}

const AGENT_ICON_MAP = {
  analyst: 'critic',
}

const AGENT_COLORS = {
  analyst: '#A8A878',
  critic: '#C08574',
  gate: '#7A95A8',
  planner: '#9B8AA6',
  prd_writer: '#C9A961',
  researcher: '#8BA888',
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
        {!isUser && (
          <span className="bubble-label" style={{ color: AGENT_COLORS[agent] || 'var(--secondary)' }}>
            {label}
          </span>
        )}
        <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-agent'} ${loading ? 'bubble-loading' : ''}`}>
          {loading ? (
            <div className="bubble-loading-content">
              <LoadingDots />
              <span className="progress-msg">
                {progressMessage || AGENT_MESSAGES[agent]?.progress || ''}
              </span>
            </div>
          ) : agent === 'prd_writer' && jobId ? (
            <div className="bubble-done-content">
              {AGENT_MESSAGES.prd_writer?.done && (
                <p className="done-msg">{AGENT_MESSAGES.prd_writer.done}</p>
              )}
              <button className="prd-view-btn" onClick={() => navigate(`/result/${jobId}`)}>
                IdeaVault가 만들어준 나만의 PRD 보기!
              </button>
            </div>
          ) : isUser ? (
            <pre className="bubble-text">{content}</pre>
          ) : (
            <div className="bubble-text bubble-markdown">
              {AGENT_MESSAGES[agent]?.done && (
                <p className="done-msg">{AGENT_MESSAGES[agent].done}</p>
              )}
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
