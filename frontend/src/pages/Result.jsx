import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import './Result.css'

function extractH2Sections(md) {
  if (!md) return []
  const lines = md.split('\n')
  return lines
    .filter(l => /^## /.test(l))
    .map(l => l.replace(/^## /, '').trim())
    .slice(0, 8)
}

export default function Result() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [prd, setPrd] = useState('')
  const [sections, setSections] = useState([])
  const contentRef = useRef(null)

  useEffect(() => {
    fetch(`/result/${jobId}`)
      .then(r => r.json())
      .then(data => {
        const md = data.prd || ''
        setPrd(md)
        setSections(extractH2Sections(md))
      })
      .catch(() => {})
  }, [jobId])

  function scrollToSection(title) {
    const headings = contentRef.current?.querySelectorAll('h2') || []
    for (const h of headings) {
      if (h.textContent.trim() === title) {
        h.scrollIntoView({ behavior: 'smooth', block: 'start' })
        return
      }
    }
  }

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
          <button className="btn-back" onClick={() => navigate(-1)}>← 뒤로가기</button>
          <h2 className="result-title">PRD 뷰어</h2>
          <div style={{ width: 80 }} />
        </div>

        <div className="result-content" ref={contentRef}>
          <ReactMarkdown>{prd}</ReactMarkdown>
        </div>

        <div className="result-footer">
          <button className="btn-download" onClick={handleDownload}>
            IdeaVault가 만들어준 나만의 PRD 다운로드 하기!
          </button>
        </div>
      </div>
    </div>
  )
}
