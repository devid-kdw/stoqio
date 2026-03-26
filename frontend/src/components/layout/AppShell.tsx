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

  useEffect(() => {
    if (user?.role === 'ADMIN' && shellStatus === 'idle') {
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

  if (user?.role === 'ADMIN' && (shellStatus === 'idle' || shellStatus === 'loading')) {
    return (
      <FullPageState
        title="Učitavanje postavki sustava"
        message="Sustav dohvaća naziv lokacije i nazive rola za trenutnu sesiju."
        loading
      />
    )
  }

  if (user?.role === 'ADMIN' && shellStatus === 'error') {
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
