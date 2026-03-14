import { create } from 'zustand'

import i18n from '../i18n'
import {
  settingsApi,
  type SettingsGeneral,
  type SettingsRoleDisplayName,
  type SystemRole,
} from '../api/settings'
import { runWithRetry } from '../utils/http'

export const DEFAULT_LOCATION_NAME = 'STOQIO'
export const DEFAULT_ROLE_DISPLAY_NAMES: Record<SystemRole, string> = {
  ADMIN: 'Admin',
  MANAGER: 'Menadžment',
  WAREHOUSE_STAFF: 'Administracija',
  VIEWER: 'Kontrola',
  OPERATOR: 'Operater',
}

type ShellSettingsStatus = 'idle' | 'loading' | 'ready' | 'error'

interface SettingsStoreState {
  locationName: string
  roleDisplayNames: Record<SystemRole, string>
  shellStatus: ShellSettingsStatus
  loadShellSettings: (force?: boolean) => Promise<void>
  applyGeneralSettings: (general: SettingsGeneral) => Promise<void>
  applyRoleDisplayNames: (roles: SettingsRoleDisplayName[]) => void
  resetShellSettings: () => void
}

function toRoleDisplayNameMap(
  roles: SettingsRoleDisplayName[]
): Record<SystemRole, string> {
  const nextMap = { ...DEFAULT_ROLE_DISPLAY_NAMES }

  roles.forEach((role) => {
    nextMap[role.role] = role.display_name
  })

  return nextMap
}

export const useSettingsStore = create<SettingsStoreState>((set, get) => ({
  locationName: DEFAULT_LOCATION_NAME,
  roleDisplayNames: { ...DEFAULT_ROLE_DISPLAY_NAMES },
  shellStatus: 'idle',

  loadShellSettings: async (force = false) => {
    const { shellStatus } = get()
    if (!force && (shellStatus === 'loading' || shellStatus === 'ready')) {
      return
    }

    set({ shellStatus: 'loading' })

    try {
      const [general, roles] = await runWithRetry(() =>
        Promise.all([settingsApi.getGeneral(), settingsApi.getRoles()])
      )

      await i18n.changeLanguage(general.default_language).catch(() => undefined)

      set({
        locationName: general.location_name || DEFAULT_LOCATION_NAME,
        roleDisplayNames: toRoleDisplayNameMap(roles),
        shellStatus: 'ready',
      })
    } catch {
      set({ shellStatus: 'error' })
    }
  },

  applyGeneralSettings: async (general) => {
    await i18n.changeLanguage(general.default_language).catch(() => undefined)
    set({
      locationName: general.location_name || DEFAULT_LOCATION_NAME,
      shellStatus: 'ready',
    })
  },

  applyRoleDisplayNames: (roles) => {
    set({
      roleDisplayNames: toRoleDisplayNameMap(roles),
      shellStatus: 'ready',
    })
  },

  resetShellSettings: () =>
    set({
      locationName: DEFAULT_LOCATION_NAME,
      roleDisplayNames: { ...DEFAULT_ROLE_DISPLAY_NAMES },
      shellStatus: 'idle',
    }),
}))
