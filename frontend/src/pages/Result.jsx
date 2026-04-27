// PRD 결과 페이지 — Markdown 렌더링 + 사이드 TOC + .md 다운로드
import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getResult } from '../api/client'
import './Result.css'

// Markdown에서 ## 헤딩만 추출 (사이드 TOC용, 최대 8개)
function extractH2Sections(md) {
  if (!md) return []
  const lines = md.split('\n')
  return lines
    .filter(l => /^## /.test(l))
    .map(l => l.replace(/^## /, '').trim())
    .slice(0, 8)
}

// PRD 결과 메인 컴포넌트
export default function Result() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  // PRD Markdown 원문
  const [prd, setPrd] = useState('')
  // TOC 섹션 제목 목록
  const [sections, setSections] = useState([])
  // Markdown 렌더링 영역 DOM 노드 — TOC 클릭 시 h2 탐색용
  const contentRef = useRef(null)

  // jobId 기반 PRD 데이터 로드 — 파이프라인 완료 전 요청 시 404가 올 수 있으므로 재시도
  useEffect(() => {
    let cancelled = false
    function attempt() {
      getResult(jobId)
        .then(data => {
          if (cancelled) return
          const md = data.prd || ''
          setPrd(md)
          setSections(extractH2Sections(md))
        })
        .catch(() => {
          if (!cancelled) setTimeout(attempt, 2000)
        })
    }
    attempt()
    return () => { cancelled = true }
  }, [jobId])

  // 제목 일치 h2 탐색 후 스크롤 이동 — querySelectorAll로 렌더링된 DOM 직접 접근
  function scrollToSection(title) {
    const headings = contentRef.current?.querySelectorAll('h2') || []
    for (const h of headings) {
      if (h.textContent.trim() === title) {
        h.scrollIntoView({ behavior: 'smooth', block: 'start' })
        return
      }
    }
  }

  // PRD .md 파일 다운로드 (Blob → 임시 URL → <a> 클릭)
  function handleDownload() {
    const blob = new Blob([prd], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `prd_${jobId}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="result-page">
      <div className="result-toc">
        <h3 className="toc-title">목차</h3>
        {/* TOC 섹션 목록 */}
        <ul className="toc-list">
          {sections.map((s, i) => (
            <li key={i}>
              <button className="toc-item" onClick={() => scrollToSection(s)}>{s}</button>
            </li>
          ))}
        </ul>
      </div>

      <div className="result-main">
        <div className="result-header">
          {/* navigate(-1): 브라우저 히스토리 한 단계 뒤로 */}
          <button className="btn-back" onClick={() => navigate(-1)}>← 뒤로가기</button>
          <h2 className="result-title">PRD 뷰어</h2>
          <button className="btn-download" onClick={handleDownload}>PRD 다운로드</button>
        </div>

        {/* ReactMarkdown: Markdown → HTML 렌더링 / remarkGfm: 표·체크박스 등 GitHub 확장 문법 지원 */}
        <div className="result-content" ref={contentRef}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{prd}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
