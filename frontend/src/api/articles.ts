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
  reorder_threshold?: number | null
  reorder_coverage_days?: number | null
  density?: number
  is_active: boolean
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

  lookupCategories: async (): Promise<ArticleCategoryLookupItem[]> => {
    const response = await client.get<ArticleCategoryLookupItem[]>('/articles/lookups/categories')
    return response.data
  },

  lookupUoms: async (): Promise<ArticleUomLookupItem[]> => {
    const response = await client.get<ArticleUomLookupItem[]>('/articles/lookups/uoms')
    return response.data
  },
}
