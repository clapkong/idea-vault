// 토큰 사용량 통계 대시보드 — 기간 필터, 파이·막대 차트, CSV 내보내기
import { useEffect, useState, useMemo } from 'react'
import { getAnalytics } from '../api/client'
import './Analytics.css'

// 기간 필터 탭 레이블 목록
const RANGES = ['오늘', '7일', '30일', '전체']
// 레이블 → API 쿼리 파라미터 매핑
const RANGE_PARAMS = { '오늘': 'today', '7일': '7days', '30일': '30days', '전체': 'all' }

// 모델명 → 차트 색상 매핑
const MODEL_COLORS = {
  'claude-sonnet': '#8B6F47',
  'claude-haiku': '#A68A64',
  'sonnet': '#8B6F47',
  'haiku': '#A68A64',
}

// 모델명 부분 일치로 차트 색상 반환 (매핑 없으면 회색)
function getModelColor(model) {
  const lower = (model || '').toLowerCase()
  for (const key of Object.keys(MODEL_COLORS)) {
    if (lower.includes(key)) return MODEL_COLORS[key]
  }
  return '#bbb'
}

// 모델별 토큰 비율 파이 차트 — hover 시 슬라이스별 툴팁
function PieChart({ data }) {
  // hover 중인 슬라이스 위치·데이터
  const [tooltip, setTooltip] = useState(null)
  if (!data || data.length === 0) return <p className="chart-empty">데이터 없음</p>
  const total = data.reduce((s, d) => s + d.value, 0)
  let cumAngle = 0
  const slices = data.map(d => {
    const angle = (d.value / total) * 360
    const start = cumAngle
    cumAngle += angle
    return { ...d, start, angle }
  })

  // 극좌표 → SVG XY 좌표 변환 (슬라이스 꼭짓점 계산용)
  function polarToXY(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

  // 파이 슬라이스 SVG path 문자열 생성
  function slicePath(cx, cy, r, startAngle, sweepAngle) {
    if (sweepAngle >= 360) {
      return `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.001} ${cy - r} Z`
    }
    const start = polarToXY(cx, cy, r, startAngle)
    const end = polarToXY(cx, cy, r, startAngle + sweepAngle)
    const large = sweepAngle > 180 ? 1 : 0
    return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y} Z`
  }

  return (
    <div className="pie-wrap" style={{ position: 'relative' }}>
      <svg viewBox="0 0 200 200" className="pie-svg"
        onMouseLeave={() => setTooltip(null)}
      >
        <circle cx="100" cy="100" r="90" fill="var(--background)" />
        <g className="pie-slices">
          {/* 파이 슬라이스 목록 */}
          {slices.map((s, i) => (
            <path
              key={i}
              d={slicePath(100, 100, 90, s.start, s.angle)}
              fill={getModelColor(s.label)}
              style={{ cursor: 'pointer' }}
              onMouseEnter={e => {
                const rect = e.currentTarget.closest('.pie-wrap').getBoundingClientRect()
                setTooltip({ slice: s, x: e.clientX - rect.left, y: e.clientY - rect.top })
              }}
              onMouseMove={e => {
                const rect = e.currentTarget.closest('.pie-wrap').getBoundingClientRect()
                setTooltip(prev => prev ? { ...prev, x: e.clientX - rect.left, y: e.clientY - rect.top } : null)
              }}
            />
          ))}
        </g>
      </svg>
      {/* 색상 범례 */}
      <div className="pie-legend">
        {slices.map((s, i) => (
          <div key={i} className="legend-item">
            <span className="legend-dot" style={{ background: getModelColor(s.label) }} />
            <span className="legend-label">{s.label}</span>
            <span className="legend-pct">{((s.value / total) * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
      {/* hover 툴팁 */}
      {tooltip && (
        <div style={{
          position: 'absolute',
          left: tooltip.x + 10,
          top: tooltip.y - 52,
          background: 'var(--text)',
          color: 'white',
          borderRadius: 6,
          padding: '5px 10px',
          fontSize: 11,
          pointerEvents: 'none',
          whiteSpace: 'nowrap',
          opacity: 0.88,
          zIndex: 10,
          lineHeight: 1.6,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700 }}>
            <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 1, background: getModelColor(tooltip.slice.label), flexShrink: 0 }} />
            {tooltip.slice.label}
          </div>
          <div style={{ paddingLeft: 14 }}>{tooltip.slice.value.toLocaleString()} tokens</div>
        </div>
      )}
    </div>
  )
}

// 날짜별 토큰 적층 막대 차트 — hover 시 모델 분포 툴팁
function ColumnChart({ data }) {
  // hover 중인 바 인덱스
  const [hovered, setHovered] = useState(null)
  if (!data || data.length === 0) return <p className="chart-empty">데이터 없음</p>

  const maxVal = Math.max(...data.map(d => d.total), 1)
  const magnitude = Math.pow(10, Math.floor(Math.log10(maxVal)))
  const norm = maxVal / magnitude
  const niceMultiple = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10
  const niceMax = niceMultiple * magnitude
  const Y_TICKS = 4
  const ticks = Array.from({ length: Y_TICKS + 1 }, (_, i) => (niceMax / Y_TICKS) * i)

  const SVG_W = 500, SVG_H = 300
  const ML = 52, MR = 12, MT = 16, MB = 40
  const CW = SVG_W - ML - MR
  const CH = SVG_H - MT - MB
  const barW = Math.max(4, Math.min(32, (CW / data.length) * 0.55))

  // 숫자 천 단위 포맷
  function fmt(v) {
    return v.toLocaleString()
  }

  return (
    <svg
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
    >
      {/* Y축 그리드 라인 + 레이블 */}
      {ticks.map((tick, i) => {
        const y = MT + CH - (tick / niceMax) * CH
        return (
          <g key={i}>
            <line x1={ML} y1={y} x2={ML + CW} y2={y}
              stroke="var(--border)" strokeWidth={i === 0 ? 1 : 0.5}
              strokeDasharray={i === 0 ? '' : '4,3'} />
            <text x={ML - 6} y={y + 3.5} textAnchor="end" fontSize={10} fill="var(--text-muted)">
              {fmt(tick)}
            </text>
          </g>
        )
      })}

      <line x1={ML} y1={MT} x2={ML} y2={MT + CH} stroke="var(--border)" strokeWidth={1} />

      {/* 날짜별 스택 바 + hover 툴팁 */}
      {data.map((d, i) => {
        const cx = ML + (i + 0.5) * (CW / data.length)
        const isHov = hovered === i

        const segRects = []
        let stackY = MT + CH
        for (const seg of d.segments) {
          const h = Math.max(1, (seg.value / niceMax) * CH)
          const y = stackY - h
          stackY = y
          segRects.push({ ...seg, y, h })
        }
        const topY = stackY

        const hasMult = d.segments.length > 1
        const tipLines = hasMult
          ? [...d.segments.map(seg => ({ text: `${seg.model}: ${fmt(seg.value)}`, bold: false, model: seg.model })), { text: `합계: ${fmt(d.total)}`, bold: true, model: null }]
          : [{ text: fmt(d.total), bold: true, model: null }]
        const lineH = 14
        const padX = 10, padY = 6
        const tipW = Math.max(...tipLines.map(l => l.text.length * 6 + (l.model ? 12 : 0))) + padX * 2
        const tipH = tipLines.length * lineH + padY * 2
        const tipX = Math.min(Math.max(cx - tipW / 2, ML), ML + CW - tipW)
        const tipTopY = topY - tipH - 6

        return (
          <g key={i} onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
            {/* 모델별 세그먼트 */}
            {segRects.map((seg, si) => (
              <rect
                key={si}
                x={cx - barW / 2} y={seg.y} width={barW} height={seg.h}
                fill={isHov ? 'var(--secondary)' : getModelColor(seg.model)}
                rx={si === segRects.length - 1 ? 2 : 0}
                style={{ transformBox: 'fill-box', transformOrigin: 'bottom', animation: `bar-rise 0.45s ease ${i * 0.04}s both` }}
              />
            ))}
            <text x={cx} y={MT + CH + 14} textAnchor="middle" fontSize={9} fill="var(--text-muted)">
              {d.label.slice(5)}
            </text>
            {/* hover 툴팁 */}
            {isHov && (
              <g>
                <rect x={tipX} y={tipTopY} width={tipW} height={tipH} rx={4}
                  fill="var(--text)" opacity={0.85} />
                {tipLines.map((line, li) => (
                  <g key={li}>
                    {line.model && (
                      <rect
                        x={tipX + padX}
                        y={tipTopY + padY + li * lineH + 2}
                        width={8} height={8} rx={1}
                        fill={getModelColor(line.model)}
                      />
                    )}
                    <text
                      x={tipX + padX + (line.model ? 12 : 0)}
                      y={tipTopY + padY + li * lineH + 10}
                      fontSize={10} fill="white" fontWeight={line.bold ? '700' : '400'}>
                      {line.text}
                    </text>
                  </g>
                ))}
              </g>
            )}
          </g>
        )
      })}
    </svg>
  )
}

// 수평 바 차트 — 에이전트별 토큰 비교
function BarChart({ data }) {
  if (!data || data.length === 0) return <p className="chart-empty">데이터 없음</p>
  const maxVal = Math.max(...data.map(d => d.value), 1)
  return (
    <div className="bar-chart">
      {/* 바 행 목록 */}
      {data.map((d, i) => (
        <div key={i} className="bar-row">
          <span className="bar-label">{d.label}</span>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{
                width: `${(d.value / maxVal) * 100}%`,
                background: getModelColor(d.model),
              }}
            />
          </div>
          <span className="bar-value">{d.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

// 메인 대시보드 컴포넌트
export default function Analytics() {
  // 선택된 기간 필터
  const [range, setRange] = useState('전체')
  // API에서 받아온 원본 데이터 행
  const [rows, setRows] = useState([])
  // 차트 모드 (model | date)
  const [chartMode, setChartMode] = useState('model')
  // 데이터 로딩 상태
  const [loading, setLoading] = useState(false)

  // range 변경 시 analytics API 재호출
  useEffect(() => {
    setLoading(true)
    getAnalytics(RANGE_PARAMS[range])
      .then(data => {
        setRows(Array.isArray(data) ? data : (data.data || []))
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [range])

  // 총 세션 수·토큰 수 집계 — useMemo: rows 바뀔 때만 재계산, 매 렌더마다 집계 반복 방지
  const summary = useMemo(() => {
    const totalTokens = rows.reduce((s, r) => s + (r.tokens || 0), 0)
    const uniqueJobs = new Set(rows.map(r => r.job_id)).size
    return { count: uniqueJobs, tokens: totalTokens }
  }, [rows])

  // 모델별 토큰 합계 집계 (파이 차트용)
  const modelChartData = useMemo(() => {
    const acc = {}
    rows.forEach(r => {
      const m = r.model || 'unknown'
      acc[m] = (acc[m] || 0) + (r.tokens || 0)
    })
    return Object.entries(acc).map(([label, value]) => ({ label, value }))
  }, [rows])

  // 날짜별·모델별 토큰 집계 (스택 막대 차트용)
  const dateChartData = useMemo(() => {
    const acc = {}
    rows.forEach(r => {
      const d = (r.date || '').slice(0, 10)
      if (!d) return
      const m = r.model || 'unknown'
      if (!acc[d]) acc[d] = {}
      acc[d][m] = (acc[d][m] || 0) + (r.tokens || 0)
    })
    return Object.entries(acc)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([label, models]) => ({
        label,
        total: Object.values(models).reduce((s, v) => s + v, 0),
        segments: Object.entries(models).map(([model, value]) => ({ model, value })),
      }))
  }, [rows])

  // CSV 생성 후 브라우저 다운로드 트리거 — Blob → 임시 URL → <a> 클릭
  function handleCSV() {
    // TODO(backend): serve this CSV directly from FastAPI via pandas for server-side aggregation.
    const header = ['날짜', 'job_id', '제목', '모델', '토큰']
    const csvRows = rows.map(r => [
      r.date || '', r.job_id || '', r.title || '', r.model || '', r.tokens || 0
    ])
    const csv = [header, ...csvRows].map(r => r.join(',')).join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'analytics.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="analytics-page">
      <h2 className="analytics-title">토큰 사용량 통계</h2>

      <div className="analytics-main">
        <div className="analytics-left">
          {/* 기간 필터 버튼 */}
          <div className="range-btns">
            {RANGES.map(r => (
              <button
                key={r}
                className={`range-btn ${range === r ? 'active' : ''}`}
                onClick={() => setRange(r)}
              >
                {r}
              </button>
            ))}
          </div>
          <div className="summary-cards">
            <div className="summary-card">
              <span className="summary-label">총 세션</span>
              <span className="summary-value">{summary.count}개</span>
            </div>
            <div className="summary-card">
              <span className="summary-label">총 토큰</span>
              <span className="summary-value">{summary.tokens.toLocaleString()}</span>
            </div>
          </div>
          <div className="analytics-table-area">
            {/* 로딩 중 / 데이터 테이블 */}
            {loading ? (
              <div className="table-loading">불러오는 중...</div>
            ) : (
              <div className="table-scroll">
                <table className="analytics-table">
                  <thead>
                    <tr>
                      <th>날짜</th>
                      <th>제목</th>
                      <th>모델</th>
                      <th>토큰</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* 데이터 없음 행 */}
                    {rows.length === 0 && (
                      <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>데이터 없음</td></tr>
                    )}
                    {/* 데이터 행 목록 */}
                    {rows.map((r, i) => (
                      <tr key={i}>
                        <td>{(r.date || '').slice(0, 10)}</td>
                        <td className="title-cell">{r.title || '-'}</td>
                        <td>{r.model || '-'}</td>
                        <td>{(r.tokens || 0).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="table-footer">
              <button className="btn-csv" onClick={handleCSV}>CSV로 내보내기</button>
            </div>
          </div>
        </div>

        <div className="analytics-right">
          <div className="chart-mode-chips">
            <button
              className={`chart-chip ${chartMode === 'model' ? 'active' : ''}`}
              onClick={() => setChartMode('model')}
            >
              모델별
            </button>
            <button
              className={`chart-chip ${chartMode === 'date' ? 'active' : ''}`}
              onClick={() => setChartMode('date')}
            >
              날짜별
            </button>
          </div>
          {/* 모델별 / 날짜별 차트 전환 */}
          {chartMode === 'model' ? (
            <div key="model" className="chart-section">
              <h4 className="chart-title">모델 별 사용량</h4>
              <PieChart data={modelChartData} />
            </div>
          ) : (
            <div key="date" className="chart-section">
              <h4 className="chart-title">날짜 별 사용량</h4>
              <ColumnChart data={dateChartData} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
