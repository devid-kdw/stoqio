import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { ActionIcon, Button, Stack, Text, Tooltip, useMantineColorScheme } from '@mantine/core'
import { IconSun, IconMoon } from '@tabler/icons-react'
import { authApi } from '../../api/auth'
import {
  DEFAULT_LOCATION_NAME,
  useSettingsStore,
} from '../../store/settingsStore'

export default function Sidebar() {
  const { user, refreshToken, logout } = useAuthStore()
  const locationName = useSettingsStore((state) => state.locationName)
  const roleDisplayNames = useSettingsStore((state) => state.roleDisplayNames)
  const { colorScheme, toggleColorScheme } = useMantineColorScheme()

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
  const currentRoleLabel = roleDisplayNames[role as keyof typeof roleDisplayNames] ?? role

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

  const isDark = colorScheme === 'dark'

  const linkStyle = {
    display: 'block',
    padding: '0.75rem 1rem',
    textDecoration: 'none',
    color: isDark ? '#c1c2c5' : '#333',
    borderRadius: '4px',
    marginBottom: '0.25rem',
  }

  const activeStyle = {
    ...linkStyle,
    background: isDark ? '#2c2e33' : '#e0e0e0',
    fontWeight: 'bold',
  }

  return (
    <nav
      style={{
        width: '240px',
        background: isDark ? '#1a1b1e' : '#f5f5f5',
        padding: '1rem',
        borderRight: `1px solid ${isDark ? '#373a40' : '#ddd'}`,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ marginBottom: '2rem' }}>
        <Text fw={700} size="lg">
          {locationName}
        </Text>
        {locationName !== DEFAULT_LOCATION_NAME ? (
          <Text size="xs" c="dimmed">
            STOQIO
          </Text>
        ) : null}
        <Text size="xs" c="dimmed">
          Korisnik: {user.username} ({currentRoleLabel})
        </Text>
      </div>

      <Stack gap={4} style={{ flex: 1 }}>
        {canSeeApprovals && (
          <NavLink to="/approvals" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Odobravanja
          </NavLink>
        )}
        {canSeeDrafts && (
          <NavLink to="/drafts" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Unos izlaza
          </NavLink>
        )}
        {canSeeWarehouse && (
          <NavLink to="/warehouse" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Skladište
          </NavLink>
        )}
        {canSeeIdentifier && (
          <NavLink to="/identifier" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Identifikacija
          </NavLink>
        )}
        {canSeeOrders && (
          <NavLink to="/orders" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Narudžbenice
          </NavLink>
        )}
        {canSeeReceiving && (
          <NavLink to="/receiving" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Zaprimanje
          </NavLink>
        )}
        {canSeeEmployees && (
          <NavLink to="/employees" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Zaposlenici
          </NavLink>
        )}
        {canSeeInventory && (
          <NavLink to="/inventory" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Inventura
          </NavLink>
        )}
        {canSeeReports && (
          <NavLink to="/reports" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Izvještaji
          </NavLink>
        )}
        {canSeeSettings && (
          <NavLink to="/settings" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            Postavke
          </NavLink>
        )}
      </Stack>

      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: `1px solid ${isDark ? '#373a40' : '#ddd'}` }}>
        <Tooltip label={isDark ? 'Svijetli način' : 'Tamni način'} position="right" withArrow>
          <ActionIcon
            id="sidebar-color-scheme-toggle"
            variant="subtle"
            size="lg"
            aria-label={isDark ? 'Prebaci na svijetli način' : 'Prebaci na tamni način'}
            onClick={() => toggleColorScheme()}
            mb="xs"
          >
            {isDark ? <IconSun size={18} /> : <IconMoon size={18} />}
          </ActionIcon>
        </Tooltip>
        <Button variant="outline" color="red" fullWidth onClick={handleLogout}>
          Odjava
        </Button>
      </div>
    </nav>
  )
}
