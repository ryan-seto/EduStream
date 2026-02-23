import { useState, useEffect, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { generateApi } from '../api/client'
import type { GenerateRequest } from '../types'

const INTERVAL_OPTIONS = [
  { label: '1 hour', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '6 hours', value: 360 },
  { label: '12 hours', value: 720 },
  { label: '24 hours', value: 1440 },
]

type QueueItem = {
  topic: string
  status: 'queued' | 'generating' | 'ready' | 'failed'
  id?: number
  hookText?: string
  tweetText?: string
}

// Scenario categories matching the backend scenario pool
const SCENARIO_CATEGORIES = [
  {
    id: 'beam',
    label: 'Beam Reactions',
    description: 'Simply supported, cantilever, UDL problems',
    tags: 'beam loading reaction simply supported',
    icon: '━',
  },
  {
    id: 'cantilever',
    label: 'Cantilever Beams',
    description: 'Fixed support with point loads and moments',
    tags: 'beam cantilever fixed moment',
    icon: '┗',
  },
  {
    id: 'fbd',
    label: 'Force Equilibrium',
    description: 'Free body diagrams, resultant forces, inclined planes',
    tags: 'force fbd free body equilibrium',
    icon: '↗',
  },
  {
    id: 'stress',
    label: 'Stress & Strain',
    description: 'Axial stress, shear stress, elongation',
    tags: 'stress strain axial shear',
    icon: '⊕',
  },
  {
    id: 'moment',
    label: 'Moments',
    description: 'Force moments, couple moments, torque',
    tags: 'moment couple torque',
    icon: '↻',
  },
  {
    id: 'stress_strain',
    label: 'Stress-Strain Curves',
    description: 'Identify points, material behavior, true/false',
    tags: 'stress strain curve yield ultimate fracture material interview',
    icon: '📈',
  },
  {
    id: 'concepts',
    label: 'Concept Posts',
    description: "Hooke's law, pulleys, gear ratios — infographics & quizzes",
    tags: 'concept hooke pulley gear ratio interview',
    icon: '💡',
  },
]

function StatusBadge({ status }: { status: QueueItem['status'] }) {
  const config: Record<string, { text: string; color: string; bg: string; animate?: boolean }> = {
    queued: { text: 'Queued', color: 'text-warm-400', bg: 'bg-cream-200' },
    generating: { text: 'Generating...', color: 'text-yellow-600', bg: 'bg-yellow-50', animate: true },
    ready: { text: 'Ready', color: 'text-emerald-600', bg: 'bg-emerald-50' },
    failed: { text: 'Failed', color: 'text-red-600', bg: 'bg-red-50' },
  }
  const { text, color, bg, animate } = config[status] || config.queued
  return (
    <span className={`text-sm px-2.5 py-1 rounded-full font-medium ${color} ${bg} ${animate ? 'animate-pulse' : ''}`}>
      {text}
    </span>
  )
}

export default function Generate() {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<'single' | 'batch'>('single')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [batchCount, setBatchCount] = useState(5)
  const [results, setResults] = useState<QueueItem[]>([])

  const { data: settingsData } = useQuery({
    queryKey: ['generate-settings'],
    queryFn: () => generateApi.getSettings(),
  })

  const intervalMutation = useMutation({
    mutationFn: (minutes: number) => generateApi.updateSettings({ publish_interval_minutes: minutes }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['generate-settings'] }),
  })

  // Poll for status updates on queued/generating items
  const pollStatuses = useCallback(async () => {
    const pendingItems = results.filter(r => r.id && (r.status === 'queued' || r.status === 'generating'))
    if (pendingItems.length === 0) return

    for (const item of pendingItems) {
      if (!item.id) continue
      try {
        const status = await generateApi.status(item.id)
        setResults(prev => prev.map(r =>
          r.id === item.id
            ? {
                ...r,
                status: status.status as QueueItem['status'],
                hookText: status.script_data?.hook_text,
                tweetText: status.script_data?.tweet_text,
              }
            : r
        ))
        if (status.status === 'ready' || status.status === 'failed') {
          queryClient.invalidateQueries({ queryKey: ['content'] })
        }
      } catch (err) {
        console.error('Failed to poll status:', err)
      }
    }
  }, [results, queryClient])

  useEffect(() => {
    const interval = setInterval(pollStatuses, 2000)
    return () => clearInterval(interval)
  }, [pollStatuses])

  const singleMutation = useMutation({
    mutationFn: (data: GenerateRequest) => generateApi.single(data),
    onSuccess: (data, variables) => {
      setResults(prev => [...prev, {
        topic: variables.topic_name,
        status: 'generating',
        id: data.content_id,
      }])
    },
  })

  const batchMutation = useMutation({
    mutationFn: (topics: GenerateRequest[]) => generateApi.batch(topics),
    onSuccess: (data, variables) => {
      setResults(prev => [
        ...prev,
        ...data.map((d, i) => ({
          topic: variables[i]?.topic_name || 'Problem',
          status: 'generating' as const,
          id: d.content_id,
        })),
      ])
    },
  })

  const handleGenerateSingle = (categoryId: string) => {
    const cat = SCENARIO_CATEGORIES.find(c => c.id === categoryId)
    if (!cat) return
    singleMutation.mutate({
      topic_name: cat.tags,
      category: 'engineering',
      description: cat.tags,
    })
  }

  const handleGenerateRandom = () => {
    singleMutation.mutate({
      topic_name: '',
      category: '',
      description: '',
    })
  }

  const handleBatchGenerate = () => {
    const topics: GenerateRequest[] = []
    for (let i = 0; i < batchCount; i++) {
      if (selectedCategory) {
        const cat = SCENARIO_CATEGORIES.find(c => c.id === selectedCategory)!
        topics.push({
          topic_name: cat.tags,
          category: 'engineering',
          description: cat.tags,
        })
      } else {
        // Random mix — let backend pick from full pool with LRU
        topics.push({
          topic_name: '',
          category: '',
          description: '',
        })
      }
    }
    batchMutation.mutate(topics)
  }

  const readyCount = results.filter(r => r.status === 'ready').length
  const generatingCount = results.filter(r => r.status === 'generating').length

  return (
    <div>
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-2xl font-bold text-warm-800 mb-2">Generate Content</h1>
          <p className="text-warm-400">
            Each generation creates a unique problem with randomized values and answer options.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-white border border-warm-200 rounded-lg px-3 py-2">
          <span className="text-xs text-warm-400 whitespace-nowrap">Post every</span>
          <select
            value={settingsData?.publish_interval_minutes || 720}
            onChange={(e) => intervalMutation.mutate(Number(e.target.value))}
            className="text-sm font-medium text-warm-700 bg-transparent border-none focus:outline-none cursor-pointer"
          >
            {INTERVAL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setMode('single')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === 'single'
              ? 'bg-primary-600 text-white'
              : 'bg-white border border-warm-200 text-warm-600 hover:bg-cream-200'
          }`}
        >
          Single
        </button>
        <button
          onClick={() => setMode('batch')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === 'batch'
              ? 'bg-primary-600 text-white'
              : 'bg-white border border-warm-200 text-warm-600 hover:bg-cream-200'
          }`}
        >
          Batch Generate
        </button>
      </div>

      {mode === 'single' ? (
        <div>
          {/* Quick generate random */}
          <button
            onClick={handleGenerateRandom}
            disabled={singleMutation.isPending}
            className="w-full mb-6 px-6 py-4 bg-primary-600 hover:bg-primary-700 rounded-xl font-medium text-white transition-colors disabled:opacity-50 text-lg"
          >
            {singleMutation.isPending ? 'Generating...' : 'Generate Random Problem'}
          </button>

          {/* Category grid */}
          <h3 className="font-medium mb-4 text-warm-500">Or pick a category:</h3>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {SCENARIO_CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => handleGenerateSingle(cat.id)}
                disabled={singleMutation.isPending}
                className="p-4 bg-white border border-warm-200 hover:border-primary-400 hover:shadow-md rounded-xl text-left transition-all disabled:opacity-50"
              >
                <div className="text-2xl mb-2">{cat.icon}</div>
                <div className="font-medium text-warm-800 mb-1">{cat.label}</div>
                <div className="text-sm text-warm-400">{cat.description}</div>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-4 bg-white border border-warm-200 rounded-xl p-6">
          <div>
            <label className="block text-sm font-medium text-warm-700 mb-2">Category</label>
            <select
              value={selectedCategory || ''}
              onChange={(e) => setSelectedCategory(e.target.value || null)}
              className="w-full px-4 py-2.5 bg-cream-50 border border-warm-200 rounded-lg focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 text-warm-700"
            >
              <option value="">Random mix (all categories)</option>
              {SCENARIO_CATEGORIES.map(cat => (
                <option key={cat.id} value={cat.id}>{cat.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-warm-700 mb-2">
              Number of problems: <span className="text-primary-600 font-bold">{batchCount}</span>
            </label>
            <input
              type="range"
              min={1}
              max={30}
              value={batchCount}
              onChange={(e) => setBatchCount(parseInt(e.target.value))}
              className="w-full accent-primary-600"
            />
            <div className="flex justify-between text-xs text-warm-400">
              <span>1</span>
              <span>30</span>
            </div>
          </div>

          <button
            onClick={handleBatchGenerate}
            disabled={batchMutation.isPending}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-700 rounded-lg font-medium text-white transition-colors disabled:opacity-50"
          >
            {batchMutation.isPending ? 'Generating...' : `Generate ${batchCount} Problems`}
          </button>
        </div>
      )}

      {/* Generation Queue */}
      {results.length > 0 && (
        <div className="mt-8">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-medium text-warm-800">
              Generation Queue
              {generatingCount > 0 && (
                <span className="text-yellow-600 text-sm ml-2">({generatingCount} generating...)</span>
              )}
            </h3>
            <span className="text-sm text-warm-400">
              {readyCount}/{results.length} ready
            </span>
          </div>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {[...results].reverse().map((result, i) => (
              <div key={i} className="flex justify-between items-center p-3 bg-white border border-warm-200 rounded-lg">
                <div className="flex-1 min-w-0 mr-4">
                  <span className="text-sm text-warm-700 truncate block">
                    {result.hookText || result.topic || 'Random Problem'}
                  </span>
                  {result.tweetText && (
                    <span className="text-xs text-warm-400 italic truncate block mt-0.5">
                      "{result.tweetText}"
                    </span>
                  )}
                </div>
                <StatusBadge status={result.status} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
