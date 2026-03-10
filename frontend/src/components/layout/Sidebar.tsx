import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { Button, Stack, Text } from '@mantine/core'
import { authApi } from '../../api/auth'

export default function Sidebar() {
  const { user, refreshToken, logout } = useAuthStore()
  
  const handleLogout = async () => {
    try {
      if (refreshToken) {
        await authApi.logout(refreshToken)
      }
    } catch (e) {
      console.error('Logout failed', e)
    } finally {
      logout()
    }
  }

  if (!user) return null

  const role = user.role

  const canSeeDrafts = ['ADMIN', 'OPERATOR'].includes(role)
  const canSeeApprovals = ['ADMIN'].includes(role)
  const canSeeReceiving = ['ADMIN'].includes(role)
  const canSeeOrders = ['ADMIN', 'MANAGER'].includes(role)
  const canSeeWarehouse = ['ADMIN', 'MANAGER'].includes(role)
  const canSeeIdentifier = ['ADMIN', 'MANAGER', 'WAREHOUSE_STAFF', 'VIEWER'].includes(role)
  const canSeeEmployees = ['ADMIN', 'WAREHOUSE_STAFF'].includes(role)
  const canSeeInventory = ['ADMIN'].includes(role)
  const canSeeReports = ['ADMIN', 'MANAGER'].includes(role)
  const canSeeSettings = ['ADMIN'].includes(role)

  const linkStyle = {
    display: 'block',
    padding: '0.75rem 1rem',
    textDecoration: 'none',
    color: '#333',
    borderRadius: '4px',
    marginBottom: '0.25rem'
  }

  const activeStyle = {
    ...linkStyle,
    background: '#e0e0e0',
    fontWeight: 'bold'
  }

  return (
    <nav style={{ width: '240px', background: '#f5f5f5', padding: '1rem', borderRight: '1px solid #ddd', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '2rem' }}>
        <Text fw={700} size="lg">WMS</Text>
        <Text size="xs" c="dimmed">User: {user.username} ({user.role})</Text>
      </div>

      <Stack gap={4} style={{ flex: 1 }}>
        {canSeeApprovals && <NavLink to="/approvals" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Approvals</NavLink>}
        {canSeeDrafts && <NavLink to="/drafts" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Drafts</NavLink>}
        {canSeeWarehouse && <NavLink to="/warehouse" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Warehouse</NavLink>}
        {canSeeIdentifier && <NavLink to="/identifier" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Identifier</NavLink>}
        {canSeeOrders && <NavLink to="/orders" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Orders</NavLink>}
        {canSeeReceiving && <NavLink to="/receiving" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Receiving</NavLink>}
        {canSeeEmployees && <NavLink to="/employees" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Employees</NavLink>}
        {canSeeInventory && <NavLink to="/inventory" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Inventory Count</NavLink>}
        {canSeeReports && <NavLink to="/reports" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Reports</NavLink>}
        {canSeeSettings && <NavLink to="/settings" style={({ isActive }) => isActive ? activeStyle : linkStyle}>Settings</NavLink>}
      </Stack>

      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid #ddd' }}>
        <Button variant="outline" color="red" fullWidth onClick={handleLogout}>
          Logout
        </Button>
      </div>
    </nav>
  )
}
