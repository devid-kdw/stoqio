import client from './client'

export interface ReceiptPayloadLine {
  order_line_id: number | null
  article_id?: number
  quantity?: number
  uom?: string
  batch_code?: string | null
  expiry_date?: string | null
  skip?: boolean
}

export interface CreateReceiptPayload {
  delivery_note_number: string
  note: string | null
  lines: ReceiptPayloadLine[]
}

export interface CreateReceiptResponse {
  receiving_ids: number[]
  stock_updated: Array<{
    article_id: number
    article_no: string | null
    quantity_added: number
    uom: string
  }>
}

export interface ReceivingHistoryItem {
  id: number
  received_at: string | null
  order_number: string
  article_id: number
  article_no: string | null
  description: string | null
  quantity: number
  uom: string
  batch_code: string | null
  delivery_note_number: string | null
  received_by: string | null
}

export interface ReceivingHistoryResponse {
  items: ReceivingHistoryItem[]
  total: number
  page: number
  per_page: number
}

export const receivingApi = {
  /**
   * Submit an order-linked or ad-hoc receipt.
   * POST /api/v1/receiving
   */
  submit: async (payload: CreateReceiptPayload): Promise<CreateReceiptResponse> => {
    const response = await client.post<CreateReceiptResponse>('/receiving', payload)
    return response.data
  },

  /**
   * Fetch receiving history ordered newest first.
   * GET /api/v1/receiving?page=1&per_page=50
   */
  getHistory: async (page = 1, perPage = 50): Promise<ReceivingHistoryResponse> => {
    const response = await client.get<ReceivingHistoryResponse>('/receiving', {
      params: { page, per_page: perPage },
    })
    return response.data
  },
}
