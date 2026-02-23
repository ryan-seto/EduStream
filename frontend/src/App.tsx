import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Generate from './pages/Generate'
import Analytics from './pages/Analytics'
import Sidebar from './components/layout/Sidebar'
import ProtectedRoute from './components/layout/ProtectedRoute'

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-cream-100">
      <Sidebar />
      <main className="flex-1 p-8 ml-64">
        {children}
      </main>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Public routes — viewable by anyone */}
      <Route
        path="/"
        element={
          <AppLayout>
            <Dashboard />
          </AppLayout>
        }
      />
      <Route
        path="/analytics"
        element={
          <AppLayout>
            <Analytics />
          </AppLayout>
        }
      />

      {/* Admin-only routes */}
      <Route
        path="/generate"
        element={
          <ProtectedRoute adminOnly>
            <AppLayout>
              <Generate />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App
