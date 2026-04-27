// 루트 컴포넌트 — 라우팅 구조 + 전체 레이아웃 (NavBar + 페이지)
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import Home from './pages/Home'
import Analyze from './pages/Analyze'
import History from './pages/History'
import Result from './pages/Result'
import Analytics from './pages/Analytics'
import NotFound from './pages/NotFound'
import './App.css'

// 앱 루트 — NavBar + 라우팅 페이지 세로 레이아웃
function App() {
  return (
    // BrowserRouter: URL 기반 라우팅 컨텍스트 (새로고침 없이 페이지 전환)
    <BrowserRouter>
      <NavBar />
      {/* main — NavBar 아래 남은 공간 전부, 내부 스크롤 허용 */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/analyze/:jobId" element={<Analyze />} />  {/* :jobId — /generate 응답의 세션 ID */}
          <Route path="/history" element={<History />} />
          <Route path="/result/:jobId" element={<Result />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="*" element={<NotFound />} />  {/* * — 위 경로 불일치 시 404 */}
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
