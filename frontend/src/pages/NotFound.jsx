// 404 폴백 페이지 — 매칭 경로 없을 때 표시, 홈 이동 버튼 제공
import { useNavigate } from 'react-router-dom'

// 404 페이지 컴포넌트
export default function NotFound() {
  const navigate = useNavigate()
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16, padding: 48 }}>
      <h2 style={{ fontSize: 20, color: 'var(--text-muted)' }}>페이지를 찾을 수 없습니다.</h2>
      <button className="btn-primary" onClick={() => navigate('/')}>홈으로 돌아가기</button>
    </div>
  )
}
