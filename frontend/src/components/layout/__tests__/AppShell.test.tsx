import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import AppShell from '../AppShell'
import { settingsApi } from '../../../api/settings'
import { useAuthStore } from '../../../store/authStore'
import { useSettingsStore } from '../../../store/settingsStore'
import { renderWithProviders } from '../../../utils/test-utils'

vi.mock('../../../api/settings', () => ({
  settingsApi: {
    getShellSettings: vi.fn(),
  },
}))

vi.mock('../../../routePreload', () => ({
  preloadRouteChunksForRole: vi.fn(),
}))

describe('AppShell - Installation-Wide Branding', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useSettingsStore.getState().resetShellSettings()
  })

  it('renders configured location name and role label for non-admin user on success', async () => {
    // 1. Arrange
    vi.mocked(settingsApi.getShellSettings).mockResolvedValue({
      location_name: 'Factory Beta',
      default_language: 'hr',
      role_display_names: [
        { role: 'ADMIN', display_name: 'Admin' },
        { role: 'MANAGER', display_name: 'Menadžment' },
        { role: 'WAREHOUSE_STAFF', display_name: 'Administracija' },
        { role: 'VIEWER', display_name: 'Revizija' },
        { role: 'OPERATOR', display_name: 'Radnik na traci' },
      ],
    })

    // Setup an authenticated non-admin user
    useAuthStore.setState({
      user: {
        id: 1,
        username: 'pero.radnik',
        role: 'OPERATOR',
      },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    // 2. Act
    renderWithProviders(<AppShell />)

    // Wait until the shell has loaded settings and the loading screen unmounts
    await waitFor(() => {
      expect(screen.queryByText('Učitavanje postavki sustava')).not.toBeInTheDocument()
    })

    // 3. Assert
    // Verify the location name rendered in Sidebar
    expect(screen.getByText('Factory Beta')).toBeInTheDocument()

    // Verify the role layout dynamically picked 'Radnik na traci' from the payload instead of default 'Operater'
    expect(screen.getByText('Korisnik: pero.radnik (Radnik na traci)')).toBeInTheDocument()
  })

  it('falls back to default location name and role label when shell settings fail', async () => {
    // 1. Arrange
    vi.mocked(settingsApi.getShellSettings).mockRejectedValue(new Error('Network error'))

    useAuthStore.setState({
      user: {
        id: 2,
        username: 'ana.uprava',
        role: 'VIEWER',
      },
      accessToken: 'token',
      refreshToken: 'refresh',
      isAuthenticated: true,
    })

    // 2. Act
    renderWithProviders(<AppShell />)

    // Wait until loading finishes (error state falls through for non-admin roles)
    await waitFor(() => {
      expect(screen.queryByText('Učitavanje postavki sustava')).not.toBeInTheDocument()
    })

    // 3. Assert
    // Should display the DEFAULT_LOCATION_NAME because the payload failed
    expect(screen.getByText('STOQIO')).toBeInTheDocument()

    // Should display the DEFAULT_ROLE_DISPLAY_NAMES mapped to VIEWER -> 'Kontrola'
    expect(screen.getByText('Korisnik: ana.uprava (Kontrola)')).toBeInTheDocument()
  })
})
