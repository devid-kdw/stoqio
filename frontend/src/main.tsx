import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MantineProvider, localStorageColorSchemeManager } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

import App from './App'
import { authApi } from './api/auth'
import FullPageState from './components/shared/FullPageState'
import { getStoredRefreshToken, useAuthStore } from './store/authStore'
import './i18n'

const queryClient = new QueryClient()
const root = ReactDOM.createRoot(document.getElementById('root')!)

// Mantine 8 color-scheme manager — reads/writes localStorage key stoqio_color_scheme
const colorSchemeManager = localStorageColorSchemeManager({ key: 'stoqio_color_scheme' })

function renderApp() {
  root.render(
    <React.StrictMode>
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <MantineProvider colorSchemeManager={colorSchemeManager} defaultColorScheme="light">
            <Notifications autoClose={4000} limit={1} />
            <App />
          </MantineProvider>
        </QueryClientProvider>
      </BrowserRouter>
    </React.StrictMode>,
  )
}

function renderBootstrapLoading() {
  root.render(
    <React.StrictMode>
      <MantineProvider colorSchemeManager={colorSchemeManager} defaultColorScheme="light">
        <FullPageState
          title="Obnavljanje sesije"
          message="Sustav provjerava postoji li valjana prijava za ovu karticu."
          loading
        />
      </MantineProvider>
    </React.StrictMode>,
  )
}

async function bootstrapAuth() {
  const refreshToken = getStoredRefreshToken()

  if (!refreshToken) {
    return
  }

  useAuthStore.getState().hydrateRefreshToken(refreshToken)

  try {
    const { access_token } = await authApi.refresh(refreshToken)
    const user = await authApi.me(access_token)

    useAuthStore.getState().setAuth(
      {
        id: user.id,
        username: user.username,
        role: user.role,
      },
      access_token,
      refreshToken,
    )
  } catch {
    useAuthStore.getState().logout()

    if (window.location.pathname !== '/login') {
      window.history.replaceState(null, '', '/login')
    }
  }
}

async function start() {
  if (getStoredRefreshToken()) {
    renderBootstrapLoading()
  }

  await bootstrapAuth()
  renderApp()
}

void start()
