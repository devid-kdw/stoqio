import client from './client'

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
}
