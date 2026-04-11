import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Center, Loader, Stack, Text } from '@mantine/core'
import ProtectedRoute from './components/layout/ProtectedRoute'
import SetupGuard from './components/layout/SetupGuard'
import AppShell from './components/layout/AppShell'
import LoginPage from './pages/auth/LoginPage'
import SetupPage from './pages/auth/SetupPage'
import { useAuthStore } from './store/authStore'
import { getHomeRouteForRole } from './utils/roles'
import {
  loadApprovalsPage,
  loadArticleDetailPage,
  loadDraftEntryPage,
  loadEmployeeDetailPage,
  loadEmployeesPage,
  loadIdentifierPage,
  loadInventoryCountPage,
  loadOrderDetailPage,
  loadOrdersPage,
  loadReceivingPage,
  loadReportsPage,
  loadSettingsPage,
  loadWarehousePage,
} from './routePreload'

// Route-level lazy imports — keeps the main bundle lean.
const DraftEntryPage = lazy(loadDraftEntryPage)
const ApprovalsPage = lazy(loadApprovalsPage)
const ReceivingPage = lazy(loadReceivingPage)
const OrdersPage = lazy(loadOrdersPage)
const OrderDetailPage = lazy(loadOrderDetailPage)
const WarehousePage = lazy(loadWarehousePage)
const ArticleDetailPage = lazy(loadArticleDetailPage)
const ReportsPage = lazy(loadReportsPage)
const IdentifierPage = lazy(loadIdentifierPage)
const EmployeesPage = lazy(loadEmployeesPage)
const EmployeeDetailPage = lazy(loadEmployeeDetailPage)
const InventoryCountPage = lazy(loadInventoryCountPage)
const SettingsPage = lazy(loadSettingsPage)

// Suspense fallback shared across lazy routes
const LazyFallback = (
  <Center style={{ minHeight: '32vh', width: '100%' }}>
    <Stack gap="xs" align="center">
      <Loader size="sm" />
      <Text size="sm" c="dimmed">
        Učitavanje modula…
      </Text>
    </Stack>
  </Center>
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
              <Route
                path="/receiving"
                element={
                  <Suspense fallback={LazyFallback}>
                    <ReceivingPage />
                  </Suspense>
                }
              />
              <Route
                path="/inventory"
                element={
                  <Suspense fallback={LazyFallback}>
                    <InventoryCountPage />
                  </Suspense>
                }
              />
              <Route
                path="/settings"
                element={
                  <Suspense fallback={LazyFallback}>
                    <SettingsPage />
                  </Suspense>
                }
              />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'MANAGER']} />}>
              <Route
                path="/orders"
                element={
                  <Suspense fallback={LazyFallback}>
                    <OrdersPage />
                  </Suspense>
                }
              />
              <Route
                path="/orders/:id"
                element={
                  <Suspense fallback={LazyFallback}>
                    <OrderDetailPage />
                  </Suspense>
                }
              />
              <Route
                path="/warehouse"
                element={
                  <Suspense fallback={LazyFallback}>
                    <WarehousePage />
                  </Suspense>
                }
              />
              <Route
                path="/warehouse/articles/:id"
                element={
                  <Suspense fallback={LazyFallback}>
                    <ArticleDetailPage />
                  </Suspense>
                }
              />
              <Route
                path="/reports"
                element={
                  <Suspense fallback={LazyFallback}>
                    <ReportsPage />
                  </Suspense>
                }
              />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'MANAGER', 'WAREHOUSE_STAFF', 'VIEWER']} />}>
              <Route
                path="/identifier"
                element={
                  <Suspense fallback={LazyFallback}>
                    <IdentifierPage />
                  </Suspense>
                }
              />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'MANAGER', 'WAREHOUSE_STAFF']} />}>
              <Route
                path="/employees"
                element={
                  <Suspense fallback={LazyFallback}>
                    <EmployeesPage />
                  </Suspense>
                }
              />
              <Route
                path="/employees/:id"
                element={
                  <Suspense fallback={LazyFallback}>
                    <EmployeeDetailPage />
                  </Suspense>
                }
              />
            </Route>
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
