import { useEffect, useRef } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import FullPageState from '../shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import { useSettingsStore } from '../../store/settingsStore'
import { preloadRouteChunksForRole } from '../../routePreload'

const CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'

export default function AppShell() {
  const user = useAuthStore((state) => state.user)
  const shellStatus = useSettingsStore((state) => state.shellStatus)
  const loadShellSettings = useSettingsStore((state) => state.loadShellSettings)
  const preloadedRoleRef = useRef<string | null>(null)

  // Load shell settings for every authenticated role, not only ADMIN.
  // The underlying endpoint (GET /settings/shell) is accessible to all roles.
  useEffect(() => {
    if (user?.role && shellStatus === 'idle') {
      void loadShellSettings()
    }
  }, [loadShellSettings, shellStatus, user?.role])

  useEffect(() => {
    if (!user?.role || preloadedRoleRef.current === user.role) {
      return
    }

    const timer = window.setTimeout(() => {
      preloadRouteChunksForRole(user.role)
      preloadedRoleRef.current = user.role
    }, 150)

    return () => {
      window.clearTimeout(timer)
    }
  }, [user?.role])

  // Show a brief loading screen while shell settings are in flight.
  // For non-ADMIN roles we still show this briefly — it resolves quickly.
  if (shellStatus === 'idle' || shellStatus === 'loading') {
    return (
      <FullPageState
        title="Učitavanje postavki sustava"
        message="Sustav dohvaća naziv lokacije i nazive rola za trenutnu sesiju."
        loading
      />
    )
  }

  // On error: ADMIN gets a hard retry screen (they need settings for admin
  // operations). Non-ADMIN roles fall through to render with safe defaults —
  // they do not need write access to settings and must not be hard-blocked.
  if (shellStatus === 'error' && user?.role === 'ADMIN') {
    return (
      <FullPageState
        title="Greška pri povezivanju"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => {
          void loadShellSettings(true)
        }}
      />
    )
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--mantine-color-body)' }}>
      <Sidebar />
      <main style={{ flex: 1, padding: '1.5rem', background: 'var(--mantine-color-body)' }}>
        <Outlet />
      </main>
    </div>
  )
}
