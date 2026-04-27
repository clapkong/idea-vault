import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Home.css'

const EXAMPLE_PROMPTS = [
  {
    label: '💼 취업 포트폴리오',
    text: '취업 포트폴리오 만들어야 해요. 백엔드 개발자 (주로 사용하는 언어: JavaSpring) 지망생이에요. 프로젝트에 취업할 때 제 역량이 최대한 부각될 수 있는 요소가 많이 있었으면 좋겠어요. 시간은 한 3주 정도 잡고 있어요',
  },
  {
    label: '🎓 캡스톤 팀 프로젝트',
    text: '소프트웨어 3학년 전공 캡스톤 수업 프로젝트인데 팀이 3명이고 한 학기 동안 해야 해요. 교수님께서 실생활과 연관된 주제를 원하세요. 팀원은 JavaScript 포함한 웹 프론트 1명, Swift 경력자 1명, 나머지 한명은 SQLD가 있고 백엔드를 공부하고 싶어해요. 디자인 하기 싫고 ML은 너무 어려워요. 투두앱 같은 뻔한 건 만들기 싫어요.',
  },
  {
    label: '🎵 음악 + 개발 입문',
    text: '저 개발 시작한 지 한 달 됐어요. 유튜브로 파이썬 기초만 봤고요. 뭔가 제가 쓸 수 있는걸 만들어보고 싶은데 뭘 만들 수 있는지도 모르겠어요. 저 음악 진짜 좋아하는데 음악이랑 개발 연결하고 싶어요. 근데 꼭 음악이 아니여도 괜찮아요. 돈 없어서 유료 API 못 써요. 2주 안에 끝내야 하고 혼자예요.',
  },
]

const MAX_LEN = 500
const MIN_LEN = 20

export default function Home() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function handleSubmit() {
    if (text.trim().length < MIN_LEN) {
      setError(`최소 ${MIN_LEN}자 이상 입력해주세요.`)
      return
    }
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: text }),
      })
      const data = await res.json()
      navigate(`/analyze/${data.job_id}`, { state: { idea: text } })
    } catch (e) {
      setError('서버에 연결할 수 없습니다. Mock API 서버가 실행 중인지 확인해주세요.')
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit()
    }
  }

  return (
    <div className="home-page">
      <div className="home-center">
        <h1 className="home-catchphrase">
          막연한 아이디어도 괜찮아요.<br />
          AI가 함께 다듬어 PRD로 만들어드립니다
        </h1>

        <div className="home-input-area">
          <textarea
            className="home-textarea"
            placeholder="어떤 프로젝트를 만들고 싶으신가요? 아이디어를 자유롭게 적어주세요."
            value={text}
            onChange={e => setText(e.target.value.slice(0, MAX_LEN))}
            onKeyDown={handleKeyDown}
            rows={6}
          />
          <div className="home-input-footer">
            <span className={`char-counter ${text.length < MIN_LEN && text.length > 0 ? 'warn' : ''}`}>
              {text.length}/{MAX_LEN}자
            </span>
            <button
              className="btn-primary"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? '처리 중...' : '추천 받기'}
            </button>
          </div>
          {error && <p className="error-msg">{error}</p>}
        </div>

        <div className="example-chips">
          <span className="chips-label">예시 아이디어</span>
          <div className="chips-row">
            {EXAMPLE_PROMPTS.map((p, i) => (
              <button
                key={i}
                className="chip"
                onClick={() => setText(p.text.slice(0, MAX_LEN))}
                title={p.text}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
