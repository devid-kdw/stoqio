import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import axios from 'axios'
import FullPageState from '../../components/shared/FullPageState'
import { setupApi } from '../../api/setup'
import { useAuthStore } from '../../store/authStore'
import {
  DEFAULT_SETUP_TIMEZONE,
  fetchSetupStatus,
  getTimezoneOptions,
  isRetryableSetupRequestError,
} from '../../utils/setup'
import { getHomeRouteForRole } from '../../utils/roles'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'

const CONNECTION_ERROR_MESSAGE =
  'Connection error. Please check that the server is running and try again.'

interface FormErrors {
  name?: string
  timezone?: string
}

export default function SetupPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const accessToken = useAuthStore((state) => state.accessToken)
  const setSetupStatus = useAuthStore((state) => state.setSetupStatus)
  const resetSetupStatus = useAuthStore((state) => state.resetSetupStatus)

  const timezoneOptions = getTimezoneOptions().map((timezone) => ({
    value: timezone,
    label: timezone,
  }))

  const [name, setName] = useState('')
  const [timezone, setTimezone] = useState(DEFAULT_SETUP_TIMEZONE)
  const [errors, setErrors] = useState<FormErrors>({})
  const [statusLoading, setStatusLoading] = useState(true)
  const [statusError, setStatusError] = useState(false)
  const [setupRequired, setSetupRequiredState] = useState<boolean | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    let cancelled = false

    const loadSetupStatus = async () => {
      setStatusLoading(true)
      setStatusError(false)

      try {
        const isSetupRequired = await fetchSetupStatus()

        if (cancelled) {
          return
        }

        setSetupStatus(isSetupRequired)
        setSetupRequiredState(isSetupRequired)
      } catch {
        if (cancelled) {
          return
        }

        resetSetupStatus()
        setStatusError(true)
      } finally {
        if (!cancelled) {
          setStatusLoading(false)
        }
      }
    }

    void loadSetupStatus()

    return () => {
      cancelled = true
    }
  }, [resetSetupStatus, retryCount, setSetupStatus])

  if (!user || !accessToken) {
    return <Navigate to="/login" replace />
  }

  if (statusLoading) {
    return (
      <FullPageState
        title="Provjera inicijalnog postavljanja"
        message="Sustav provjerava je li lokacija vec konfigurirana."
        loading
      />
    )
  }

  if (statusError) {
    return (
      <FullPageState
        title="Connection error"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Try again"
        onAction={() => {
          setStatusError(false)
          setStatusLoading(true)
          setRetryCount((count) => count + 1)
        }}
      />
    )
  }

  if (submitError) {
    return (
      <FullPageState
        title="Connection error"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Try again"
        onAction={() => {
          setSubmitError(false)
        }}
      />
    )
  }

  if (setupRequired === false) {
    return <Navigate to={getHomeRouteForRole(user.role)} replace />
  }

  const validate = (): FormErrors => {
    const nextErrors: FormErrors = {}
    const trimmedName = name.trim()

    if (!trimmedName) {
      nextErrors.name = 'Location name is required.'
    } else if (trimmedName.length > 100) {
      nextErrors.name = 'Location name must be 100 characters or fewer.'
    }

    if (!timezone) {
      nextErrors.timezone = 'Timezone is required.'
    }

    return nextErrors
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextErrors = validate()
    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      return
    }

    setSubmitting(true)
    setSubmitError(false)

    try {
      const payload = {
        name: name.trim(),
        timezone,
      }

      try {
        await setupApi.create(payload)
      } catch (error) {
        if (!isRetryableSetupRequestError(error)) {
          throw error
        }

        await setupApi.create(payload)
      }

      setSetupStatus(false)
      showSuccessToast('Initial setup completed successfully.')
      navigate('/approvals', { replace: true })
    } catch (error) {
      if (isRetryableSetupRequestError(error)) {
        setSubmitError(true)
        return
      }

      const message = axios.isAxiosError(error)
        ? error.response?.data?.message || 'Setup failed. Please try again.'
        : 'Setup failed. Please try again.'

      if (axios.isAxiosError(error)) {
        const field = error.response?.data?.details?.field

        if (field === 'name') {
          setErrors((currentErrors) => ({
            ...currentErrors,
            name: message,
          }))
        }

        if (error.response?.status === 409) {
          setSetupStatus(false)
          navigate(getHomeRouteForRole(user.role), { replace: true })
        }
      }

      showErrorToast(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Box
      style={{
        minHeight: '100vh',
        padding: '2rem',
        background:
          'radial-gradient(circle at top left, rgba(197, 224, 222, 0.55) 0%, rgba(247, 248, 250, 1) 45%, rgba(232, 238, 244, 0.9) 100%)',
      }}
    >
      <Box style={{ maxWidth: 1200, margin: '0 auto' }}>
        <Paper
          withBorder
          radius="xl"
          shadow="md"
          p="xl"
          style={{ width: '100%', maxWidth: 620 }}
        >
          <Stack gap="xl">
            <Stack gap="xs">
              <Text size="sm" tt="uppercase" fw={700} c="dimmed">
                Prvo pokretanje
              </Text>
              <Title order={1}>Postavljanje lokacije</Title>
              <Text c="dimmed">
                Prije rada u aplikaciji potrebno je unijeti osnovnu lokaciju sustava.
              </Text>
            </Stack>

            <form onSubmit={handleSubmit}>
              <Stack gap="md">
                <TextInput
                  label="Naziv lokacije"
                  placeholder="npr. Skladiste Tvornica d.o.o."
                  required
                  maxLength={100}
                  value={name}
                  onChange={(event) => {
                    setName(event.currentTarget.value)
                    setErrors((currentErrors) => ({ ...currentErrors, name: undefined }))
                  }}
                  error={errors.name}
                />

                <Select
                  label="Vremenska zona"
                  placeholder="Odaberite vremensku zonu"
                  required
                  searchable
                  data={timezoneOptions}
                  value={timezone}
                  onChange={(value) => {
                    setTimezone(value ?? '')
                    setErrors((currentErrors) => ({ ...currentErrors, timezone: undefined }))
                  }}
                  error={errors.timezone}
                  nothingFoundMessage="Nema rezultata"
                />

                <Button type="submit" loading={submitting} mt="sm">
                  Spremi i nastavi
                </Button>
              </Stack>
            </form>
          </Stack>
        </Paper>
      </Box>
    </Box>
  )
}
