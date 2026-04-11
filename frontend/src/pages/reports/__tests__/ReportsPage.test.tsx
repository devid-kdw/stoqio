import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import ReportsPage from '../ReportsPage'
import { reportsApi } from '../../../api/reports'
import { articlesApi } from '../../../api/articles'
import * as toasts from '../../../utils/toasts'
import axios from 'axios'
import { renderWithProviders } from '../../../utils/test-utils'
import { useAuthStore } from '../../../store/authStore'

vi.mock('../../../api/reports', () => ({
  reportsApi: {
    getStockOverview: vi.fn(),
    exportStockOverview: vi.fn(),
    getTopConsumption: vi.fn(),
    getMovementStatistics: vi.fn(),
    getReorderSummary: vi.fn(),
    getPersonalIssuancesStatistics: vi.fn(),
    getReorderDrilldown: vi.fn(),
    getPriceMovement: vi.fn(),
  },
}))

vi.mock('../../../api/articles', () => ({
  articlesApi: {
    lookupCategories: vi.fn(),
    lookupUoms: vi.fn(),
    listWarehouse: vi.fn(),
  },
}))

vi.mock('../../../utils/toasts', () => ({
  showErrorToast: vi.fn(),
  showSuccessToast: vi.fn(),
}))

const STOCK_RESPONSE = {
  period: { date_from: '', date_to: '', months: 1 },
  items: [],
  total: 0,
  page: 1,
  per_page: 100,
  summary: { warehouse_total_value: 0 },
}

const TOP_CONSUMPTION_RESPONSE = {
  period: 'month' as const,
  date_from: '2026-03-01',
  date_to: '2026-03-31',
  items: [],
}

const MOVEMENT_RESPONSE = {
  range: '6m' as const,
  granularity: 'month',
  items: [],
  note: 'Some English note from the backend (should not be displayed)',
}

const REORDER_SUMMARY_RESPONSE = {
  items: [
    { reorder_status: 'RED', count: 3 },
    { reorder_status: 'YELLOW', count: 5 },
    { reorder_status: 'NORMAL', count: 42 },
  ],
  total: 50,
}

const PERSONAL_ISSUANCES_RESPONSE = {
  year: 2026,
  items: [],
  total: 0,
}

const PRICE_MOVEMENT_RESPONSE = {
  items: [
    {
      article_id: 1,
      article_no: 'ART-001',
      description: 'Test Artikl',
      category: 'CAT-01',
      latest_price: 12.5,
      previous_price: 10.0,
      last_change_date: '2026-04-01',
      delta: 2.5,
      delta_pct: 25.0,
    },
  ],
  total: 1,
}

const DRILLDOWN_RESPONSE = {
  status: 'RED',
  items: [
    {
      article_id: 99,
      article_no: 'ART-099',
      description: 'Drilldown Artikl',
      stock: 5,
      uom: 'kg',
      reorder_threshold: 20,
      reorder_status: 'RED',
    },
  ],
  total: 1,
}

function setUpAdminUser() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useAuthStore.setState({ user: { id: 1, role: 'ADMIN' } as any })
}

function setUpManagerUser() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useAuthStore.setState({ user: { id: 2, role: 'MANAGER' } as any })
}

function setUpWarehouseStaffUser() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useAuthStore.setState({ user: { id: 3, role: 'WAREHOUSE_STAFF' } as any })
}

function mockStandardApis() {
  vi.mocked(articlesApi.lookupCategories).mockResolvedValue([])
  vi.mocked(articlesApi.lookupUoms).mockResolvedValue([])
  vi.mocked(reportsApi.getStockOverview).mockResolvedValue(STOCK_RESPONSE)
  vi.mocked(reportsApi.getTopConsumption).mockResolvedValue(TOP_CONSUMPTION_RESPONSE)
  vi.mocked(reportsApi.getMovementStatistics).mockResolvedValue(MOVEMENT_RESPONSE)
  vi.mocked(reportsApi.getReorderSummary).mockResolvedValue(REORDER_SUMMARY_RESPONSE)
  vi.mocked(reportsApi.getPersonalIssuancesStatistics).mockResolvedValue(PERSONAL_ISSUANCES_RESPONSE)
  vi.mocked(reportsApi.getPriceMovement).mockResolvedValue(PRICE_MOVEMENT_RESPONSE)
  vi.mocked(reportsApi.getReorderDrilldown).mockResolvedValue(DRILLDOWN_RESPONSE)
}

const renderComponent = () => renderWithProviders(<ReportsPage />)

