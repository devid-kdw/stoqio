import { Center, Loader } from '@mantine/core'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { getHomeRouteForRole } from '../../utils/roles'

interface ProtectedRouteProps {
  allowedRoles?: string[]
}

export default function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { authStatus, isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  // During bootstrap, auth state is resolving — show a loading indicator
  // instead of redirecting to login prematurely (N-6).
  if (authStatus === 'loading') {
    return (
      <Center style={{ height: '100vh' }}>
        <Loader />
      </Center>
    )
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    const homeRoute = getHomeRouteForRole(user.role)
    return <Navigate to={homeRoute} replace />
  }

  return <Outlet />
}
