import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { ActionIcon, Button, Stack, Text, Tooltip, useMantineColorScheme } from '@mantine/core'
import { IconSun, IconMoon } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { authApi } from '../../api/auth'
import {
  DEFAULT_LOCATION_NAME,
  useSettingsStore,
} from '../../store/settingsStore'

export default function Sidebar() {
  const { t } = useTranslation()
  const { user, refreshToken, logout } = useAuthStore()
  const locationName = useSettingsStore((state) => state.locationName)
  const roleDisplayNames = useSettingsStore((state) => state.roleDisplayNames)
  const { colorScheme, toggleColorScheme } = useMantineColorScheme()

  const handleLogout = async () => {
    try {
      if (refreshToken) {
        await authApi.logout(refreshToken)
      }
    } catch {
      // Logout API call failed — user is still logged out client-side via finally
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
        height: '100%',
        overflowY: 'auto',
        flexShrink: 0,
      }}
    >
      <div style={{ marginBottom: '2rem' }}>
        <Text fw={700} size="lg">
          {locationName}
        </Text>
        {locationName !== DEFAULT_LOCATION_NAME ? (
          <Text size="xs" c="dimmed">
            {t('sidebar.location.default')}
          </Text>
        ) : null}
        <Text size="xs" c="dimmed">
          {t('sidebar.user')}: {user.username} ({currentRoleLabel})
        </Text>
      </div>

      <Stack gap={4} style={{ flex: 1 }}>
        {canSeeApprovals && (
          <NavLink to="/approvals" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.approvals')}
          </NavLink>
        )}
        {canSeeDrafts && (
          <NavLink to="/drafts" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.drafts')}
          </NavLink>
        )}
        {canSeeWarehouse && (
          <NavLink to="/warehouse" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.warehouse')}
          </NavLink>
        )}
        {canSeeIdentifier && (
          <NavLink to="/identifier" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.identifier')}
          </NavLink>
        )}
        {canSeeOrders && (
          <NavLink to="/orders" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.orders')}
          </NavLink>
        )}
        {canSeeReceiving && (
          <NavLink to="/receiving" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.receiving')}
          </NavLink>
        )}
        {canSeeEmployees && (
          <NavLink to="/employees" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.employees')}
          </NavLink>
        )}
        {canSeeInventory && (
          <NavLink to="/inventory" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.inventory')}
          </NavLink>
        )}
        {canSeeReports && (
          <NavLink to="/reports" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.reports')}
          </NavLink>
        )}
        {canSeeSettings && (
          <NavLink to="/settings" style={({ isActive }) => (isActive ? activeStyle : linkStyle)}>
            {t('nav.settings')}
          </NavLink>
        )}
      </Stack>

      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: `1px solid ${isDark ? '#373a40' : '#ddd'}` }}>
        <Tooltip label={isDark ? t('sidebar.theme.light') : t('sidebar.theme.dark')} position="right" withArrow>
          <ActionIcon
            id="sidebar-color-scheme-toggle"
            variant="subtle"
            size="lg"
            aria-label={isDark ? t('sidebar.theme.switch_light') : t('sidebar.theme.switch_dark')}
            onClick={() => toggleColorScheme()}
            mb="xs"
          >
            {isDark ? <IconSun size={18} /> : <IconMoon size={18} />}
          </ActionIcon>
        </Tooltip>
        <Button variant="outline" color="red" fullWidth onClick={handleLogout}>
          {t('sidebar.logout')}
        </Button>
      </div>
    </nav>
  )
}
