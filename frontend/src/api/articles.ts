import client from './client'

function getPdfFilename(contentDisposition: string | undefined, fallbackName: string): string {
  if (!contentDisposition) {
    return fallbackName
  }

  const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
  if (!filenameMatch?.[1]) {
    return fallbackName
  }

  return filenameMatch[1]
}

function sanitizeFilenamePart(value: string): string {
  return value.replace(/[^A-Za-z0-9._-]+/g, '_').replace(/^_+|_+$/g, '') || 'barcode'
}

function triggerDownload(blob: Blob, filename: string): void {
  const objectUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(objectUrl)
}

/** A batch returned inline with the article lookup response (FEFO-ordered). */
export interface ArticleBatch {
  id: number
  batch_code: string
  expiry_date: string
}

/**
 * Article lookup response shape.
 * Batches are returned inline when has_batch = true (DEC-FE-004).
 */
export interface ArticleLookupResult {
  id: number
  article_no: string
  description: string
  /** UOM code string, e.g. "kg", "kom" */
  base_uom: string
  has_batch: boolean
  /** Present only when has_batch = true, ordered by expiry_date ASC (FEFO). */
  batches?: ArticleBatch[]
}

export type ReorderStatus = 'NORMAL' | 'YELLOW' | 'RED' | string

export interface WarehouseArticleListItem {
  id: number
  article_no: string
  description: string
  category_id: number | null
  category_key: string | null
  category_label_hr: string | null
  base_uom: string | null
  stock_total: number
  surplus_total: number
  reorder_threshold: number | null
  reorder_status: ReorderStatus
  is_active: boolean
}

export interface WarehouseArticlesListResponse {
  items: WarehouseArticleListItem[]
  total: number
  page: number
  per_page: number
}

export interface ArticleDetailBatch {
  id: number
  batch_code: string
  barcode: string | null
  expiry_date: string | null
  stock_total: number
  surplus_total: number
}

export interface ArticleSupplierLink {
  id: number
  supplier_id: number
  supplier_name: string | null
  supplier_internal_code: string | null
  supplier_article_code: string | null
  last_price: number | null
  last_ordered_at: string | null
  is_preferred: boolean
  is_active: boolean | null
}

export interface ArticleAliasItem {
  id: number
  alias: string
  normalized: string
}

export interface WarehouseArticleDetail {
  id: number
  article_no: string
  description: string
  category_id: number | null
  category_key: string | null
  category_label_hr: string | null
  base_uom: string | null
  pack_size: number | null
  pack_uom: string | null
  barcode: string | null
  manufacturer: string | null
  manufacturer_art_number: string | null
  has_batch: boolean
  initial_average_price: number | null
  reorder_threshold: number | null
  reorder_coverage_days: number | null
  density: number
  stock_total: number
  surplus_total: number
  reorder_status: ReorderStatus
  pending_draft_count: number
  has_pending_drafts: boolean
  is_active: boolean
  created_at: string | null
  updated_at: string | null
  batches?: ArticleDetailBatch[]
  suppliers: ArticleSupplierLink[]
  aliases: ArticleAliasItem[]
}

export interface ArticleTransactionItem {
  id: number
  occurred_at: string | null
  type: string
  quantity: number
  uom: string
  batch_code: string | null
  reference: string | null
  reference_type: string | null
  reference_id: number | null
  user: string | null
}

export interface ArticleTransactionsResponse {
  items: ArticleTransactionItem[]
  total: number
  page: number
  per_page: number
}

export interface ArticleCategoryLookupItem {
  id: number
  key: string
  label_hr: string
}

export interface ArticleUomLookupItem {
  code: string
  label_hr: string
  decimal_display: boolean
}

export interface SupplierLookupItem {
  id: number
  name: string
  internal_code: string
}

export interface SupplierLookupPreloadResponse {
  items: SupplierLookupItem[]
  total: number
  page: number
  per_page: number
}

