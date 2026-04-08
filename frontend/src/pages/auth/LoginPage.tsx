import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { TextInput, PasswordInput, Button, Paper, Title, Container, Text } from '@mantine/core'
import AuthLayout from '../../components/auth/AuthLayout'
import { useAuthStore } from '../../store/authStore'
import { authApi } from '../../api/auth'
import { fetchSetupStatus, getAuthenticatedDestination } from '../../utils/setup'
import { showErrorToast } from '../../utils/toasts'
import { getDisplayError } from '../../utils/http'

export default function LoginPage() {
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)
  const login = useAuthStore((state) => state.login)
  const logout = useAuthStore((state) => state.logout)
  const setSetupStatus = useAuthStore((state) => state.setSetupStatus)
  const resetSetupStatus = useAuthStore((state) => state.resetSetupStatus)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (isAuthenticated && user) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!username || !password) {
      setError('Korisničko ime i lozinka su obavezni.')
      return
    }

    setLoading(true)
    try {
      const data = await authApi.login(username, password)
      login(data.user, data.access_token, data.refresh_token)

      try {
        const setupRequired = await fetchSetupStatus()
        setSetupStatus(setupRequired)

        if (setupRequired && data.user.role !== 'ADMIN') {
          showErrorToast('Početno postavljanje mora dovršiti administrator.')
          logout()
          return
        }

        navigate(getAuthenticatedDestination(data.user.role, setupRequired), {
          replace: true,
        })
      } catch {
        resetSetupStatus()
        navigate('/', { replace: true })
      }
    } catch (err: unknown) {
      const msg = getDisplayError(err, 'Prijava nije uspjela. Pokušaj ponovno.')
      setError(msg)
      showErrorToast(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <Container size={420}>
        <Title ta="center" order={1}>
          Prijava u STOQIO
        </Title>
        <Text c="dimmed" size="sm" ta="center" mt={5}>
          Prijavi se svojim vjerodajnicama
        </Text>

        <Paper withBorder shadow="md" p={30} mt={30} radius="md">
          <form onSubmit={handleSubmit}>
            <TextInput
              label="Korisničko ime"
              placeholder="Unesite korisničko ime"
              required
              value={username}
              onChange={(event) => setUsername(event.currentTarget.value)}
            />
            <PasswordInput
              label="Lozinka"
              placeholder="Unesite lozinku"
              required
              mt="md"
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
              error={error}
            />

            <Button fullWidth mt="xl" type="submit" loading={loading}>
              Prijavi se
            </Button>
          </form>
        </Paper>
      </Container>
    </AuthLayout>
  )
}
