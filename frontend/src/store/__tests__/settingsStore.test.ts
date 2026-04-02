import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSettingsStore, DEFAULT_LOCATION_NAME, DEFAULT_ROLE_DISPLAY_NAMES } from '../settingsStore'
import { settingsApi } from '../../api/settings'
import i18n from '../../i18n'

vi.mock('../../api/settings', () => ({
  settingsApi: {
    getShellSettings: vi.fn(),
  },
}))

vi.mock('../../i18n', () => ({
  default: {
    changeLanguage: vi.fn().mockResolvedValue(true),
    language: 'hr',
  },
}))

describe('settingsStore and language lifecycle', () => {
  beforeEach(() => {
    useSettingsStore.getState().resetShellSettings()
    vi.clearAllMocks()
  })

  it('loading shell settings applies default_language to i18n and updates state', async () => {
    vi.mocked(settingsApi.getShellSettings).mockResolvedValue({
      location_name: 'Test Location',
      role_display_names: [{ role: 'ADMIN', display_name: 'SuperAdmin' }],
      default_language: 'en',
    })

    await useSettingsStore.getState().loadShellSettings()

    expect(settingsApi.getShellSettings).toHaveBeenCalledTimes(1)
    expect(i18n.changeLanguage).toHaveBeenCalledWith('en')

    const state = useSettingsStore.getState()
    expect(state.locationName).toBe('Test Location')
    expect(state.roleDisplayNames.ADMIN).toBe('SuperAdmin')
    // Check fallback for omitted roles
    expect(state.roleDisplayNames.MANAGER).toBe(DEFAULT_ROLE_DISPLAY_NAMES.MANAGER)
    expect(state.shellStatus).toBe('ready')
  })

  it('applying saved General settings changes the active i18n language immediately', async () => {
    await useSettingsStore.getState().applyGeneralSettings({
      location_name: 'New Config Location',
      timezone: 'Europe/Berlin',
      default_language: 'de',
    })

    expect(i18n.changeLanguage).toHaveBeenCalledWith('de')
    
    const state = useSettingsStore.getState()
    expect(state.locationName).toBe('New Config Location')
    expect(state.shellStatus).toBe('ready')
  })

  it('handles shell settings API failure gracefully and leaves safe defaults', async () => {
    vi.mocked(settingsApi.getShellSettings).mockRejectedValue(new Error('Network error'))

    await useSettingsStore.getState().loadShellSettings()

    const state = useSettingsStore.getState()
    expect(state.locationName).toBe(DEFAULT_LOCATION_NAME)
    expect(state.shellStatus).toBe('error')
    expect(i18n.changeLanguage).not.toHaveBeenCalled()
  })
})