export interface ArticleSupplierMutationPayload {
  supplier_id: number
  supplier_article_code?: string | null
  is_preferred: boolean
}

export interface ArticleMutationPayload {
  article_no: string
  description: string
  category_id: number
  base_uom: string
  pack_size?: number | null
  pack_uom?: string | null
  barcode?: string | null
  manufacturer?: string | null
  manufacturer_art_number?: string | null
  has_batch: boolean
  initial_average_price: number | null
  reorder_threshold?: number | null
  reorder_coverage_days?: number | null
  density?: number
  is_active: boolean
  suppliers: ArticleSupplierMutationPayload[]
}

// ---------------------------------------------------------------------------
// Article statistics (Wave 1 Phase 13)
// ---------------------------------------------------------------------------

export type StatPeriod = 30 | 90 | 180

export interface ArticleStatWeekBucket {
  /** ISO date string of the Monday that starts this week bucket */
  week_start: string
  quantity: number
}

export interface ArticleStatPricePoint {
  /** ISO date string */
  date: string
  unit_price: number
}

export interface ArticleStatStockPoint {
  /** ISO date string */
  date: string
  quantity: number
}

export interface ArticleStatsResponse {
  outbound_by_week: ArticleStatWeekBucket[]
  inbound_by_week: ArticleStatWeekBucket[]
  price_history: ArticleStatPricePoint[]
  // Returned by the backend but not rendered in this wave.
  stock_history: ArticleStatStockPoint[]
}

// ---------------------------------------------------------------------------
// Label print response (Phase 8 Wave 2 — direct printer support)
// ---------------------------------------------------------------------------

export interface LabelPrintResponse {
  /** Server-side confirmation message */
  message: string
}

export interface BarcodeGenerationResponse {
  barcode: string
  generated: boolean
}

