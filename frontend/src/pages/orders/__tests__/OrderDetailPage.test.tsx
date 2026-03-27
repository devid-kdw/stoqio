import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import OrderDetailPage from '../OrderDetailPage'
import { ordersApi } from '../../../api/orders'
import * as toasts from '../../../utils/toasts'
import axios from 'axios'
import { renderWithProviders } from '../../../utils/test-utils'

// Mock dependencies
vi.mock('../../../api/orders', () => ({
  ordersApi: {
    getDetail: vi.fn(),
    downloadPdf: vi.fn(),
  },
}))

vi.mock('../../../utils/toasts', () => ({
  showErrorToast: vi.fn(),
  showSuccessToast: vi.fn(),
}))

const renderComponent = () => {
  return renderWithProviders(<OrderDetailPage />, { route: '/orders/1', path: '/orders/:id' })
}

describe('OrderDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock successful initial order fetch
    vi.mocked(ordersApi.getDetail).mockResolvedValue({
      id: 1,
      order_number: 'ORD-0001',
      status: 'OPEN',
      supplier_id: 1,
      supplier_name: 'Test Supplier',
      supplier_address: '123 Test St',
      supplier_confirmation_number: null,
      note: null,
      total_value: 100,
      lines: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  })

  it('preserves the backend blob error message on PDF download failure', async () => {
    // Setup a mocked rejection with a Blob containing JSON payload
    const errorPayload = { message: 'PDF_GENERATION_FAILED details here' }
    const blob = new Blob([JSON.stringify(errorPayload)], { type: 'application/json' })
    const axiosError = new axios.AxiosError('Error')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    axiosError.response = { status: 400, data: blob, statusText: '', headers: {}, config: {} as any }
    
    vi.mocked(ordersApi.downloadPdf).mockRejectedValue(axiosError)

    renderComponent()

    // Wait for the page to load
    expect(await screen.findByText('ORD-0001')).toBeInTheDocument()

    // Find and click the PDF download button
    const pdfButton = screen.getByRole('button', { name: /generiraj pdf/i })
    fireEvent.click(pdfButton)

    // Wait for the showErrorToast to be called and verify the message text survives
    await vi.waitFor(() => {
      expect(toasts.showErrorToast).toHaveBeenCalledWith('PDF_GENERATION_FAILED details here')
    })
  })
})
