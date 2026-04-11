import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'

import IdentifierPage from '../IdentifierPage'
import { identifierApi } from '../../../api/identifier'
import { useAuthStore } from '../../../store/authStore'
import { renderWithProviders } from '../../../utils/test-utils'

vi.mock('../../../api/identifier', () => ({
  identifierApi: {
    search: vi.fn(),
    submitReport: vi.fn(),
    listReports: vi.fn(),
    resolveReport: vi.fn(),
  },
}))

function setAuthenticatedUser(role: string) {
  useAuthStore.setState({
    user: {
      id: 1,
      username: `${role.toLowerCase()}.user`,
      role,
    },
    accessToken: 'token',
    refreshToken: 'refresh',
    isAuthenticated: true,
    setupStatus: 'complete',
    authStatus: 'authenticated',
  })
}

async function performSearch(term: string) {
  fireEvent.change(
    screen.getByPlaceholderText('Broj artikla, opis, alias ili barkod'),
    { target: { value: term } }
  )

  await waitFor(() => {
    expect(identifierApi.search).toHaveBeenCalledWith(term)
  })
}

describe('IdentifierPage role-aware result rendering', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    useAuthStore.getState().clearAuth()
  })

  it('renders exact stock, ordered quantity, and purchase price fields for admin/manager-shaped results', async () => {
    setAuthenticatedUser('ADMIN')
    vi.mocked(identifierApi.search).mockResolvedValueOnce({
      total: 1,
      items: [
        {
          id: 10,
          article_no: 'ADM-001',
          description: 'Admin test artikl',
          category_label_hr: 'Boje',
          base_uom: 'kg',
          decimal_display: true,
          matched_via: 'article_no',
          matched_alias: null,
          stock: 9.5,
          is_ordered: true,
          ordered_quantity: 12.25,
          latest_purchase_price: 4.3,
        },
      ],
    })

    renderWithProviders(<IdentifierPage />)

    await performSearch('ADM-001')

    expect(await screen.findByText('ADM-001')).toBeInTheDocument()
    expect(screen.getByText('Na stanju')).toBeInTheDocument()
    expect(screen.getByText('Naručena količina')).toBeInTheDocument()
    expect(screen.getByText('Zadnja nabavna cijena')).toBeInTheDocument()
    expect(screen.getByText(/9(?:,|\.)50 kg/)).toBeInTheDocument()
    expect(screen.getByText(/12(?:,|\.)25 kg/)).toBeInTheDocument()
    expect(screen.getByText(/4(?:,|\.)30/)).toBeInTheDocument()
    expect(screen.queryByText('Dostupnost')).not.toBeInTheDocument()
    expect(screen.queryByText('Višak')).not.toBeInTheDocument()
  })

  it('renders boolean-only availability fields for warehouse staff/viewer-shaped results', async () => {
    setAuthenticatedUser('WAREHOUSE_STAFF')
    vi.mocked(identifierApi.search).mockResolvedValueOnce({
      total: 1,
      items: [
        {
          id: 11,
          article_no: 'AVL-001',
          description: 'Availability test artikl',
          category_label_hr: 'Potrošni materijal',
          base_uom: 'kom',
          decimal_display: false,
          matched_via: 'alias',
          matched_alias: 'AVL ALIAS',
          in_stock: false,
          is_ordered: true,
        },
      ],
    })

    renderWithProviders(<IdentifierPage />)

    await performSearch('AVL-001')

    expect(await screen.findByText('AVL-001')).toBeInTheDocument()
    expect(screen.getByText('Dostupnost')).toBeInTheDocument()
    expect(screen.getByText('Nije na stanju')).toBeInTheDocument()
    expect(screen.getByText('Naručeno')).toBeInTheDocument()
    expect(screen.getByText('Alias: AVL ALIAS')).toBeInTheDocument()
    expect(screen.queryByText('Na stanju')).not.toBeInTheDocument()
    expect(screen.queryByText('Naručena količina')).not.toBeInTheDocument()
    expect(screen.queryByText('Zadnja nabavna cijena')).not.toBeInTheDocument()
    expect(screen.queryByText('Višak')).not.toBeInTheDocument()
  })
})
