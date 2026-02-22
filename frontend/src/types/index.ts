export interface User {
  id: number
  email: string
  name: string
  role: 'admin' | 'editor'
  is_active: boolean
  created_at: string
}

export interface Topic {
  id: number
  name: string
  category: string
  description: string | null
  created_at: string
}

export type ContentType = 'problem' | 'concept'

export interface ScriptData {
  type: ContentType
  hook_text: string
  diagram_description: string
  content_steps: Array<{ text: string; highlight?: string }>
  answer_options?: string[]
  correct_answer?: string
  explanation?: string
  cta_text: string
  tweet_text?: string
}

export interface Content {
  id: number
  topic_id: number
  content_type: ContentType
  script_text: string | null
  script_data: ScriptData | null
  diagram_path: string | null
  diagram_url: string | null
  audio_path: string | null
  video_path: string | null
  duration_seconds: number | null
  status: ContentStatus
  error_message: string | null
  created_at: string
  updated_at: string
  topic?: Topic
}

export type ContentStatus = 'draft' | 'generating' | 'ready' | 'queued' | 'published' | 'failed'

export interface Schedule {
  id: number
  content_id: number
  platform: Platform
  scheduled_at: string
  published_at: string | null
  status: 'pending' | 'published' | 'failed'
  platform_post_id: string | null
  error_message: string | null
  created_at: string
}

export type Platform = 'youtube' | 'tiktok' | 'instagram' | 'twitter'

export interface QueueStatus {
  pending_items: {
    content_id: number
    scheduled_at: string | null
    status: string
  }[]
  sqs_approximate_count: number
}

export interface GenerateRequest {
  topic_name: string
  category: string
  description?: string
  content_type?: ContentType
}

export interface GenerateResponse {
  content_id: number
  status: string
  message: string
}

export interface AuthToken {
  access_token: string
  token_type: string
}
