import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import FullPageState from '../shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import { useSettingsStore } from '../../store/settingsStore'

const CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'

export default function AppShell() {
  const user = useAuthStore((state) => state.user)
  const shellStatus = useSettingsStore((state) => state.shellStatus)
  const loadShellSettings = useSettingsStore((state) => state.loadShellSettings)

  useEffect(() => {
    if (user?.role === 'ADMIN' && shellStatus === 'idle') {
      void loadShellSettings()
    }
  }, [loadShellSettings, shellStatus, user?.role])

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
    <div style={{ display: 'flex', minHeight: '100vh', background: '#fafafa' }}>
      <Sidebar />
      <main style={{ flex: 1, padding: '1.5rem', background: '#fff' }}>
        <Outlet />
      </main>
    </div>
  )
}
