import client from './client'

export interface ApprovalsOperatorEntry {
  id: number
  created_at: string | null
  operator: string | null
  quantity: number
  employee_id_ref: string | null
  status: string
}

export interface ApprovalsAggregatedRow {
  line_id: number
  article_id: number
  article_no: string | null
  description: string | null
  batch_id: number | null
  batch_code: string | null
  total_quantity: number
  uom: string
  status: 'PENDING' | 'APPROVED' | 'PARTIAL' | 'REJECTED' | string
  entry_count: number
  entries: ApprovalsOperatorEntry[]
}

export interface ApprovalsDraftGroup {
  draft_group_id: number
  group_number: string
  operational_date: string
  status: 'PENDING' | 'APPROVED' | 'PARTIAL' | 'REJECTED' | string
  draft_note: string | null
  total_entries: number
  rows?: ApprovalsAggregatedRow[]
}

export interface GetApprovalsResponse {
  items: ApprovalsDraftGroup[]
  total: number
  page: number
  per_page: number
}

export interface ApproveSingleResponse {
  line_id: number
  article_id: number | null
  article_no: string | null
  approved_quantity: number
  uom: string
  stock_after: number
  surplus_consumed: number
  stock_consumed: number
  reorder_warning: boolean
}

export interface ApproveAllResponse {
  approved: ApproveSingleResponse[]
  skipped: number[]
}

export interface RejectResponse {
  status: string
  reason: string
}

export interface UpdateQuantityPayload {
  quantity: number
}

export interface RejectPayload {
  reason: string
}

export const approvalsApi = {
  /**
   * Fetch pending draft groups.
   */
  getPending: async (): Promise<GetApprovalsResponse> => {
    const response = await client.get<GetApprovalsResponse>('/approvals', {
      params: { status: 'pending' },
    })
    return response.data
  },

  /**
   * Fetch history draft groups.
   */
  getHistory: async (): Promise<GetApprovalsResponse> => {
    const response = await client.get<GetApprovalsResponse>('/approvals', {
      params: { status: 'history' },
    })
    return response.data
  },

  /**
   * Fetch detail of a specific draft group.
   */
  getDetail: async (draftGroupId: number): Promise<ApprovalsDraftGroup> => {
    const response = await client.get<ApprovalsDraftGroup>(`/approvals/${draftGroupId}`)
    return response.data
  },

  /**
   * Update the aggregated quantity of a pending line.
   */
  updateLine: async (
    draftGroupId: number,
    lineId: number,
    payload: UpdateQuantityPayload
  ): Promise<ApprovalsDraftGroup> => {
    const response = await client.patch<ApprovalsDraftGroup>(
      `/approvals/${draftGroupId}/lines/${lineId}`,
      payload
    )
    return response.data
  },

  /**
   * Approve a single aggregated line.
   */
  approveLine: async (draftGroupId: number, lineId: number): Promise<ApproveSingleResponse> => {
    const response = await client.post<ApproveSingleResponse>(
      `/approvals/${draftGroupId}/lines/${lineId}/approve`
    )
    return response.data
  },

  /**
   * Approve all pending lines in a draft group.
   */
  approveAll: async (draftGroupId: number): Promise<ApproveAllResponse> => {
    const response = await client.post<ApproveAllResponse>(`/approvals/${draftGroupId}/approve`)
    return response.data
  },

  /**
   * Reject a single aggregated line.
   */
  rejectLine: async (
    draftGroupId: number,
    lineId: number,
    payload: RejectPayload
  ): Promise<RejectResponse> => {
    const response = await client.post<RejectResponse>(
      `/approvals/${draftGroupId}/lines/${lineId}/reject`,
      payload
    )
    return response.data
  },

  /**
   * Reject an entire draft group.
   */
  rejectDraft: async (draftGroupId: number, payload: RejectPayload): Promise<RejectResponse> => {
    const response = await client.post<RejectResponse>(
      `/approvals/${draftGroupId}/reject`,
      payload
    )
    return response.data
  },
}
