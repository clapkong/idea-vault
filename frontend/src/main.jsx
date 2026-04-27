// 앱 진입점 — index.html #root에 React 트리 마운트
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// createRoot: DOM 노드에 React 트리 마운트 (React 18 방식)
// StrictMode: 개발용 사이드이펙트 감지 (프로덕션 미포함)
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
