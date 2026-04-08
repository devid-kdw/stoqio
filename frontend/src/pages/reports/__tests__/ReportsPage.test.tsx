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
  },
}))

vi.mock('../../../api/articles', () => ({
  articlesApi: {
    lookupCategories: vi.fn(),
    lookupUoms: vi.fn(),
  },
}))

vi.mock('../../../utils/toasts', () => ({
  showErrorToast: vi.fn(),
  showSuccessToast: vi.fn(),
}))

const renderComponent = () => {
  return renderWithProviders(<ReportsPage />)
}

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    useAuthStore.setState({ user: { id: 1, role: 'ADMIN' } as any })
    
    // Mock successful initial API loads
    vi.mocked(articlesApi.lookupCategories).mockResolvedValue([])
    vi.mocked(articlesApi.lookupUoms).mockResolvedValue([])
    vi.mocked(reportsApi.getStockOverview).mockResolvedValue({
      period: { date_from: '', date_to: '', months: 1 },
      items: [],
      total: 0,
      page: 1,
      per_page: 100,
      summary: {
        warehouse_total_value: 0
      }
    })
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
})
