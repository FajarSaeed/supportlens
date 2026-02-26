import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export type Category =
  | 'Billing'
  | 'Refund'
  | 'Account Access'
  | 'Cancellation'
  | 'General Inquiry'

export interface TraceOut {
  id: string
  user_message: string
  bot_response: string
  category: Category
  timestamp: string
  response_time_ms: number
}

export interface CategoryStat {
  count: number
  percent: number
}

export interface AnalyticsOut {
  total_traces: number
  avg_response_time_ms: number
  by_category: Record<Category, CategoryStat>
}

export interface ChatOut {
  bot_response: string
  response_time_ms: number
}

export const CATEGORIES: Category[] = [
  'Billing',
  'Refund',
  'Account Access',
  'Cancellation',
  'General Inquiry',
]

export const api = {
  getAnalytics: () =>
    http.get<AnalyticsOut>('/analytics').then((r) => r.data),

  getTraces: (category?: string) =>
    http
      .get<TraceOut[]>('/traces', { params: category ? { category } : {} })
      .then((r) => r.data),

  postTrace: (payload: {
    user_message: string
    bot_response: string
    response_time_ms: number
  }) => http.post<TraceOut>('/traces', payload).then((r) => r.data),

  chat: (user_message: string) =>
    http.post<ChatOut>('/chat', { user_message }).then((r) => r.data),
}
