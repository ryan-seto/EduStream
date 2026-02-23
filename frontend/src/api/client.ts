import axios from 'axios'
import type {
  User,
  Content,
  AuthToken,
  GenerateRequest,
  GenerateResponse,
  QueueStatus,
} from '../types'

export const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses — only redirect if user had a token (was logged in)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem('token')) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const authApi = {
  googleLogin: async (credential: string): Promise<AuthToken> => {
    const response = await api.post('/auth/google', { credential })
    return response.data
  },

  getMe: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },

  getConfig: async (): Promise<{ google_client_id: string }> => {
    const response = await api.get('/auth/config')
    return response.data
  },
}

// Content
export const contentApi = {
  list: async (status?: string): Promise<Content[]> => {
    const params = status ? { status_filter: status } : {}
    const response = await api.get('/content/', { params })
    return response.data
  },

  get: async (id: number): Promise<Content> => {
    const response = await api.get(`/content/${id}`)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/content/${id}`)
  },
}

// Generation
export const generateApi = {
  single: async (data: GenerateRequest): Promise<GenerateResponse> => {
    const response = await api.post('/generate/single', data)
    return response.data
  },

  batch: async (topics: GenerateRequest[]): Promise<GenerateResponse[]> => {
    const response = await api.post('/generate/batch', { topics })
    return response.data
  },

  status: async (contentId: number): Promise<{
    content_id: number
    status: string
    has_script: boolean
    has_diagram: boolean
    has_audio: boolean
    has_video: boolean
    error_message: string | null
  }> => {
    const response = await api.get(`/generate/status/${contentId}`)
    return response.data
  },

  getSettings: async (): Promise<{ publish_interval_minutes: number }> => {
    const response = await api.get('/generate/settings')
    return response.data
  },

  updateSettings: async (data: { publish_interval_minutes: number }): Promise<{ publish_interval_minutes: number }> => {
    const response = await api.put('/generate/settings', data)
    return response.data
  },
}

// Publishing
export const publishApi = {
  platforms: async (): Promise<{
    platform: string
    configured: boolean
    name: string
  }[]> => {
    const response = await api.get('/publish/platforms')
    return response.data
  },

  publish: async (data: {
    content_id: number
    platform: string
    caption?: string
    hashtags?: string[]
  }): Promise<{
    success: boolean
    platform: string
    post_url: string | null
    post_id: string | null
    message: string
  }> => {
    const response = await api.post('/publish/publish', data)
    return response.data
  },

  queue: async (data: {
    content_id: number
    platform?: string
    scheduled_at?: string
  }): Promise<{ message: string; schedule_id: number; scheduled_at: string }> => {
    const response = await api.post('/publish/queue', data)
    return response.data
  },

  queueAll: async (): Promise<{ message: string; queued_count: number }> => {
    const response = await api.post('/publish/queue-all')
    return response.data
  },

  queueStatus: async (): Promise<QueueStatus> => {
    const response = await api.get('/publish/queue-status')
    return response.data
  },

  history: async (contentId: number): Promise<{
    id: number
    platform: string
    status: string
    published_at: string | null
    post_id: string | null
    error: string | null
  }[]> => {
    const response = await api.get(`/publish/history/${contentId}`)
    return response.data
  },
}

// Analytics
export const analyticsApi = {
  overview: async (): Promise<{
    total_content: number
    by_status: Record<string, number>
    by_type: Record<string, number>
    this_week: number
    this_month: number
    daily_counts: { date: string; count: number }[]
    category_counts: { category: string; count: number }[]
    recent_publications: {
      content_id: number
      title: string
      platform: string
      published_at: string | null
      post_url: string | null
      status: string
    }[]
    publish_rate: number
    weekly_publish_data: { date: string; status: string; count: number }[]
  }> => {
    const response = await api.get('/analytics/overview')
    return response.data
  },
}

export default api
