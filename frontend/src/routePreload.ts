export const loadDraftEntryPage = () => import('./pages/drafts/DraftEntryPage')
export const loadApprovalsPage = () => import('./pages/approvals/ApprovalsPage')
export const loadReceivingPage = () => import('./pages/receiving/ReceivingPage')
export const loadOrdersPage = () => import('./pages/orders/OrdersPage')
export const loadOrderDetailPage = () => import('./pages/orders/OrderDetailPage')
export const loadWarehousePage = () => import('./pages/warehouse/WarehousePage')
export const loadArticleDetailPage = () => import('./pages/warehouse/ArticleDetailPage')
export const loadReportsPage = () => import('./pages/reports/ReportsPage')
export const loadIdentifierPage = () => import('./pages/identifier/IdentifierPage')
export const loadEmployeesPage = () => import('./pages/employees/EmployeesPage')
export const loadEmployeeDetailPage = () => import('./pages/employees/EmployeeDetailPage')
export const loadInventoryCountPage = () => import('./pages/inventory/InventoryCountPage')
export const loadSettingsPage = () => import('./pages/settings/SettingsPage')

type Role =
  | 'ADMIN'
  | 'MANAGER'
  | 'WAREHOUSE_STAFF'
  | 'VIEWER'
  | 'OPERATOR'
  | string
  | undefined
  | null

export function preloadRouteChunksForRole(role: Role): void {
  const loaders = [loadIdentifierPage]

  if (role === 'ADMIN' || role === 'OPERATOR') {
    loaders.push(loadDraftEntryPage)
  }

  if (role === 'ADMIN') {
    loaders.push(
      loadApprovalsPage,
      loadReceivingPage,
      loadInventoryCountPage,
      loadSettingsPage,
    )
  }

  if (role === 'ADMIN' || role === 'MANAGER') {
    loaders.push(
      loadOrdersPage,
      loadOrderDetailPage,
      loadWarehousePage,
      loadArticleDetailPage,
      loadReportsPage,
    )
  }

  if (role === 'ADMIN' || role === 'WAREHOUSE_STAFF') {
    loaders.push(loadEmployeesPage, loadEmployeeDetailPage)
  }

  void Promise.allSettled(loaders.map((loader) => loader()))
}
