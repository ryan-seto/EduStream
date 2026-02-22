import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { contentApi, publishApi, API_BASE } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import type { Content } from '../types'

function getAssetUrl(path: string | null): string | null {
  if (!path) return null
  const urlPath = path.replace(/\\/g, '/').replace(/^\.\//, '')
  return `${API_BASE}/${urlPath}`
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: 'bg-warm-400',
    generating: 'bg-yellow-500',
    ready: 'bg-emerald-500',
    queued: 'bg-emerald-400',
    published: 'bg-blue-500',
    failed: 'bg-red-500',
  }

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-warm-500">
      <span className={`w-1.5 h-1.5 rounded-full ${colors[status] || 'bg-warm-400'}`} />
      {status}
    </span>
  )
}

function ContentCard({ content, onDelete, onPublish, onQueue, isPublishing, isQueuing, isAdmin }: {
  content: Content
  onDelete: (id: number) => void
  onPublish: (id: number) => void
  onQueue: (id: number) => void
  isPublishing: boolean
  isQueuing: boolean
  isAdmin: boolean
}) {
  const [showDiagram, setShowDiagram] = useState(false)
  const [showVideo, setShowVideo] = useState(false)
  const scriptData = content.script_data
  const rawDiagramUrl = content.diagram_url || getAssetUrl(content.diagram_path)
  // Backend returns relative paths for local files — prepend API_BASE
  const diagramUrl = rawDiagramUrl && !rawDiagramUrl.startsWith('http')
    ? `${API_BASE}${rawDiagramUrl}`
    : rawDiagramUrl
  const videoUrl = getAssetUrl(content.video_path)

  const canPublish = content.status === 'ready' && content.diagram_path

  return (
    <div className="bg-white border border-warm-200 rounded-xl hover:shadow-md transition-all group relative overflow-hidden">
      {diagramUrl && (
        <div
          className="relative cursor-pointer"
          onClick={() => videoUrl ? setShowVideo(true) : setShowDiagram(true)}
        >
          <img
            src={diagramUrl}
            alt="Diagram"
            className="w-full h-36 object-cover rounded-t-xl"
          />
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            {videoUrl ? (
              <div className="flex flex-col items-center">
                <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
                <span className="text-white text-sm mt-1">Play Video</span>
              </div>
            ) : (
              <span className="text-white text-sm">View Diagram</span>
            )}
          </div>
          {videoUrl && (
            <div className="absolute top-2 left-2 px-2 py-0.5 bg-emerald-500 text-white text-xs rounded-full font-medium">
              Video Ready
            </div>
          )}
        </div>
      )}

      <div className="p-4">
        {isAdmin && (
          <button
            onClick={() => onDelete(content.id)}
            className="absolute top-2 right-2 p-1.5 text-warm-400 hover:text-red-500 hover:bg-red-50 transition-all bg-white/90 rounded-lg shadow-sm border border-warm-200 hover:border-red-300"
            title="Discard"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}

        <div className="flex justify-end mb-2 pr-6">
          <StatusDot status={content.status} />
        </div>

        {content.status === 'failed' && content.error_message && (
          <p className="text-xs text-red-500 mb-2 line-clamp-2">{content.error_message}</p>
        )}

        {scriptData ? (
          <div className="space-y-2">
            <p className="text-sm text-primary-600 font-medium">
              {scriptData.hook_text}
            </p>
            {scriptData.answer_options && (
              <div className="grid grid-cols-2 gap-1">
                {scriptData.answer_options.map((opt, i) => (
                  <span
                    key={i}
                    className={`text-xs px-2 py-1 rounded-lg ${
                      opt.startsWith(scriptData.correct_answer || '')
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-cream-100 text-warm-500'
                    }`}
                  >
                    {opt}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : content.script_text ? (
          <p className="text-sm text-warm-500 line-clamp-2">
            {content.script_text.substring(0, 100)}...
          </p>
        ) : content.status !== 'failed' ? (
          <p className="text-sm text-warm-400 italic">Generating script...</p>
        ) : null}

        {scriptData?.tweet_text && (
          <p className="text-xs text-warm-400 italic mt-2 px-1 line-clamp-3">
            "{scriptData.tweet_text}"
          </p>
        )}

        <div className="mt-3 text-xs text-warm-400 text-right">
          {new Date(content.created_at).toLocaleDateString()}
        </div>

        {canPublish && isAdmin && (
          <div className="mt-3">
            <div className="flex gap-2">
              <button
                onClick={() => onPublish(content.id)}
                disabled={isPublishing}
                className="py-2 px-3 border border-blue-200 bg-blue-50 hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-sm font-medium text-blue-600 transition-colors flex items-center justify-center gap-1.5"
                title="Publish immediately"
              >
                {isPublishing ? (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
                  </svg>
                )}
                Post Now
              </button>
              <button
                onClick={() => onQueue(content.id)}
                disabled={isQueuing}
                className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 disabled:cursor-not-allowed rounded-lg text-sm font-medium text-white transition-colors flex items-center justify-center gap-1.5"
                title="Approve for scheduled publishing"
              >
                {isQueuing ? (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
                Approve
              </button>
            </div>
          </div>
        )}

        {content.status === 'queued' && (
          <div className="mt-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-center text-emerald-700 font-medium">
            Approved — Scheduled
          </div>
        )}

        {content.status === 'published' && (
          <div className="mt-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-center text-emerald-700 font-medium">
            Published
          </div>
        )}
      </div>

      {/* Diagram Modal */}
      {showDiagram && diagramUrl && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-8"
          onClick={() => setShowDiagram(false)}
        >
          <div className="relative max-w-4xl max-h-full">
            <img
              src={diagramUrl}
              alt="Diagram"
              className="max-w-full max-h-[80vh] rounded-xl shadow-2xl"
            />
            <button
              onClick={() => setShowDiagram(false)}
              className="absolute -top-4 -right-4 p-2 bg-white rounded-full text-warm-600 hover:text-warm-800 shadow-lg"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Video Modal */}
      {showVideo && videoUrl && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-8"
          onClick={() => setShowVideo(false)}
        >
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <video
              src={videoUrl}
              controls
              autoPlay
              className="max-h-[85vh] rounded-xl shadow-2xl"
              style={{ maxWidth: '400px' }}
            />
            <button
              onClick={() => setShowVideo(false)}
              className="absolute -top-4 -right-4 p-2 bg-white rounded-full text-warm-600 hover:text-warm-800 shadow-lg"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            {content.duration_seconds && (
              <div className="absolute bottom-4 left-4 px-2 py-1 bg-black/70 rounded text-sm text-white">
                {Math.floor(content.duration_seconds / 60)}:{(content.duration_seconds % 60).toString().padStart(2, '0')}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function KpiCard({ label, value, accent, icon }: {
  label: string
  value: string | number
  accent?: string
  icon: React.ReactNode
}) {
  return (
    <div className="bg-white border border-warm-200 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-warm-400">{label}</p>
        <div className={`p-2 rounded-lg ${accent || 'bg-cream-200'}`}>
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold text-warm-800">{value}</p>
    </div>
  )
}

export default function Dashboard() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [publishingId, setPublishingId] = useState<number | null>(null)
  const [queuingId, setQueuingId] = useState<number | null>(null)

  const { data: content, isLoading } = useQuery({
    queryKey: ['content'],
    queryFn: () => contentApi.list(),
  })

  const deleteMutation = useMutation({
    mutationFn: contentApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
    },
  })

  const publishMutation = useMutation({
    mutationFn: (contentId: number) => publishApi.publish({
      content_id: contentId,
      platform: 'twitter',
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
      setPublishingId(null)
      if (data.post_url) {
        alert(`Published successfully! View at: ${data.post_url}`)
      }
    },
    onError: (error: Error) => {
      setPublishingId(null)
      alert(`Failed to publish: ${error.message}`)
    },
  })

  const queueMutation = useMutation({
    mutationFn: (contentId: number) => publishApi.queue({
      content_id: contentId,
      platform: 'twitter',
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
      setQueuingId(null)
      alert(`Queued! ${data.message}`)
    },
    onError: (error: Error) => {
      setQueuingId(null)
      alert(`Failed to queue: ${error.message}`)
    },
  })

  const queueAllMutation = useMutation({
    mutationFn: () => publishApi.queueAll(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['content'] })
      alert(data.message)
    },
    onError: (error: Error) => {
      alert(`Failed to queue all: ${error.message}`)
    },
  })

  const handleDelete = (id: number) => {
    if (confirm('Delete this content?')) {
      deleteMutation.mutate(id)
    }
  }

  const handlePublish = (id: number) => {
    if (confirm('Publish this content to Twitter?')) {
      setPublishingId(id)
      publishMutation.mutate(id)
    }
  }

  const handleQueue = (id: number) => {
    setQueuingId(id)
    queueMutation.mutate(id)
  }

  const now = new Date()
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)

  const stats = {
    total: content?.length || 0,
    generating: content?.filter(c => c.status === 'generating').length || 0,
    ready: content?.filter(c => c.status === 'ready').length || 0,
    published: content?.filter(c => c.status === 'published').length || 0,
    thisWeek: content?.filter(c => new Date(c.created_at) >= weekAgo).length || 0,
  }

  const successRate = stats.total > 0
    ? Math.round((stats.published / stats.total) * 100)
    : 0

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-warm-800">Dashboard</h1>
          <p className="text-sm text-warm-400 mt-1">Overview of your content pipeline</p>
        </div>
        {isAdmin && (
          <div className="flex items-center gap-3">
            {stats.ready > 0 && (
              <button
                onClick={() => {
                  if (confirm(`Approve all ${stats.ready} ready items for scheduled publishing?`)) {
                    queueAllMutation.mutate()
                  }
                }}
                disabled={queueAllMutation.isPending}
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Approve All ({stats.ready})
              </button>
            )}
            <Link
              to="/generate"
              className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
            >
              + Generate Content
            </Link>
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Total Posts"
          value={stats.total}
          accent="bg-cream-200"
          icon={<svg className="w-5 h-5 text-warm-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>}
        />
        <KpiCard
          label="Published"
          value={stats.published}
          accent="bg-emerald-50"
          icon={<svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" /></svg>}
        />
        <KpiCard
          label="This Week"
          value={stats.thisWeek}
          accent="bg-blue-50"
          icon={<svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>}
        />
        <KpiCard
          label="Success Rate"
          value={`${successRate}%`}
          accent="bg-primary-50"
          icon={<svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
        />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-warm-400">Loading...</div>
      ) : content && content.length > 0 ? (
        <>
          {/* Review Queue — ready posts awaiting approval */}
          {(() => {
            const readyItems = content.filter(c => c.status === 'ready')
            if (readyItems.length === 0) return null
            return (
              <div className="mb-8">
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold text-warm-800">Review Queue</h2>
                    <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700">
                      {readyItems.length} awaiting review
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  {readyItems.map((item) => (
                    <ContentCard
                      key={item.id}
                      content={item}
                      onDelete={handleDelete}
                      onPublish={handlePublish}
                      onQueue={handleQueue}
                      isPublishing={publishingId === item.id}
                      isQueuing={queuingId === item.id}
                      isAdmin={isAdmin}
                    />
                  ))}
                </div>
              </div>
            )
          })()}

          {/* Scheduled — approved posts waiting to publish */}
          {(() => {
            const queuedItems = content.filter(c => c.status === 'queued')
            if (queuedItems.length === 0) return null
            return (
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-lg font-semibold text-warm-800">Scheduled</h2>
                  <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-emerald-100 text-emerald-700">
                    {queuedItems.length} approved
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  {queuedItems.map((item) => (
                    <ContentCard
                      key={item.id}
                      content={item}
                      onDelete={handleDelete}
                      onPublish={handlePublish}
                      onQueue={handleQueue}
                      isPublishing={publishingId === item.id}
                      isQueuing={queuingId === item.id}
                      isAdmin={isAdmin}
                    />
                  ))}
                </div>
              </div>
            )
          })()}

          {/* Published & Other */}
          {(() => {
            const otherItems = content.filter(c => c.status !== 'ready' && c.status !== 'queued')
            if (otherItems.length === 0) return null
            return (
              <div className="mb-8">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold text-warm-800">All Content</h2>
                  {stats.generating > 0 && (
                    <span className="text-sm text-yellow-600 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
                      {stats.generating} generating...
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-4">
                  {otherItems.map((item) => (
                    <ContentCard
                      key={item.id}
                      content={item}
                      onDelete={handleDelete}
                      onPublish={handlePublish}
                      onQueue={handleQueue}
                      isPublishing={publishingId === item.id}
                      isQueuing={queuingId === item.id}
                      isAdmin={isAdmin}
                    />
                  ))}
                </div>
              </div>
            )
          })()}
        </>
      ) : (
        <div className="text-center py-16 bg-white border border-warm-200 rounded-xl">
          <p className="text-warm-500 mb-4">No content yet</p>
          {isAdmin && (
            <Link
              to="/generate"
              className="text-primary-600 hover:text-primary-700 font-medium hover:underline"
            >
              Generate your first post
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
