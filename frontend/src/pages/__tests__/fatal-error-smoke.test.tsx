import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import axios from 'axios'
import DraftEntryPage from '../drafts/DraftEntryPage'
import ReceivingPage from '../receiving/ReceivingPage'
import ApprovalsPage from '../approvals/ApprovalsPage'
import { approvalsApi } from '../../api/approvals'
import { draftsApi } from '../../api/drafts'
import { ordersApi } from '../../api/orders'
import { renderWithProviders } from '../../utils/test-utils'

vi.mock('../../api/approvals', () => ({
  approvalsApi: {
    getPending: vi.fn(),
  },
}))

vi.mock('../../api/drafts', () => ({
  draftsApi: {
    getTodayLines: vi.fn(),
  },
}))

vi.mock('../../api/orders', () => ({
  ordersApi: {
    getReceivingDetail: vi.fn(),
    listOpenOrdersPreload: vi.fn(),
  },
}))

const createNetworkError = () => {
  const error = new axios.AxiosError('Network Error')
  error.response = undefined // Network errors have no response object mapped
  return error
}

describe('Fatal State Smoke Tests', () => {
  it('DraftEntryPage shows Croatian connection error on 500/network load failure', async () => {
    vi.mocked(draftsApi.getTodayLines).mockRejectedValue(createNetworkError())

    renderWithProviders(<DraftEntryPage />)

    await waitFor(() => {
      expect(screen.getByText(/Greška povezivanja\./i)).toBeInTheDocument()
    })
  })

  it('ReceivingPage shows Croatian connection error on 500/network load failure', async () => {
    vi.mocked(ordersApi.listOpenOrdersPreload).mockRejectedValue(createNetworkError())

    renderWithProviders(<ReceivingPage />)

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Greška povezivanja/i })).toBeInTheDocument()
    })
  })

  it('ApprovalsPage shows Croatian connection error on 500/network load failure', async () => {
    vi.mocked(approvalsApi.getPending).mockRejectedValue(createNetworkError())

    renderWithProviders(<ApprovalsPage />)

    await waitFor(() => {
      expect(screen.getByText(/Greška povezivanja\./i)).toBeInTheDocument()
    })
  })
})
