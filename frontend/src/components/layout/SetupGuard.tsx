import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import FullPageState from '../shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import { fetchSetupStatus } from '../../utils/setup'
import { CONNECTION_ERROR_MESSAGE } from '../../utils/http'
import { showErrorToast } from '../../utils/toasts'

export default function SetupGuard() {
  const location = useLocation()  // still needed for <Navigate state={{ from: location }} />
  const user = useAuthStore((state) => state.user)
  const setupStatus = useAuthStore((state) => state.setupStatus)
  const setSetupStatus = useAuthStore((state) => state.setSetupStatus)
  const resetSetupStatus = useAuthStore((state) => state.resetSetupStatus)
  const logout = useAuthStore((state) => state.logout)

  const [loading, setLoading] = useState(setupStatus === 'unknown')
  const [hasError, setHasError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    if (setupStatus !== 'unknown') {
      setLoading(false)
      setHasError(false)
      return
    }

    let cancelled = false

    const checkSetupStatus = async () => {
      setLoading(true)
      setHasError(false)

      try {
        const setupRequired = await fetchSetupStatus()

        if (cancelled) {
          return
        }

        setSetupStatus(setupRequired)
      } catch {
        if (cancelled) {
          return
        }

        setHasError(true)
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void checkSetupStatus()

    return () => {
      cancelled = true
    }
  }, [retryCount, setSetupStatus, setupStatus])

  useEffect(() => {
    if (setupStatus === 'required' && user && user.role !== 'ADMIN') {
      showErrorToast('Početno postavljanje mora dovršiti administrator.')
      logout()
    }
  }, [logout, setupStatus, user])

  if (loading) {
    return (
      <FullPageState
        title="Provjera inicijalnog postavljanja"
        message="Sustav provjerava je li lokacija već konfigurirana."
        loading
      />
    )
  }

  if (hasError) {
    return (
      <FullPageState
        title="Greška povezivanja"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => {
          setHasError(false)
          setLoading(true)
          resetSetupStatus()
          setRetryCount((count) => count + 1)
        }}
      />
    )
  }

  if (setupStatus === 'required') {
    if (user?.role === 'ADMIN') {
      return <Navigate to="/setup" replace state={{ from: location }} />
    }

    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
