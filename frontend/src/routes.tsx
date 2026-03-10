import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './components/layout/ProtectedRoute'
import AppShell from './components/layout/AppShell'
import LoginPage from './pages/auth/LoginPage'
import { useAuthStore } from './store/authStore'
import { getHomeRouteForRole } from './utils/roles'

// Placeholders
const Placeholder = ({ name }: { name: string }) => (
  <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
    <h2>{name}</h2>
    <p>Scaffold placeholder — not yet implemented.</p>
  </div>
)

export default function AppRoutes() {
  const { isAuthenticated, user } = useAuthStore()

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route 
        path="/" 
        element={
          isAuthenticated ? (
            <Navigate to={getHomeRouteForRole(user?.role)} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        } 
      />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'OPERATOR']} />}>
            <Route path="/drafts" element={<Placeholder name="Drafts" />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
            <Route path="/approvals" element={<Placeholder name="Approvals" />} />
            <Route path="/receiving" element={<Placeholder name="Receiving" />} />
            <Route path="/inventory" element={<Placeholder name="Inventory Count" />} />
            <Route path="/settings" element={<Placeholder name="Settings" />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'MANAGER']} />}>
            <Route path="/orders" element={<Placeholder name="Orders" />} />
            <Route path="/orders/:id" element={<Placeholder name="Order Detail" />} />
            <Route path="/warehouse" element={<Placeholder name="Warehouse" />} />
            <Route path="/warehouse/articles/:id" element={<Placeholder name="Article Detail" />} />
            <Route path="/reports" element={<Placeholder name="Reports" />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'MANAGER', 'WAREHOUSE_STAFF', 'VIEWER']} />}>
            <Route path="/identifier" element={<Placeholder name="Identifier" />} />
          </Route>

          <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'WAREHOUSE_STAFF']} />}>
            <Route path="/employees" element={<Placeholder name="Employees" />} />
            <Route path="/employees/:id" element={<Placeholder name="Employee Detail" />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
