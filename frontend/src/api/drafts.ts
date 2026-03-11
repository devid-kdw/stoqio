import client from './client'

/** A single draft line, as returned by the backend. */
export interface DraftLine {
  id: number
  draft_group_id: number
  article_id: number
  article_no: string | null
  description: string | null
  batch_id: number | null
  batch_code: string | null
  quantity: number
  uom: string
  employee_id_ref: string | null
  status: 'DRAFT' | 'APPROVED' | string
  source: string
  created_by: string | null
  created_at: string | null
}

export interface DraftGroup {
  id: number
  group_number: string
  status: string
  operational_date: string
  draft_note: string | null
}

export interface GetDraftsResponse {
  items: DraftLine[]
  draft_group: DraftGroup | null
}

export interface AddDraftPayload {
  article_id: number
  batch_id?: number | null
  quantity: number
  uom: string
  employee_id_ref?: string
  draft_note?: string
  source: 'manual'
  client_event_id: string
}

export interface UpdateDraftPayload {
  quantity: number
}

export interface UpdateDraftGroupPayload {
  draft_note: string
}

export const draftsApi = {
  /**
   * Fetch today's draft lines (newest first).
   * GET /api/v1/drafts?date=today
   */
  getTodayLines: async (): Promise<GetDraftsResponse> => {
    const response = await client.get<GetDraftsResponse>('/drafts', {
      params: { date: 'today' },
    })
    return response.data
  },

  /**
   * Add a new draft line.
   * POST /api/v1/drafts — returns 201 on creation, 200 on idempotent replay.
   */
  addLine: async (payload: AddDraftPayload): Promise<DraftLine> => {
    const response = await client.post<DraftLine>('/drafts', payload)
    return response.data
  },

  /**
   * Update quantity of an existing draft line.
   * PATCH /api/v1/drafts/{id}
   */
  updateLine: async (id: number, payload: UpdateDraftPayload): Promise<DraftLine> => {
    const response = await client.patch<DraftLine>(`/drafts/${id}`, payload)
    return response.data
  },

  /**
   * Update today's shared draft note.
   * PATCH /api/v1/drafts/group
   */
  updateGroup: async (payload: UpdateDraftGroupPayload): Promise<DraftGroup> => {
    const response = await client.patch<DraftGroup>('/drafts/group', payload)
    return response.data
  },

  /**
   * Delete a draft line.
   * DELETE /api/v1/drafts/{id}
   */
  deleteLine: async (id: number): Promise<void> => {
    await client.delete(`/drafts/${id}`)
  },
}
