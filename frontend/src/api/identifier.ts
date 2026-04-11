import client from './client'

export type IdentifierMatchedVia = 'article_no' | 'description' | 'alias' | 'barcode' | string
export type IdentifierReportStatus = 'OPEN' | 'RESOLVED' | string
export type IdentifierQueueStatusFilter = 'open' | 'resolved'

interface IdentifierSearchItemBase {
  id: number
  article_no: string
  description: string
  category_label_hr: string | null
  base_uom: string | null
  decimal_display: boolean | null
  matched_via: IdentifierMatchedVia
  matched_alias: string | null
}

/** Returned for ADMIN and MANAGER — exact quantities and purchase price visible. */
export interface IdentifierSearchQuantityItem extends IdentifierSearchItemBase {
  stock: number
  is_ordered: boolean
  ordered_quantity: number
  latest_purchase_price: number | null
}

/** Returned for WAREHOUSE_STAFF and VIEWER — boolean availability only, no price. */
export interface IdentifierSearchAvailabilityItem extends IdentifierSearchItemBase {
  in_stock: boolean
  is_ordered: boolean
}

export type IdentifierSearchItem =
  | IdentifierSearchQuantityItem
  | IdentifierSearchAvailabilityItem

export interface IdentifierSearchResponse {
  items: IdentifierSearchItem[]
  total: number
}

export interface MissingArticleReportItem {
  id: number
  search_term: string
  report_count: number
  status: IdentifierReportStatus
  created_at: string | null
  resolution_note: string | null
  resolved_at: string | null
}

export interface MissingArticleReportQueueResponse {
  items: MissingArticleReportItem[]
  total: number
}

export interface SubmitMissingArticleReportPayload {
  search_term: string
}

export interface ResolveMissingArticleReportPayload {
  resolution_note?: string | null
}

export const identifierApi = {
  search: async (query: string): Promise<IdentifierSearchResponse> => {
    const response = await client.get<IdentifierSearchResponse>('/identifier', {
      params: { q: query },
    })
    return response.data
  },

  submitReport: async (
    payload: SubmitMissingArticleReportPayload
  ): Promise<MissingArticleReportItem> => {
    const response = await client.post<MissingArticleReportItem>('/identifier/reports', payload)
    return response.data
  },

  listReports: async (
    status: IdentifierQueueStatusFilter = 'open'
  ): Promise<MissingArticleReportQueueResponse> => {
    const response = await client.get<MissingArticleReportQueueResponse>('/identifier/reports', {
      params: { status },
    })
    return response.data
  },

  resolveReport: async (
    reportId: number,
    payload: ResolveMissingArticleReportPayload
  ): Promise<MissingArticleReportItem> => {
    const response = await client.post<MissingArticleReportItem>(
      `/identifier/reports/${reportId}/resolve`,
      payload
    )
    return response.data
  },
}
