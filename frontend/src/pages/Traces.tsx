import { useEffect, useState } from 'react'
import type { TraceOut, Category } from '../api'
import { api, CATEGORIES } from '../api'

const BADGE: Record<Category, string> = {
  Billing: 'bg-blue-100 text-blue-700',
  Refund: 'bg-green-100 text-green-700',
  'Account Access': 'bg-yellow-100 text-yellow-700',
  Cancellation: 'bg-red-100 text-red-700',
  'General Inquiry': 'bg-purple-100 text-purple-700',
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}

export default function Traces() {
  const [traces, setTraces] = useState<TraceOut[]>([])
  const [filter, setFilter] = useState<string>('')
  const [search, setSearch] = useState<string>('')
  const [searchInput, setSearchInput] = useState<string>('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    api
      .getTraces(filter || undefined, search || undefined)
      .then(setTraces)
      .catch(() => setError('Failed to load traces. Is the backend running on :8000?'))
      .finally(() => setLoading(false))
  }, [filter, search])

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSearch(searchInput.trim())
  }

  function clearSearch() {
    setSearchInput('')
    setSearch('')
  }

  function toggleRow(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-gray-800">Traces</h1>

        {/* Category filter */}
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">All Categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Keyword search bar */}
      <form onSubmit={handleSearchSubmit} className="flex gap-2 items-center">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by keyword in messages…"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <button
          type="submit"
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          Search
        </button>
        {search && (
          <button
            type="button"
            onClick={clearSearch}
            className="text-sm text-gray-500 hover:text-gray-700 px-3 py-2 rounded-lg border border-gray-300 bg-white transition-colors"
          >
            Clear
          </button>
        )}
      </form>

      {search && (
        <p className="text-xs text-indigo-600 font-medium">
          Showing results for: <span className="italic">"{search}"</span>
        </p>
      )}

      {error && <p className="text-red-600">{error}</p>}

      {loading ? (
        <p className="text-gray-400 animate-pulse">Loading…</p>
      ) : traces.length === 0 ? (
        <p className="text-gray-500">No traces found.</p>
      ) : (
        <div className="rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left w-8"></th>
                <th className="px-4 py-3 text-left">User Message</th>
                <th className="px-4 py-3 text-left">Category</th>
                <th className="px-4 py-3 text-left">Response (ms)</th>
                <th className="px-4 py-3 text-left">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {traces.map((t) => {
                const isOpen = expanded.has(t.id)
                return (
                  <>
                    <tr
                      key={t.id}
                      className="hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => toggleRow(t.id)}
                    >
                      <td className="px-4 py-3 text-gray-400 select-none">
                        {isOpen ? '▾' : '▸'}
                      </td>
                      <td className="px-4 py-3 text-gray-800 max-w-xs truncate">
                        {t.user_message}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${BADGE[t.category]}`}
                        >
                          {t.category}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600 font-mono">{t.response_time_ms}</td>
                      <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                        {formatDate(t.timestamp)}
                      </td>
                    </tr>

                    {isOpen && (
                      <tr key={`${t.id}-expanded`} className="bg-indigo-50">
                        <td />
                        <td colSpan={4} className="px-4 py-4 space-y-3">
                          <div>
                            <p className="text-xs font-semibold uppercase text-indigo-400 mb-1">
                              User
                            </p>
                            <p className="text-gray-800 whitespace-pre-wrap">{t.user_message}</p>
                          </div>
                          <div>
                            <p className="text-xs font-semibold uppercase text-indigo-400 mb-1">
                              Bot
                            </p>
                            <p className="text-gray-700 whitespace-pre-wrap">{t.bot_response}</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