export const articlesApi = {
  /**
   * Lookup an article by article_no or barcode.
   * GET /api/v1/articles?q={query}
   *
   * Returns the matched ArticleLookupResult or throws AxiosError with 404
   * when no article is found.
   */
  lookup: async (q: string): Promise<ArticleLookupResult> => {
    const response = await client.get<ArticleLookupResult>('/articles', {
      params: { q },
    })
    return response.data
  },

  listWarehouse: async (params: {
    page: number
    perPage: number
    q?: string
    category?: string | null
    includeInactive?: boolean
  }): Promise<WarehouseArticlesListResponse> => {
    const response = await client.get<WarehouseArticlesListResponse>('/articles', {
      params: {
        page: params.page,
        per_page: params.perPage,
        q: params.q?.trim() ? params.q.trim() : undefined,
        category: params.category ?? undefined,
        include_inactive: params.includeInactive ?? false,
      },
    })
    return response.data
  },

  getDetail: async (articleId: number): Promise<WarehouseArticleDetail> => {
    const response = await client.get<WarehouseArticleDetail>(`/articles/${articleId}`)
    return response.data
  },

  create: async (payload: ArticleMutationPayload): Promise<WarehouseArticleDetail> => {
    const response = await client.post<WarehouseArticleDetail>('/articles', payload)
    return response.data
  },

  update: async (
    articleId: number,
    payload: ArticleMutationPayload
  ): Promise<WarehouseArticleDetail> => {
    const response = await client.put<WarehouseArticleDetail>(`/articles/${articleId}`, payload)
    return response.data
  },

  deactivate: async (articleId: number): Promise<WarehouseArticleDetail> => {
    const response = await client.patch<WarehouseArticleDetail>(`/articles/${articleId}/deactivate`)
    return response.data
  },

  listTransactions: async (
    articleId: number,
    page: number,
    perPage: number
  ): Promise<ArticleTransactionsResponse> => {
    const response = await client.get<ArticleTransactionsResponse>(
      `/articles/${articleId}/transactions`,
      {
        params: {
          page,
          per_page: perPage,
        },
      }
    )
    return response.data
  },

  downloadBarcode: async (articleId: number, fallbackArticleNo?: string): Promise<void> => {
    const response = await client.get<Blob>(`/articles/${articleId}/barcode`, {
      responseType: 'blob',
    })

    const fallbackName = `wms_article_${sanitizeFilenamePart(
      fallbackArticleNo ?? `article-${articleId}`
    )}_barcode.pdf`
    const filename = getPdfFilename(response.headers['content-disposition'], fallbackName)

    triggerDownload(response.data, filename)
  },

  downloadBatchBarcode: async (
    batchId: number,
    options?: { articleNo?: string; batchCode?: string }
  ): Promise<void> => {
    const response = await client.get<Blob>(`/batches/${batchId}/barcode`, {
      responseType: 'blob',
    })

    const fallbackName = `wms_batch_${sanitizeFilenamePart(
      options?.articleNo ?? 'article'
    )}_${sanitizeFilenamePart(options?.batchCode ?? `batch-${batchId}`)}_barcode.pdf`
    const filename = getPdfFilename(response.headers['content-disposition'], fallbackName)

    triggerDownload(response.data, filename)
  },

  generateBarcode: async (articleId: number): Promise<BarcodeGenerationResponse> => {
    const response = await client.post<BarcodeGenerationResponse>(
      `/articles/${articleId}/barcode/generate`
    )
    return response.data
  },

  generateBatchBarcode: async (batchId: number): Promise<BarcodeGenerationResponse> => {
    const response = await client.post<BarcodeGenerationResponse>(
      `/batches/${batchId}/barcode/generate`
    )
    return response.data
  },

  lookupCategories: async (): Promise<ArticleCategoryLookupItem[]> => {
    const response = await client.get<ArticleCategoryLookupItem[]>('/articles/lookups/categories')
    return response.data
  },

  lookupUoms: async (): Promise<ArticleUomLookupItem[]> => {
    const response = await client.get<ArticleUomLookupItem[]>('/articles/lookups/uoms')
    return response.data
  },

  lookupSuppliers: async (): Promise<SupplierLookupItem[]> => {
    const response = await client.get<SupplierLookupItem[]>('/suppliers')
    return response.data
  },

  lookupSuppliersPreload: async (): Promise<SupplierLookupPreloadResponse> => {
    const response = await client.get<SupplierLookupPreloadResponse>('/suppliers', {
      params: { per_page: 200 },
    })
    return response.data
  },

  createAlias: async (articleId: number, alias: string): Promise<ArticleAliasItem> => {
    const response = await client.post<ArticleAliasItem>(`/articles/${articleId}/aliases`, { alias })
    return response.data
  },

  deleteAlias: async (articleId: number, aliasId: number): Promise<void> => {
    await client.delete(`/articles/${articleId}/aliases/${aliasId}`)
  },

  /**
   * Fetch article statistics for the given period.
   * GET /api/v1/articles/{id}/stats?period={days}
   *
   * Lazy — call only when the Statistics section is first opened.
   * Valid period values: 30, 90, 180.
   */
  getStats: async (articleId: number, period: StatPeriod): Promise<ArticleStatsResponse> => {
    const response = await client.get<ArticleStatsResponse>(`/articles/${articleId}/stats`, {
      params: { period },
    })
    return response.data
  },

  /**
   * Send a direct-print request for an article label to the configured label printer.
   * POST /api/v1/articles/{id}/barcode/print
   * ADMIN only.
   */
  printArticleLabel: async (articleId: number): Promise<LabelPrintResponse> => {
    const response = await client.post<LabelPrintResponse>(`/articles/${articleId}/barcode/print`)
    return response.data
  },

  /**
   * Send a direct-print request for a batch label to the configured label printer.
   * POST /api/v1/batches/{id}/barcode/print
   * ADMIN only.
   */
  printBatchLabel: async (batchId: number): Promise<LabelPrintResponse> => {
    const response = await client.post<LabelPrintResponse>(`/batches/${batchId}/barcode/print`)
    return response.data
  },
}
