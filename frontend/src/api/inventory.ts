import client from './client'

export type InventoryCountType = 'REGULAR' | 'OPENING'

export interface ShortageApprovalSummary {
  total: number
  approved: number
  rejected: number
  pending: number
}

export interface InventoryCountSummary {
  total_lines: number
  no_change: number
  surplus_added: number
  shortage_drafts_created: number
  opening_stock_set?: number
}

export interface InventoryCountLine {
  line_id: number
  article_id: number | null
  article_no: string | null
  description: string | null
  batch_id: number | null
  batch_code: string | null
  expiry_date: string | null
  system_quantity: number
  counted_quantity: number | null
  difference: number | null
  uom: string
  decimal_display: boolean
  resolution:
    | 'NO_CHANGE'
    | 'SURPLUS_ADDED'
    | 'SHORTAGE_DRAFT_CREATED'
    | 'OPENING_STOCK_SET'
    | null
}

export interface ActiveCount {
  id: number
  status: 'IN_PROGRESS'
  type: InventoryCountType
  started_by: string | null
  started_at: string | null
  completed_at: null
  total_lines: number
  counted_lines: number
  lines: InventoryCountLine[]
}

export interface HistoryItem {
  id: number
  status: 'COMPLETED'
  type: InventoryCountType
  started_by: string | null
  started_at: string | null
  completed_at: string | null
  total_lines: number
  discrepancies: number
  shortage_drafts_summary?: ShortageApprovalSummary
}

export interface HistoryResponse {
  items: HistoryItem[]
  total: number
  page: number
  per_page: number
  opening_count_exists: boolean
}

export interface CountDetail {
  id: number
  status: string
  type: InventoryCountType
  started_by: string | null
  started_at: string | null
  completed_at: string | null
  summary: InventoryCountSummary
  shortage_drafts_summary?: ShortageApprovalSummary
  lines: InventoryCountLine[]
}

export interface OpeningBatchLinePayload {
  article_id: number
  batch_code: string
  expiry_date: string
  counted_quantity: number
}

export const inventoryApi = {
  /** GET /api/v1/inventory/active — returns null when no count is IN_PROGRESS */
  getActive: async (): Promise<ActiveCount | null> => {
    const response = await client.get<{ active: null } | ActiveCount>('/inventory/active')
    const data = response.data
    // Backend returns { "active": null } when none, or the count object directly
    if ('active' in data) return null
    return data
  },

  /** GET /api/v1/inventory?page=1&per_page=50 — paginated COMPLETED counts */
  history: async (page: number, perPage: number): Promise<HistoryResponse> => {
    const response = await client.get<HistoryResponse>('/inventory', {
      params: { page, per_page: perPage },
    })
    return response.data
  },

  /** POST /api/v1/inventory — start a new count */
  start: async (type?: InventoryCountType): Promise<void> => {
    await client.post('/inventory', type ? { type } : undefined)
  },

  /** GET /api/v1/inventory/{id} — read-only detail for any count */
  detail: async (id: number): Promise<CountDetail> => {
    const response = await client.get<CountDetail>(`/inventory/${id}`)
    return response.data
  },

  /** PATCH /api/v1/inventory/{id}/lines/{line_id} — save counted quantity */
  updateLine: async (
    countId: number,
    lineId: number,
    countedQuantity: number
  ): Promise<InventoryCountLine> => {
    const response = await client.patch<InventoryCountLine>(
      `/inventory/${countId}/lines/${lineId}`,
      { counted_quantity: countedQuantity }
    )
    return response.data
  },

  /** POST /api/v1/inventory/{id}/complete */
  complete: async (countId: number): Promise<{ id: number }> => {
    const response = await client.post<{ id: number }>(`/inventory/${countId}/complete`)
    return response.data
  },

  /** POST /api/v1/inventory/{count_id}/opening-batch-lines */
  addOpeningBatchLine: async (
    countId: number,
    payload: OpeningBatchLinePayload
  ): Promise<ActiveCount> => {
    const response = await client.post<ActiveCount>(
      `/inventory/${countId}/opening-batch-lines`,
      payload
    )
    return response.data
  },
}
