import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

const publicNav = [
  {
    name: 'Dashboard',
    href: '/',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1" />
      </svg>
    ),
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
]

const adminNav = [
  {
    name: 'Generate',
    href: '/generate',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
      </svg>
    ),
  },
  {
    name: 'Topics',
    href: '/topics',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
  },
]

function NavLink({ item }: { item: typeof publicNav[0] }) {
  const location = useLocation()
  const isActive = location.pathname === item.href

  return (
    <Link
      to={item.href}
      className={`flex items-center gap-3 px-3 py-2.5 mb-0.5 rounded-lg text-sm font-medium transition-colors ${
        isActive
          ? 'bg-primary-50 text-primary-700'
          : 'text-warm-500 hover:bg-cream-200 hover:text-warm-700'
      }`}
    >
      <span className={isActive ? 'text-primary-600' : 'text-warm-400'}>{item.icon}</span>
      {item.name}
    </Link>
  )
}

export default function Sidebar() {
  const { user, isAdmin, logout } = useAuth()

  return (
    <div className="fixed inset-y-0 left-0 w-64 bg-white border-r border-warm-200">
      <div className="flex flex-col h-full">
        {/* Brand */}
        <div className="px-6 py-5">
          <h1 className="text-lg font-bold text-warm-800">EduStream AI</h1>
          <p className="text-xs text-warm-400 mt-0.5">Content Dashboard</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3">
          <p className="px-3 mb-2 text-xs font-semibold text-warm-400 tracking-wider uppercase">
            Content
          </p>
          {publicNav.map((item) => (
            <NavLink key={item.name} item={item} />
          ))}

          {isAdmin && (
            <>
              <div className="my-4 border-t border-warm-100" />
              <p className="px-3 mb-2 text-xs font-semibold text-warm-400 tracking-wider uppercase">
                Admin
              </p>
              {adminNav.map((item) => (
                <NavLink key={item.name} item={item} />
              ))}
            </>
          )}
        </nav>

        {/* User block */}
        <div className="p-4 border-t border-warm-200">
          {user ? (
            <>
              <div className="mb-3 px-2">
                <p className="text-sm font-medium text-warm-700">{user.name}</p>
                <p className="text-xs text-warm-400">{user.role}</p>
              </div>
              <button
                onClick={logout}
                className="w-full px-3 py-2 text-sm text-warm-400 hover:text-warm-700 hover:bg-cream-200 rounded-lg transition-colors text-left"
              >
                Sign Out
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="w-full block px-3 py-2 text-sm text-warm-500 hover:text-warm-700 hover:bg-cream-200 rounded-lg transition-colors text-center"
            >
              Sign In
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
