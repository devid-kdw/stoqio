import client from './client'

export type ReportReorderStatus = 'NORMAL' | 'YELLOW' | 'RED' | string
export type ReportTransactionType =
  | 'STOCK_RECEIPT'
  | 'OUTBOUND'
  | 'SURPLUS_CONSUMED'
  | 'STOCK_CONSUMED'
  | 'INVENTORY_ADJUSTMENT'
  | 'PERSONAL_ISSUE'
  | string
export type ReportExportFormat = 'xlsx' | 'pdf'
export type TopConsumptionPeriod = 'week' | 'month' | 'year'
export type MovementRange = '3m' | '6m' | '12m'

export interface StockOverviewPeriod {
  date_from: string
  date_to: string
  months: number
}

export interface StockOverviewItem {
  article_id: number
  article_no: string
  description: string
  supplier_name: string | null
  stock: number
  surplus: number
  total_available: number
  uom: string | null
  inbound: number
  outbound: number
  avg_monthly_consumption: number
  coverage_months: number | null
  reorder_threshold: number | null
  reorder_status: ReportReorderStatus
}

export interface StockOverviewResponse {
  period: StockOverviewPeriod
  items: StockOverviewItem[]
  total: number
}

export interface SurplusReportItem {
  id: number
  article_id: number
  article_no: string | null
  description: string | null
  batch_id: number | null
  batch_code: string | null
  expiry_date: string | null
  surplus_qty: number
  uom: string | null
  discovered: string | null
}

export interface SurplusReportResponse {
  items: SurplusReportItem[]
  total: number
}

export interface TransactionLogItem {
  id: number
  occurred_at: string | null
  article_id: number | null
  article_no: string | null
  description: string | null
  type: ReportTransactionType
  quantity: number
  uom: string | null
  batch_code: string | null
  reference: string | null
  user: string | null
}

export interface TransactionLogResponse {
  items: TransactionLogItem[]
  total: number
  page: number
  per_page: number
}

export interface TopConsumptionItem {
  article_id: number
  article_no: string
  description: string
  outbound: number
  uom: string | null
}

export interface TopConsumptionResponse {
  period: TopConsumptionPeriod
  date_from: string
  date_to: string
  items: TopConsumptionItem[]
}

export interface MovementStatisticsItem {
  bucket: string
  label: string
  period_start: string
  period_end: string
  inbound: number
  outbound: number
}

export interface MovementStatisticsResponse {
  range: MovementRange
  granularity: 'week' | 'month' | string
  items: MovementStatisticsItem[]
  note: string
}

export interface ReorderSummaryItem {
  reorder_status: ReportReorderStatus
  count: number
}

export interface ReorderSummaryResponse {
  items: ReorderSummaryItem[]
  total: number
}

export interface PersonalIssuanceStatisticsItem {
  employee_id: number
  employee_name: string | null
  job_title: string | null
  article_id: number
  article_no: string
  article: string
  quantity_issued: number
  quota: number | null
  remaining: number | null
  uom: string | null
  quota_uom: string | null
}

export interface PersonalIssuancesStatisticsResponse {
  year: number
  items: PersonalIssuanceStatisticsItem[]
  total: number
}

export interface StockOverviewQuery {
  dateFrom: string
  dateTo: string
  category?: string | null
  reorderOnly?: boolean
}

export interface TransactionLogQuery {
  articleId?: number | null
  dateFrom?: string | null
  dateTo?: string | null
  txTypes?: ReportTransactionType[]
  page?: number
  perPage?: number
}

