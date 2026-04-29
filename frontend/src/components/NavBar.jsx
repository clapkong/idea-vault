// 상단 네비게이션 바 — 로고 + 페이지 링크
import { NavLink } from 'react-router-dom'
import './NavBar.css'

// 네비게이션 바 컴포넌트
export default function NavBar() {
  return (
    <nav className="navbar">
      <NavLink to="/" className="navbar-brand">Idea Vault</NavLink>
      {/* NavLink: 현재 경로 일치 시 isActive=true — active 클래스로 현재 탭 강조 */}
      <div className="navbar-links">
        <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'} end>
          추천 받기
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          히스토리
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          토큰 사용량 통계
        </NavLink>
      </div>
    </nav>
  )
}
