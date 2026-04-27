// 에이전트·유저 채팅 버블 공용 컴포넌트 — 에이전트별 색상·아이콘·로딩 상태·Markdown 렌더링
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './ChatBubble.css'

// 에이전트 키 → 표시 이름 매핑
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

// 에이전트별 진행 중·완료 안내 메시지
const AGENT_MESSAGES = {
  planner: { progress: '아이디어를 발굴하고 방향을 기획하고 있습니다...', done: '기획이 완료되었습니다! 결과를 확인해보세요.'},
  researcher: { progress: '관련 자료를 검색하고 있습니다...', done: '조사가 완료되었습니다! 수집한 정보를 확인해보세요.' },
  analyst: { progress: '적합성을 분석하고 있습니다...', done: '분석이 완료되었습니다! 분석 결과를 확인해보세요.' },
  critic: { progress: '아이디어의 실현 가능성과 완성도를 검증하고 있습니다...', done: '검증이 완료되었습니다! 검증 결과를 확인해보세요.' },
  gate: { progress: '아이디어를 더 발전시킬지 판단하고 있습니다...', done: '판단이 완료되었습니다.' },
  prd_writer: { progress: '최종 PRD를 작성하고 있습니다...', done: 'PRD 작성이 완료되었습니다!' },
}

const AGENT_ICON_MAP = {}

// 에이전트별 버블 레이블 색상
const AGENT_COLORS = {
  analyst: '#A8A878',
  critic: '#C08574',
  gate: '#7A95A8',
  planner: '#9B8AA6',
  prd_writer: '#C9A961',
  researcher: '#8BA888',
}

// 로딩 중 애니메이션 점 3개
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

// 타임스탬프 → 12시간제 시간 문자열 변환 (HH:MM:SS 또는 ISO 문자열 모두 처리)
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

// 채팅 버블 컴포넌트 — role에 따라 유저·에이전트 레이아웃 전환
export default function ChatBubble({ message, jobId }) {
  const navigate = useNavigate()
  const { role, agent, content, timestamp, tokens, loading, progressMessage } = message
  const isUser = role === 'user'
  const label = isUser ? 'User' : (AGENT_LABELS[agent] || agent)
  const iconAgent = AGENT_ICON_MAP[agent] || agent
  const iconSrc = isUser ? '/agents/user.png' : `/agents/${iconAgent}.png`

  return (
    <div className={`chat-bubble-row ${isUser ? 'user-row' : 'agent-row'}`}>
      {/* 에이전트 아바타 (좌측) — onError: 이미지 로드 실패 시 숨김 */}
      {!isUser && (
        <div className="agent-avatar">
          <img src={iconSrc} alt={label} onError={e => { e.target.style.display = 'none' }} />
        </div>
      )}
      <div className="bubble-wrapper">
        {/* 에이전트 이름 레이블 */}
        {!isUser && (
          <span className="bubble-label" style={{ color: AGENT_COLORS[agent] || 'var(--secondary)' }}>
            {label}
          </span>
        )}
        <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-agent'} ${loading ? 'bubble-loading' : ''}`}>
          {/* 로딩 중 — 점 애니메이션 + 진행 메시지 */}
          {loading ? (
            <div className="bubble-loading-content">
              <LoadingDots />
              <span className="progress-msg">
                {progressMessage || AGENT_MESSAGES[agent]?.progress || ''}
              </span>
            </div>
          ) : agent === 'prd_writer' && jobId ? (
            // prd_writer 완료 — PRD 결과 페이지 이동 버튼
            <div className="bubble-done-content">
              {AGENT_MESSAGES.prd_writer?.done && (
                <p className="done-msg">{AGENT_MESSAGES.prd_writer.done}</p>
              )}
              <button className="prd-view-btn" onClick={() => navigate(`/result/${jobId}`)}>
                IdeaVault가 만들어준 나만의 PRD 보기!
              </button>
            </div>
          ) : isUser ? (
            // 유저 메시지 — 줄바꿈 보존을 위해 pre 사용
            <pre className="bubble-text">{content}</pre>
          ) : (
            // 에이전트 메시지 — Markdown 렌더링
            <div className="bubble-text bubble-markdown">
              {AGENT_MESSAGES[agent]?.done && (
                <p className="done-msg">{AGENT_MESSAGES[agent].done}</p>
              )}
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
        </div>
        {/* 시간·토큰 메타 정보 */}
        {!isUser && (timestamp || tokens != null) && (
          <div className="bubble-meta">
            {timestamp && <span>{formatTime(timestamp)}</span>}
            {tokens != null && (
              typeof tokens === 'object'
                ? <span>{tokens.total.toLocaleString()} tokens (in {tokens.input.toLocaleString()} | out {tokens.output.toLocaleString()})</span>
                : <span>{tokens.toLocaleString()} tokens</span>
            )}
          </div>
        )}
      </div>
      {/* 유저 아바타 (우측) */}
      {isUser && (
        <div className="agent-avatar">
          <img src="/agents/user.png" alt="User" onError={e => { e.target.style.display = 'none' }} />
        </div>
      )}
    </div>
  )
}
