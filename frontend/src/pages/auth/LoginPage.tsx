import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { TextInput, PasswordInput, Button, Paper, Title, Container, Text } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import axios from 'axios'
import { useAuthStore } from '../../store/authStore'
import { authApi } from '../../api/auth'
import { getHomeRouteForRole } from '../../utils/roles'

export default function LoginPage() {
  const { isAuthenticated, user, login } = useAuthStore()
  
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (isAuthenticated && user) {
    return <Navigate to={getHomeRouteForRole(user.role)} replace />
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!username || !password) {
      setError('Username and password are required.')
      return
    }

    setLoading(true)
    try {
      const data = await authApi.login(username, password)
      login(data.user, data.access_token, data.refresh_token)
    } catch (err: unknown) {
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.message || 'Login failed. Please try again.'
        : 'Login failed. Please try again.'
      setError(msg)
      notifications.show({
        title: 'Error',
        message: msg,
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container size={420} my={40}>
      <Title ta="center" order={1}>
        WMS Login
      </Title>
      <Text c="dimmed" size="sm" ta="center" mt={5}>
        Please sign in with your credentials
      </Text>

      <Paper withBorder shadow="md" p={30} mt={30} radius="md">
        <form onSubmit={handleSubmit}>
          <TextInput
            label="Username"
            placeholder="Your username"
            required
            value={username}
            onChange={(event) => setUsername(event.currentTarget.value)}
          />
          <PasswordInput
            label="Password"
            placeholder="Your password"
            required
            mt="md"
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
            error={error}
          />
          
          <Button fullWidth mt="xl" type="submit" loading={loading}>
            Sign in
          </Button>
        </form>
      </Paper>
    </Container>
  )
}
