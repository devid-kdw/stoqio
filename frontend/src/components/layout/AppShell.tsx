// AppShell — scaffold stub.
// Will wrap Sidebar + main content area in a future phase.
export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar will go here */}
      <main style={{ flex: 1, padding: '1rem' }}>{children}</main>
    </div>
  )
}
