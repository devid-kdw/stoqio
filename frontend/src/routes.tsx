import { Routes, Route, Navigate } from 'react-router-dom'

// Page stubs — will be replaced with real implementations in later phases.
// Each file matches the path in 07_ARCHITECTURE.md § 4 (Frontend routing).
const Placeholder = ({ name }: { name: string }) => (
  <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
    <h2>{name}</h2>
    <p>Scaffold placeholder — not yet implemented.</p>
  </div>
)

export default function AppRoutes() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Placeholder name="Login" />} />

      {/* Root redirect — will be role-aware in Phase 3 */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Protected stubs */}
      <Route path="/drafts" element={<Placeholder name="Drafts" />} />
      <Route path="/approvals" element={<Placeholder name="Approvals" />} />
      <Route path="/receiving" element={<Placeholder name="Receiving" />} />
      <Route path="/orders" element={<Placeholder name="Orders" />} />
      <Route path="/orders/:id" element={<Placeholder name="Order Detail" />} />
      <Route path="/warehouse" element={<Placeholder name="Warehouse" />} />
      <Route path="/warehouse/articles/:id" element={<Placeholder name="Article Detail" />} />
      <Route path="/identifier" element={<Placeholder name="Identifier" />} />
      <Route path="/employees" element={<Placeholder name="Employees" />} />
      <Route path="/employees/:id" element={<Placeholder name="Employee Detail" />} />
      <Route path="/inventory" element={<Placeholder name="Inventory Count" />} />
      <Route path="/reports" element={<Placeholder name="Reports" />} />
      <Route path="/settings" element={<Placeholder name="Settings" />} />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