function getFilename(contentDisposition: string | undefined, fallbackName: string): string {
  if (!contentDisposition) {
    return fallbackName
  }

  const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
  if (!filenameMatch?.[1]) {
    return fallbackName
  }

  return filenameMatch[1]
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

function buildStockOverviewParams(
  query: StockOverviewQuery,
  extra?: Record<string, string>
): URLSearchParams {
  const params = new URLSearchParams()
  params.set('date_from', query.dateFrom)
  params.set('date_to', query.dateTo)

  if (query.category) {
    params.set('category', query.category)
  }

  if (query.reorderOnly) {
    params.set('reorder_only', 'true')
  }

  if (extra) {
    Object.entries(extra).forEach(([key, value]) => {
      params.set(key, value)
    })
  }

  return params
}

function buildTransactionParams(
  query: TransactionLogQuery,
  extra?: Record<string, string>
): URLSearchParams {
  const params = new URLSearchParams()

  if (query.articleId) {
    params.set('article_id', String(query.articleId))
  }

  if (query.dateFrom) {
    params.set('date_from', query.dateFrom)
  }

  if (query.dateTo) {
    params.set('date_to', query.dateTo)
  }

  if (typeof query.page === 'number') {
    params.set('page', String(query.page))
  }

  if (typeof query.perPage === 'number') {
    params.set('per_page', String(query.perPage))
  }

  query.txTypes?.forEach((type) => {
    params.append('tx_type', type)
  })

  if (extra) {
    Object.entries(extra).forEach(([key, value]) => {
      params.set(key, value)
    })
  }

  return params
}

async function downloadReport(
  path: string,
  params: URLSearchParams,
  fallbackFilename: string
): Promise<void> {
  const response = await client.get<Blob>(path, {
    params,
    responseType: 'blob',
  })

  const filename = getFilename(response.headers['content-disposition'], fallbackFilename)
  triggerDownload(response.data, filename)
}

export const reportsApi = {
  getStockOverview: async (query: StockOverviewQuery): Promise<StockOverviewResponse> => {
    const response = await client.get<StockOverviewResponse>('/reports/stock-overview', {
      params: buildStockOverviewParams(query),
    })
    return response.data
  },

  exportStockOverview: async (
    format: ReportExportFormat,
    query: StockOverviewQuery
  ): Promise<void> =>
    downloadReport(
      '/reports/stock-overview/export',
      buildStockOverviewParams(query, { format }),
      `wms_stock_overview.${format}`
    ),

  getSurplus: async (): Promise<SurplusReportResponse> => {
    const response = await client.get<SurplusReportResponse>('/reports/surplus')
    return response.data
  },

  exportSurplus: async (format: ReportExportFormat): Promise<void> => {
    const params = new URLSearchParams()
    params.set('format', format)

    return downloadReport('/reports/surplus/export', params, `wms_surplus.${format}`)
  },

  getTransactions: async (query: TransactionLogQuery): Promise<TransactionLogResponse> => {
    const response = await client.get<TransactionLogResponse>('/reports/transactions', {
      params: buildTransactionParams(query),
    })
    return response.data
  },

  exportTransactions: async (
    format: ReportExportFormat,
    query: TransactionLogQuery
  ): Promise<void> =>
    downloadReport(
      '/reports/transactions/export',
      buildTransactionParams(query, { format }),
      `wms_transactions.${format}`
    ),

  getTopConsumption: async (period: TopConsumptionPeriod): Promise<TopConsumptionResponse> => {
    const response = await client.get<TopConsumptionResponse>(
      '/reports/statistics/top-consumption',
      {
        params: { period },
      }
    )
    return response.data
  },

  getMovementStatistics: async (range: MovementRange): Promise<MovementStatisticsResponse> => {
    const response = await client.get<MovementStatisticsResponse>('/reports/statistics/movement', {
      params: { range },
    })
    return response.data
  },

  getReorderSummary: async (): Promise<ReorderSummaryResponse> => {
    const response = await client.get<ReorderSummaryResponse>('/reports/statistics/reorder-summary')
    return response.data
  },

  getPersonalIssuancesStatistics: async (): Promise<PersonalIssuancesStatisticsResponse> => {
    const response = await client.get<PersonalIssuancesStatisticsResponse>(
      '/reports/statistics/personal-issuances'
    )
    return response.data
  },
}
