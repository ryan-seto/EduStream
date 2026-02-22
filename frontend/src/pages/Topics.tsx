import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { topicsApi } from '../api/client'

const CATEGORIES = [
  'engineering',
  'physics',
  'mathematics',
  'chemistry',
  'biology',
]

export default function Topics() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [category, setCategory] = useState('engineering')
  const [description, setDescription] = useState('')

  const { data: topics, isLoading } = useQuery({
    queryKey: ['topics'],
    queryFn: () => topicsApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: topicsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topics'] })
      setName('')
      setDescription('')
      setShowForm(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: topicsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['topics'] })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    createMutation.mutate({
      name: name.trim(),
      category,
      description: description.trim() || null,
    })
  }

  const handleDelete = (id: number, topicName: string) => {
    if (confirm(`Delete topic "${topicName}"?`)) {
      deleteMutation.mutate(id)
    }
  }

  // Group topics by category
  const topicsByCategory = topics?.reduce((acc, topic) => {
    if (!acc[topic.category]) acc[topic.category] = []
    acc[topic.category].push(topic)
    return acc
  }, {} as Record<string, typeof topics>)

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-warm-800">Topics</h1>
          <p className="text-sm text-warm-400 mt-1">Manage your content topics and categories</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add Topic'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-8 p-6 bg-white border border-warm-200 rounded-xl">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-warm-700 mb-2">Topic Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Simply Supported Beam Analysis"
                className="w-full px-4 py-2.5 bg-cream-50 border border-warm-200 rounded-lg focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 text-warm-700 placeholder-warm-300"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-warm-700 mb-2">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-4 py-2.5 bg-cream-50 border border-warm-200 rounded-lg focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 text-warm-700"
              >
                {CATEGORIES.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-warm-700 mb-2">
              Description / Problem Details (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the specific problem setup, values, or context for this topic..."
              rows={3}
              className="w-full px-4 py-2.5 bg-cream-50 border border-warm-200 rounded-lg focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 text-warm-700 placeholder-warm-300"
            />
          </div>
          <button
            type="submit"
            disabled={createMutation.isPending || !name.trim()}
            className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {createMutation.isPending ? 'Adding...' : 'Add Topic'}
          </button>
        </form>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-warm-400">Loading topics...</div>
      ) : topics && topics.length > 0 ? (
        <div className="space-y-8">
          {Object.entries(topicsByCategory || {}).map(([cat, catTopics]) => (
            <div key={cat}>
              <h2 className="text-xs font-semibold text-warm-400 tracking-wider uppercase mb-3">{cat}</h2>
              <div className="grid grid-cols-2 gap-4">
                {catTopics?.map(topic => (
                  <div
                    key={topic.id}
                    className="p-4 bg-white border border-warm-200 rounded-xl group hover:shadow-md transition-all"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-medium text-warm-800 mb-1">{topic.name}</h3>
                        {topic.description && (
                          <p className="text-sm text-warm-400 line-clamp-2">{topic.description}</p>
                        )}
                        <p className="text-xs text-warm-300 mt-2">
                          Added {new Date(topic.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDelete(topic.id, topic.name)}
                        className="p-2 text-warm-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                        title="Delete topic"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-white border border-warm-200 rounded-xl">
          <div className="text-4xl mb-3">📂</div>
          <p className="text-warm-500 mb-4">No topics yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="text-primary-600 hover:text-primary-700 font-medium hover:underline"
          >
            Add your first topic
          </button>
        </div>
      )}
    </div>
  )
}
