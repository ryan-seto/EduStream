import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { analyticsApi } from '../api/client'

function KpiCard({ label, value, sub, accent, icon }: {
  label: string
  value: string | number
  sub?: string
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
      {sub && <p className="text-xs text-warm-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function Analytics() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => analyticsApi.overview(),
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <div className="text-center py-16 text-warm-400">Loading analytics...</div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-16">
        <p className="text-warm-500 mb-2">Failed to load analytics</p>
        <p className="text-sm text-warm-400">Make sure the backend is running</p>
      </div>
    )
  }

  const published = data.by_status?.published || 0
  const failed = data.by_status?.failed || 0
  const ready = data.by_status?.ready || 0

  // Calculate avg posts per week (over last 30 days)
  const avgPerWeek = data.this_month > 0
    ? Math.round((data.this_month / 30) * 7 * 10) / 10
    : 0

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-warm-800">Analytics</h1>
        <p className="text-sm text-warm-400 mt-1">Track your content generation and publishing performance</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Total Generated"
          value={data.total_content}
          sub={`${data.this_week} this week`}
          accent="bg-cream-200"
          icon={<svg className="w-5 h-5 text-warm-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>}
        />
        <KpiCard
          label="Published"
          value={published}
          sub={`${ready} ready to publish`}
          accent="bg-emerald-50"
          icon={<svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 13l4 4L19 7" /></svg>}
        />
        <KpiCard
          label="Publish Rate"
          value={`${data.publish_rate}%`}
          sub={`${failed} failed`}
          accent="bg-primary-50"
          icon={<svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
        />
        <KpiCard
          label="Avg Posts / Week"
          value={avgPerWeek}
          sub="Last 30 days"
          accent="bg-blue-50"
          icon={<svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        {/* Posts Over Time */}
        <div className="bg-white border border-warm-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-warm-700 mb-4">Posts Over Time</h3>
          {data.daily_counts.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={data.daily_counts}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#527a52" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#527a52" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8e5e0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#a8a198' }}
                  tickFormatter={(v) => {
                    const d = new Date(v)
                    return `${d.getMonth() + 1}/${d.getDate()}`
                  }}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#a8a198' }}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e8e5e0',
                    borderRadius: '8px',
                    fontSize: '13px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#527a52"
                  strokeWidth={2}
                  fill="url(#colorCount)"
                  name="Posts"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-warm-400 text-sm">
              No data yet
            </div>
          )}
        </div>

        {/* Posts by Category */}
        <div className="bg-white border border-warm-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-warm-700 mb-4">Posts by Category</h3>
          {data.category_counts.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data.category_counts} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e8e5e0" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: '#a8a198' }}
                  allowDecimals={false}
                />
                <YAxis
                  dataKey="category"
                  type="category"
                  tick={{ fontSize: 11, fill: '#a8a198' }}
                  width={90}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e8e5e0',
                    borderRadius: '8px',
                    fontSize: '13px',
                  }}
                />
                <Bar
                  dataKey="count"
                  fill="#6f966f"
                  radius={[0, 4, 4, 0]}
                  name="Posts"
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-warm-400 text-sm">
              No data yet
            </div>
          )}
        </div>
      </div>

      {/* Impressions Placeholder + Content Type Breakdown */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-white border border-warm-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-warm-700 mb-1">Total Impressions</h3>
          <p className="text-3xl font-bold text-warm-800 mb-1">--</p>
          <p className="text-xs text-warm-400">Connect X API for live data</p>
        </div>
        <div className="bg-white border border-warm-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-warm-700 mb-1">Avg Engagement</h3>
          <p className="text-3xl font-bold text-warm-800 mb-1">--</p>
          <p className="text-xs text-warm-400">Connect X API for live data</p>
        </div>
        <div className="bg-white border border-warm-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-warm-700 mb-1">Top Post</h3>
          <p className="text-3xl font-bold text-warm-800 mb-1">--</p>
          <p className="text-xs text-warm-400">Connect X API for live data</p>
        </div>
      </div>

      {/* Content Type Breakdown */}
      {Object.keys(data.by_type).length > 0 && (
        <div className="bg-white border border-warm-200 rounded-xl p-5 mb-8">
          <h3 className="text-sm font-semibold text-warm-700 mb-4">Content Type Breakdown</h3>
          <div className="flex gap-6">
            {Object.entries(data.by_type).map(([type, count]) => (
              <div key={type} className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${type === 'problem' ? 'bg-primary-500' : 'bg-blue-500'}`} />
                <div>
                  <p className="text-sm font-medium text-warm-700 capitalize">{type}</p>
                  <p className="text-xs text-warm-400">{count} posts</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Publications Table */}
      <div className="bg-white border border-warm-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-warm-700 mb-4">Recent Publications</h3>
        {data.recent_publications.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-warm-100">
                  <th className="text-left py-2 pr-4 font-medium text-warm-400">Date</th>
                  <th className="text-left py-2 pr-4 font-medium text-warm-400">Title</th>
                  <th className="text-left py-2 pr-4 font-medium text-warm-400">Platform</th>
                  <th className="text-left py-2 font-medium text-warm-400">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_publications.map((pub, i) => (
                  <tr key={i} className="border-b border-warm-50 last:border-0">
                    <td className="py-2.5 pr-4 text-warm-500">
                      {pub.published_at
                        ? new Date(pub.published_at).toLocaleDateString()
                        : '--'}
                    </td>
                    <td className="py-2.5 pr-4 text-warm-700 max-w-xs truncate">
                      {pub.title}
                    </td>
                    <td className="py-2.5 pr-4">
                      <span className="px-2 py-0.5 bg-cream-200 text-warm-500 rounded-full text-xs capitalize">
                        {pub.platform}
                      </span>
                    </td>
                    <td className="py-2.5">
                      <span className={`inline-flex items-center gap-1.5 text-xs ${
                        pub.status === 'published'
                          ? 'text-emerald-600'
                          : pub.status === 'failed'
                          ? 'text-red-500'
                          : 'text-warm-400'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          pub.status === 'published'
                            ? 'bg-emerald-500'
                            : pub.status === 'failed'
                            ? 'bg-red-500'
                            : 'bg-warm-400'
                        }`} />
                        {pub.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-warm-400 text-sm">
            No publications yet. Publish content from the Dashboard to see data here.
          </div>
        )}
      </div>
    </div>
  )
}
