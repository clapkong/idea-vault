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
      <svg viewBox="0 0 200 200" width={180} height={180}>
        {slices.map((s, i) => (
          <path key={i} d={slicePath(100, 100, 80, s.start, s.angle)} fill={getModelColor(s.label)} />
        ))}
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
            <div className="chart-section">
              <h4 className="chart-title">모델 별 사용량</h4>
              <PieChart data={modelChartData} />
            </div>
          ) : (
            <div className="chart-section">
              <h4 className="chart-title">날짜 별 사용량</h4>
              <BarChart data={dateChartData} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
