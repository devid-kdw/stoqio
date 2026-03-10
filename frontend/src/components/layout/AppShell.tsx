import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function AppShell() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#fafafa' }}>
      <Sidebar />
      <main style={{ flex: 1, padding: '1.5rem', background: '#fff' }}>
        <Outlet />
      </main>
    </div>
  )
}
