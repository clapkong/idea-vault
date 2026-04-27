import { useEffect, useState, useMemo } from 'react'
import './Analytics.css'

const RANGES = ['오늘', '7일', '30일', '전체']
const RANGE_PARAMS = { '오늘': 'today', '7일': '7days', '30일': '30days', '전체': 'all' }

const MODEL_COLORS = {
  'claude-sonnet': '#8B6F47',
  'claude-haiku': '#A68A64',
  'sonnet': '#8B6F47',
  'haiku': '#A68A64',
}

function getModelColor(model) {
  const lower = (model || '').toLowerCase()
  for (const key of Object.keys(MODEL_COLORS)) {
    if (lower.includes(key)) return MODEL_COLORS[key]
  }
  return '#bbb'
}

function PieChart({ data }) {
  if (!data || data.length === 0) return <p className="chart-empty">데이터 없음</p>
  const total = data.reduce((s, d) => s + d.value, 0)
  let cumAngle = 0
  const slices = data.map(d => {
    const angle = (d.value / total) * 360
    const start = cumAngle
    cumAngle += angle
    return { ...d, start, angle }
  })

  function polarToXY(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

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
    <div className="pie-wrap">
      <svg viewBox="0 0 200 200" className="pie-svg">
        <circle cx="100" cy="100" r="90" fill="var(--background)" />
        <g className="pie-slices">
          {slices.map((s, i) => (
            <path key={i} d={slicePath(100, 100, 90, s.start, s.angle)} fill={getModelColor(s.label)} />
          ))}
        </g>
      </svg>
      <div className="pie-legend">
        {slices.map((s, i) => (
          <div key={i} className="legend-item">
            <span className="legend-dot" style={{ background: getModelColor(s.label) }} />
            <span className="legend-label">{s.label}</span>
            <span className="legend-pct">{((s.value / total) * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ColumnChart({ data }) {
  const [hovered, setHovered] = useState(null)
  if (!data || data.length === 0) return <p className="chart-empty">데이터 없음</p>

  const maxVal = Math.max(...data.map(d => d.value), 1)
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

  function fmt(v) {
    if (v >= 10000) return `${(v / 1000).toFixed(0)}k`
    if (v >= 1000) return `${(v / 1000).toFixed(1)}k`
    return v.toLocaleString()
  }

  return (
    <svg
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
    >
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

      {data.map((d, i) => {
        const barH = Math.max(1, (d.value / niceMax) * CH)
        const cx = ML + (i + 0.5) * (CW / data.length)
        const by = MT + CH - barH
        const isHov = hovered === i
        const tipText = fmt(d.value)
        const tipW = tipText.length * 7 + 16
        const tipX = Math.min(Math.max(cx - tipW / 2, ML), ML + CW - tipW)

        return (
          <g key={i} onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
            <rect x={cx - barW / 2} y={by} width={barW} height={barH}
              fill={isHov ? 'var(--secondary)' : getModelColor(d.model)} rx={2}
              style={{ transformBox: 'fill-box', transformOrigin: 'bottom', animation: `bar-rise 0.45s ease ${i * 0.04}s both` }} />
            <text x={cx} y={MT + CH + 14} textAnchor="middle" fontSize={9} fill="var(--text-muted)">
              {d.label.slice(5)}
            </text>
            {isHov && (
              <g>
                <rect x={tipX} y={by - 26} width={tipW} height={20} rx={4}
                  fill="var(--text)" opacity={0.85} />
                <text x={tipX + tipW / 2} y={by - 12} textAnchor="middle"
                  fontSize={10} fill="white" fontWeight="600">
                  {tipText}
                </text>
              </g>
            )}
          </g>
        )
      })}
    </svg>
  )
}

function BarChart({ data }) {
  if (!data || data.length === 0) return <p className="chart-empty">데이터 없음</p>
  const maxVal = Math.max(...data.map(d => d.value), 1)
  return (
    <div className="bar-chart">
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

export default function Analytics() {
  const [range, setRange] = useState('전체')
  const [rows, setRows] = useState([])
  const [chartMode, setChartMode] = useState('model')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    const param = RANGE_PARAMS[range]
    fetch(`/analytics?range=${param}`)
      .then(r => r.json())
      .then(data => {
        // backend returns {summary, data} or flat array
        const rows = Array.isArray(data) ? data : (data.data || [])
        setRows(rows)
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [range])

  const summary = useMemo(() => {
    const totalTokens = rows.reduce((s, r) => s + (r.tokens || 0), 0)
    const totalCost = rows.reduce((s, r) => s + (r.cost || 0), 0)
    return { count: rows.length, tokens: totalTokens, cost: totalCost }
  }, [rows])

  const modelChartData = useMemo(() => {
    const acc = {}
    rows.forEach(r => {
      const m = r.model || 'unknown'
      acc[m] = (acc[m] || 0) + (r.tokens || 0)
    })
    return Object.entries(acc).map(([label, value]) => ({ label, value }))
  }, [rows])

  const dateChartData = useMemo(() => {
    const acc = {}
    rows.forEach(r => {
      const d = (r.date || '').slice(0, 10)
      if (!d) return
      acc[d] = { value: (acc[d]?.value || 0) + (r.tokens || 0), model: r.model }
    })
    return Object.entries(acc)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([label, v]) => ({ label, value: v.value, model: v.model }))
  }, [rows])

  function handleCSV() {
    const header = ['날짜', '제목', '모델', '토큰', '비용']
    const csvRows = rows.map(r => [
      r.date || '', r.title || '', r.model || '', r.tokens || 0, r.cost || 0
    ])
    const csv = [header, ...csvRows].map(r => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'analytics.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="analytics-page">
      <div className="analytics-header">
        <h2 className="analytics-title">토큰 사용량 통계</h2>
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
            <span className="summary-label">총 요청</span>
            <span className="summary-value">{summary.count}개</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">총 토큰</span>
            <span className="summary-value">{summary.tokens.toLocaleString()}</span>
          </div>
          <div className="summary-card">
            <span className="summary-label">총 비용</span>
            <span className="summary-value">${summary.cost.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="analytics-body">
        <div className="analytics-table-area">
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
                    <th>비용</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.length === 0 && (
                    <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>데이터 없음</td></tr>
                  )}
                  {rows.map((r, i) => (
                    <tr key={i}>
                      <td>{(r.date || '').slice(0, 10)}</td>
                      <td className="title-cell">{r.title || '-'}</td>
                      <td>{r.model || '-'}</td>
                      <td>{(r.tokens || 0).toLocaleString()}</td>
                      <td>${(r.cost || 0).toFixed(4)}</td>
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

        <div className="analytics-chart-area">
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
