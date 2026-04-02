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

// Converts the SettingsRoleDisplayName[] arrays returned by both GET /settings/shell
// (all authenticated roles) and GET /settings/roles (ADMIN-only) into the store's
// internal role-label map while filling missing roles from defaults.
function toRoleDisplayNameMap(
  roles: SettingsRoleDisplayName[]
): Record<SystemRole, string> {
  const nextMap = { ...DEFAULT_ROLE_DISPLAY_NAMES }

  roles.forEach((role) => {
    nextMap[role.role] = role.display_name
  })

  return nextMap
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
      // Use the minimal read-only shell endpoint — accessible to all
      // authenticated roles, not only ADMIN.
      const shell = await runWithRetry(() => settingsApi.getShellSettings())

      await i18n.changeLanguage(shell.default_language).catch(() => undefined)

      set({
        locationName: shell.location_name || DEFAULT_LOCATION_NAME,
        roleDisplayNames: toRoleDisplayNameMap(shell.role_display_names),
        shellStatus: 'ready',
      })
    } catch {
      // Network/auth failure — safe defaults remain in place. AppShell can
      // offer a retry, but the shell must not hard-block authenticated routing.
      set({ shellStatus: 'error' })
    }
  },

  // Used by SettingsPage after ADMIN saves General settings so the sidebar
  // reflects the new location name and language immediately.
  applyGeneralSettings: async (general) => {
    await i18n.changeLanguage(general.default_language).catch(() => undefined)
    set({
      locationName: general.location_name || DEFAULT_LOCATION_NAME,
      shellStatus: 'ready',
    })
  },

  // Used by SettingsPage after ADMIN saves Role Display Names so the sidebar
  // reflects the new labels immediately without a full shell reload.
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
