import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import axios, { type InternalAxiosRequestConfig } from 'axios'
import DraftEntryPage from '../drafts/DraftEntryPage'
import ReceivingPage from '../receiving/ReceivingPage'
import DraftGroupCard from '../approvals/components/DraftGroupCard'
import { approvalsApi, type ApprovalsDraftGroup } from '../../api/approvals'
import { draftsApi, type GetDraftsResponse, type GetMyLinesResponse } from '../../api/drafts'
import { ordersApi, type OrdersListResponse } from '../../api/orders'
import { renderWithProviders } from '../../utils/test-utils'

vi.mock('../../utils/setup', async () => {
  const actual = await vi.importActual<typeof import('../../utils/setup')>('../../utils/setup')
  return {
    ...actual,
    fetchSetupStatus: vi.fn(),
  }
})

vi.mock('../../store/authStore', () => {
  return {
    useAuthStore: Object.assign(
      vi.fn((selector) => {
        const state = {
          user: { id: 1, role: 'ADMIN', default_language: 'hr' },
          accessToken: 'token',
          setSetupStatus: vi.fn(),
          resetSetupStatus: vi.fn(),
        }
        if (selector) return selector(state)
        return state
      }),
      {
        setState: vi.fn(),
        getState: vi.fn(() => ({
          user: { id: 1, role: 'ADMIN', default_language: 'hr' },
          accessToken: 'token',
          setSetupStatus: vi.fn(),
          resetSetupStatus: vi.fn(),
        }))
      }
    )
  }
})

vi.mock('../../api/approvals', () => ({
  approvalsApi: {
    getPending: vi.fn(),
    getDetail: vi.fn(),
  },
}))

vi.mock('../../api/drafts', () => ({
  draftsApi: {
    getTodayLines: vi.fn(),
    getMyLines: vi.fn(),
  },
}))

vi.mock('../../api/orders', () => ({
  ordersApi: {
    listOpenOrdersPreload: vi.fn(),
  },
}))

describe('Localized Copy Smoke Tests', () => {
  const createHttpError = (message: string) => {
    const config = { headers: new axios.AxiosHeaders() } as InternalAxiosRequestConfig
    const error = new axios.AxiosError('HTTP Error')
    error.response = {
      data: { message },
      status: 400,
      statusText: 'Bad Request',
      headers: {},
      config,
    }
    return error
  }

  it('DraftEntryPage shows localized errors on empty submit', async () => {
    const todayLinesResponse: GetDraftsResponse = { items: [], draft_group: null }
    const myLinesResponse: GetMyLinesResponse = { lines: [] }

    vi.mocked(draftsApi.getTodayLines).mockResolvedValue(todayLinesResponse)
    vi.mocked(draftsApi.getMyLines).mockResolvedValue(myLinesResponse)

    renderWithProviders(<DraftEntryPage />)

    await waitFor(() => {
      expect(screen.queryByText(/Učitavanje/i)).not.toBeInTheDocument()
    })

    const submitBtn = screen.getByRole('button', { name: /Dodaj/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText('Broj artikla je obavezan.')).toBeInTheDocument()
      expect(screen.getByText('Količina je obavezna.')).toBeInTheDocument()
    })
  })

  it('DraftGroupCard shows localized error on detail fetch failure', async () => {
    // Component renders expanded rows, which triggers fetchDetail
    vi.mocked(approvalsApi.getDetail).mockRejectedValue(createHttpError('Server said no.'))

    const summary: ApprovalsDraftGroup = {
      draft_group_id: 1,
      group_number: 'DG-2026-0001',
      operational_date: '2026-04-02',
      status: 'PENDING',
      draft_note: null,
      total_entries: 5,
    }

    renderWithProviders(<DraftGroupCard summary={summary} isHistory={false} />)

    // Click the expansion toggle
    const toggleBtn = screen.getByRole('button', { name: /2026/ }) 
    fireEvent.click(toggleBtn)

    await waitFor(() => {
      expect(screen.getByText('Nema dostupnog sadržaja.')).toBeInTheDocument()
    })
  })

  it('ReceivingPage shows localized errors on empty adhoc submit', async () => {
    const openOrdersResponse: OrdersListResponse = {
      items: [],
      total: 0,
      page: 1,
      per_page: 200,
    }

    vi.mocked(ordersApi.listOpenOrdersPreload).mockResolvedValue(openOrdersResponse)

    renderWithProviders(<ReceivingPage />)

    await waitFor(() => {
      expect(screen.queryByText(/Učitavanje/i)).not.toBeInTheDocument()
    })

    // switch to ad-hoc mode in segmented control
    const adhocRadio = screen.getByRole('radio', { name: /Ad-hoc zaprimanje/i })
    fireEvent.click(adhocRadio)

    // click submit
    const submitBtn = screen.getByRole('button', { name: /Potvrdi zaprimanje/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByText('Broj artikla je obavezan.')).toBeInTheDocument()
      expect(screen.getByText('Količina je obavezna.')).toBeInTheDocument()
    })
  })
})
