import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './components/layout/ProtectedRoute'
import SetupGuard from './components/layout/SetupGuard'
import AppShell from './components/layout/AppShell'
import LoginPage from './pages/auth/LoginPage'
import SetupPage from './pages/auth/SetupPage'
import FullPageState from './components/shared/FullPageState'
import { useAuthStore } from './store/authStore'
import { getHomeRouteForRole } from './utils/roles'

// Route-level lazy imports — keeps the main bundle lean.
const DraftEntryPage = lazy(() => import('./pages/drafts/DraftEntryPage'))
const ApprovalsPage = lazy(() => import('./pages/approvals/ApprovalsPage'))

// Suspense fallback shared across lazy routes
const LazyFallback = <FullPageState title="Učitavanje…" loading />

// Placeholders for not-yet-implemented pages
const Placeholder = ({ name }: { name: string }) => (
  <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
    <h2>{name}</h2>
    <p>Scaffold placeholder — not yet implemented.</p>
  </div>
)

function HomeRedirect() {
  const user = useAuthStore((state) => state.user)
  return <Navigate to={getHomeRouteForRole(user?.role)} replace />
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
          <Route path="/setup" element={<SetupPage />} />
        </Route>

        <Route element={<SetupGuard />}>
          <Route path="/" element={<HomeRedirect />} />

          <Route element={<AppShell />}>
            <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'OPERATOR']} />}>
              <Route
                path="/drafts"
                element={
                  <Suspense fallback={LazyFallback}>
                    <DraftEntryPage />
                  </Suspense>
                }
              />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
              <Route
                path="/approvals"
                element={
                  <Suspense fallback={LazyFallback}>
                    <ApprovalsPage />
                  </Suspense>
                }
              />
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
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