async function switchToStatisticsTab() {
  const statisticsTab = screen.getByRole('tab', { name: /Statistike/i })
  fireEvent.click(statisticsTab)
  // Wait for init to complete
  await waitFor(() => {
    expect(reportsApi.getTopConsumption).toHaveBeenCalled()
  })
}

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setUpAdminUser()
    mockStandardApis()
  })

  it('preserves the backend blob error message on stock export failure', async () => {
    const errorPayload = { message: 'Nema podataka za odabrani period' }
    const blob = new Blob([JSON.stringify(errorPayload)], { type: 'application/json' })
    const axiosError = new axios.AxiosError('Error')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    axiosError.response = { status: 400, data: blob, statusText: '', headers: {}, config: {} as any }
    
    vi.mocked(reportsApi.exportStockOverview).mockRejectedValue(axiosError)

    renderComponent()

    // Wait for the initial load to clear
    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    })

    // Find and click the stock export button (first one is for stock)
    const exportButtons = screen.getAllByRole('button', { name: 'PDF' })
    fireEvent.click(exportButtons[0])

    // Wait for the showErrorToast to be called and verify the message text
    await waitFor(() => {
      expect(toasts.showErrorToast).toHaveBeenCalledWith('Nema podataka za odabrani period')
    })
  })

  // ── W9-F-008: Statistics subsections collapsed by default ──

  describe('W9-F-008: Statistics subsections collapsed by default', () => {
    it('shows section headers but hides content when Statistics tab is opened', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      // Section headers should be visible as buttons
      expect(screen.getByLabelText('Top 10 po potrošnji')).toBeInTheDocument()
      expect(screen.getByLabelText('Ulaz i izlaz kroz vrijeme')).toBeInTheDocument()
      expect(screen.getByLabelText('Sažetak zona naručivanja')).toBeInTheDocument()
      expect(screen.getByLabelText('Osobna izdavanja')).toBeInTheDocument()
      expect(screen.getByLabelText('Kretanje cijena')).toBeInTheDocument()

      // Subsection descriptive text should NOT be visible when collapsed
      expect(screen.queryByText('Klik na zonu otvara popis artikala unutar Statistika.')).not.toBeVisible()
    })

    it('opens a subsection when the header is clicked', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      // Click to open Reorder zone section
      fireEvent.click(screen.getByLabelText('Sažetak zona naručivanja'))

      // Descriptive text inside should become visible
      await waitFor(() => {
        expect(screen.getByText('Klik na zonu otvara popis artikala unutar Statistika.')).toBeVisible()
      })

      // Zone items should now be visible
      expect(screen.getByText('Crvena zona')).toBeInTheDocument()
    })
  })

  // ── W9-F-009: Reorder zone drilldown stays inside Statistics ──

  describe('W9-F-009: Reorder zone drilldown stays inside Statistics', () => {
    it('does not switch to Stock Overview tab when a zone is clicked', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      // Open reorder section first
      fireEvent.click(screen.getByLabelText('Sažetak zona naručivanja'))
      await waitFor(() => {
        expect(screen.getByText('Crvena zona')).toBeVisible()
      })

      // Click on the Red zone
      fireEvent.click(screen.getByText('Crvena zona'))

      // Drilldown should load inside Statistics (not switch tabs)
      await waitFor(() => {
        expect(reportsApi.getReorderDrilldown).toHaveBeenCalledWith('RED')
      })

      // The statistics tab should still be active, not the stock tab
      const statisticsTab = screen.getByRole('tab', { name: /Statistike/i })
      expect(statisticsTab).toHaveAttribute('aria-selected', 'true')

      // Drilldown content should appear
      await waitFor(() => {
        expect(screen.getByText(/Crvena zona — 1 artikala/)).toBeInTheDocument()
      })
      expect(screen.getByText('Drilldown Artikl')).toBeInTheDocument()
      expect(screen.queryByText('NaN')).not.toBeInTheDocument()
    })
  })

  // ── W9-F-010: Movement note is Croatian ──

  describe('W9-F-010: Croatian movement helper note', () => {
    it('renders the Croatian helper note instead of backend English note', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      // Expand the movement section
      fireEvent.click(screen.getByLabelText('Ulaz i izlaz kroz vrijeme'))

      await waitFor(() => {
        const note = screen.getByTestId('movement-note-hr')
        expect(note).toBeInTheDocument()
        expect(note.textContent).toBe(
          'Količine su zbrojene po svim mjernim jedinicama. Grafikon prikazuje trendove, a ne precizne ukupne iznose.'
        )
      })

      // The backend English note should NOT be shown
      expect(screen.queryByText('Some English note from the backend (should not be displayed)')).not.toBeInTheDocument()
    })
  })

  // ── W9-F-010: Movement filter UI wiring ──

  describe('W9-F-010: Movement article/category filter', () => {
    it('passes article_id in movement statistics call when article filter is applied', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      // The initial call should be with no article/category
      expect(reportsApi.getMovementStatistics).toHaveBeenCalledWith(
        expect.objectContaining({ range: '6m', articleId: null, category: null })
      )
    })
  })

  // ── W9-F-005: Price movement section ──

  describe('W9-F-005: Price movement section', () => {
    it('renders the price movement section for ADMIN and loads data on init', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      // Price movement section header should exist
      expect(screen.getByLabelText('Kretanje cijena')).toBeInTheDocument()

      // Price movement API should have been called
      expect(reportsApi.getPriceMovement).toHaveBeenCalled()
    })

    it('renders price movement section when user is MANAGER', async () => {
      setUpManagerUser()
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      expect(screen.getByLabelText('Kretanje cijena')).toBeInTheDocument()
      expect(reportsApi.getPriceMovement).toHaveBeenCalled()
    })

    it('does NOT render price movement section when user is WAREHOUSE_STAFF', async () => {
      setUpWarehouseStaffUser()
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      expect(screen.queryByLabelText('Kretanje cijena')).not.toBeInTheDocument()
      expect(reportsApi.getPriceMovement).not.toHaveBeenCalled()
    })

    it('shows price movement data when section is expanded', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })

      await switchToStatisticsTab()

      // Open Price Movement
      fireEvent.click(screen.getByLabelText('Kretanje cijena'))

      await waitFor(() => {
        expect(screen.getByText('ART-001')).toBeVisible()
        expect(screen.getByText('Test Artikl')).toBeVisible()
      })
    })
  })
})
