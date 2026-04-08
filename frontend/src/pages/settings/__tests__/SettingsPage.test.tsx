import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'

import SettingsPage from '../SettingsPage'
import { articlesApi } from '../../../api/articles'
import { authApi } from '../../../api/auth'
import { ordersApi } from '../../../api/orders'
import { settingsApi } from '../../../api/settings'
import { renderWithProviders } from '../../../utils/test-utils'

vi.mock('../../../store/authStore', () => {
  const state = {
    user: { id: 1, role: 'ADMIN', default_language: 'hr' },
    accessToken: 'token',
    updateUser: vi.fn(),
  }

  return {
    useAuthStore: Object.assign(
      vi.fn((selector) => (selector ? selector(state) : state)),
      {
        setState: vi.fn(),
        getState: vi.fn(() => state),
      }
    ),
  }
})

vi.mock('../../../store/settingsStore', () => {
  const state = {
    applyGeneralSettings: vi.fn(),
    applyRoleDisplayNames: vi.fn(),
  }

  return {
    DEFAULT_ROLE_DISPLAY_NAMES: {
      ADMIN: 'Admin',
      MANAGER: 'Menadžment',
      WAREHOUSE_STAFF: 'Administracija',
      VIEWER: 'Kontrola',
      OPERATOR: 'Operater',
    },
    useSettingsStore: Object.assign(
      vi.fn((selector) => (selector ? selector(state) : state)),
      {
        setState: vi.fn(),
        getState: vi.fn(() => state),
      }
    ),
  }
})

vi.mock('../../../api/articles', () => ({
  articlesApi: {
    lookupCategories: vi.fn(),
    lookupUoms: vi.fn(),
  },
}))

vi.mock('../../../api/auth', () => ({
  authApi: {
    me: vi.fn(),
  },
}))

vi.mock('../../../api/orders', () => ({
  ordersApi: {
    lookupArticles: vi.fn(),
  },
}))

vi.mock('../../../api/settings', () => ({
  settingsApi: {
    getGeneral: vi.fn(),
    getRoles: vi.fn(),
    getUoms: vi.fn(),
    getCategories: vi.fn(),
    getQuotas: vi.fn(),
    getBarcode: vi.fn(),
    getExport: vi.fn(),
    listSuppliers: vi.fn(),
    getUsers: vi.fn(),
  },
}))

describe('SettingsPage localized copy', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    vi.mocked(settingsApi.getGeneral).mockResolvedValue({
      location_name: 'HAM',
      timezone: 'Europe/Berlin',
      default_language: 'hr',
    })
    vi.mocked(settingsApi.getRoles).mockResolvedValue([
      { role: 'ADMIN', display_name: 'Admin' },
      { role: 'MANAGER', display_name: 'Menadžment' },
      { role: 'WAREHOUSE_STAFF', display_name: 'Administracija' },
      { role: 'VIEWER', display_name: 'Kontrola' },
      { role: 'OPERATOR', display_name: 'Operater' },
    ])
    vi.mocked(settingsApi.getUoms).mockResolvedValue([])
    vi.mocked(settingsApi.getCategories).mockResolvedValue([])
    vi.mocked(settingsApi.getQuotas).mockResolvedValue([])
    vi.mocked(settingsApi.getBarcode).mockResolvedValue({
      barcode_format: 'Code128',
      barcode_printer: '',
      label_printer_ip: '',
      label_printer_port: 9100,
      label_printer_model: 'zebra_zpl',
    })
    vi.mocked(settingsApi.getExport).mockResolvedValue({
      export_format: 'generic',
    })
    vi.mocked(settingsApi.listSuppliers).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 10,
    })
    vi.mocked(settingsApi.getUsers).mockResolvedValue([])
    vi.mocked(articlesApi.lookupCategories).mockResolvedValue([])
    vi.mocked(articlesApi.lookupUoms).mockResolvedValue([])
    vi.mocked(authApi.me).mockResolvedValue({
      id: 1,
      username: 'admin',
      role: 'ADMIN',
      is_active: true,
    })
    vi.mocked(ordersApi.lookupArticles).mockResolvedValue({ items: [] })
  })

  it('renders Croatian settings section titles and save labels', async () => {
    renderWithProviders(<SettingsPage />)

    await waitFor(() => {
      expect(screen.queryByText(/Učitavanje/i)).not.toBeInTheDocument()
    })

    expect(await screen.findByRole('heading', { name: '1. Općenito' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '2. Role' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '3. Katalog jedinica mjere' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '4. Kategorije artikala' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '5. Kvote' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '6. Barkodovi' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '7. Izvoz' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '8. Dobavljači' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '9. Korisnici' })).toBeInTheDocument()

    expect(screen.getByRole('button', { name: 'Spremi opće postavke' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Spremi nazive rola' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Spremi postavke barkoda' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Spremi postavke izvoza' })).toBeInTheDocument()
  })
})
