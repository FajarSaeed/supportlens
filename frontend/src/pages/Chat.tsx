import { useRef, useState } from 'react'
import type { TraceOut } from '../api'
import { api } from '../api'

interface Message {
  role: 'user' | 'bot'
  text: string
  ms?: number
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [liveTraces, setLiveTraces] = useState<TraceOut[]>([])
  const [chatError, setChatError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setChatError(null)
    setMessages((prev) => [...prev, { role: 'user', text }])
    setLoading(true)

    try {
      // Step 1: call POST /chat
      const chatRes = await api.chat(text)

      setMessages((prev) => [
        ...prev,
        { role: 'bot', text: chatRes.bot_response, ms: chatRes.response_time_ms },
      ])

      // Step 2: log the trace — fire-and-forget, don't block UI on failure
      api
        .postTrace({
          user_message: text,
          bot_response: chatRes.bot_response,
          response_time_ms: chatRes.response_time_ms,
        })
        .then((trace) => {
          setLiveTraces((prev) => [trace, ...prev])
        })
        .catch((err) => {
          // Trace logging failed — log to console but don't show error to user
          console.warn('Trace logging failed:', err)
        })
    } catch {
      setChatError('Chat request failed. Is the backend running on :8000?')
    } finally {
      setLoading(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') void send()
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-gray-800">Chat</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Chat panel ── */}
        <div className="flex flex-col rounded-2xl border border-gray-200 shadow-sm overflow-hidden bg-white">
          {/* Message list */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[320px] max-h-[480px]">
            {messages.length === 0 && (
              <p className="text-gray-400 text-sm text-center mt-8">
                Send a message to start chatting…
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
                    m.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-br-sm'
                      : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                  }`}
                >
                  {m.text}
                  {m.ms !== undefined && (
                    <span className="block text-xs mt-1 opacity-60">{m.ms} ms</span>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-2 text-sm text-gray-400 animate-pulse">
                  Thinking…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input row */}
          <div className="border-t border-gray-100 p-3 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask a support question…"
              disabled={loading}
              className="flex-1 border border-gray-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50"
            />
            <button
              onClick={() => void send()}
              disabled={loading || !input.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white text-sm font-medium px-4 py-2 rounded-xl transition-colors"
            >
              Send
            </button>
          </div>

          {chatError && (
            <p className="px-4 pb-3 text-xs text-red-500">{chatError}</p>
          )}
        </div>

        {/* ── Live trace log ── */}
        <div className="rounded-2xl border border-gray-200 shadow-sm overflow-hidden bg-white">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-700 text-sm">Live Trace Log</h2>
            <span className="text-xs text-gray-400">{liveTraces.length} logged</span>
          </div>
          <div className="overflow-y-auto max-h-[480px] divide-y divide-gray-50">
            {liveTraces.length === 0 ? (
              <p className="text-gray-400 text-sm text-center py-8">
                Traces will appear here after each message.
              </p>
            ) : (
              liveTraces.map((t) => (
                <div key={t.id} className="px-4 py-3 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                      {t.category}
                    </span>
                    <span className="text-xs text-gray-400 font-mono">{t.response_time_ms} ms</span>
                  </div>
                  <p className="text-xs text-gray-600 truncate">
                    <span className="font-medium text-gray-500">U:</span> {t.user_message}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    <span className="font-medium text-gray-400">B:</span> {t.bot_response}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
