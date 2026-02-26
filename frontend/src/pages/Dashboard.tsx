import { useEffect, useState } from 'react'
import type { AnalyticsOut, Category } from '../api'
import { api, CATEGORIES } from '../api'

const CATEGORY_META: Record<Category, { emoji: string; color: string }> = {
  Billing: { emoji: '💳', color: 'bg-blue-50 border-blue-300 text-blue-800' },
  Refund: { emoji: '↩️', color: 'bg-green-50 border-green-300 text-green-800' },
  'Account Access': { emoji: '🔐', color: 'bg-yellow-50 border-yellow-300 text-yellow-800' },
  Cancellation: { emoji: '🚫', color: 'bg-red-50 border-red-300 text-red-800' },
  'General Inquiry': { emoji: '💬', color: 'bg-purple-50 border-purple-300 text-purple-800' },
}

export default function Dashboard() {
  const [data, setData] = useState<AnalyticsOut | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getAnalytics()
      .then(setData)
      .catch(() => setError('Failed to load analytics. Is the backend running on :8000?'))
  }, [])

  if (error)
    return <div className="p-8 text-red-600 font-medium">{error}</div>

  if (!data)
    return <div className="p-8 text-gray-500 animate-pulse">Loading analytics…</div>

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Total Traces</p>
          <p className="mt-1 text-4xl font-bold text-gray-800">{data.total_traces}</p>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Avg Response</p>
          <p className="mt-1 text-4xl font-bold text-gray-800">
            {data.avg_response_time_ms.toFixed(0)}
            <span className="text-lg font-normal text-gray-500 ml-1">ms</span>
          </p>
        </div>
      </div>

      {/* Category cards */}
      <div>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">By Category</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CATEGORIES.map((cat) => {
            const stat = data.by_category[cat]
            const meta = CATEGORY_META[cat]
            return (
              <div
                key={cat}
                className={`rounded-2xl border p-5 flex items-start gap-4 shadow-sm ${meta.color}`}
              >
                <span className="text-3xl">{meta.emoji}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm truncate">{cat}</p>
                  <p className="text-3xl font-bold mt-1">{stat.count}</p>
                  <div className="mt-2 h-1.5 rounded-full bg-black/10 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-current opacity-40"
                      style={{ width: `${stat.percent.toFixed(1)}%` }}
                    />
                  </div>
                  <p className="text-xs mt-1 opacity-70">{stat.percent.toFixed(1)}%</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
