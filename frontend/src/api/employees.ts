import client from './client'

export interface Employee {
  id: number
  employee_id: string
  first_name: string
  last_name: string
  department: string | null
  job_title: string | null
  is_active: boolean
  created_at: string | null
}

export interface EmployeeListResponse {
  items: Employee[]
  total: number
  page: number
  per_page: number
}

export interface EmployeeMutationPayload {
  employee_id: string
  first_name: string
  last_name: string
  department?: string | null
  job_title?: string | null
  is_active?: boolean
}

export interface QuotaRow {
  article_id: number | null
  article_no: string | null
  description: string | null
  category_id: number | null
  category_label_hr: string | null
  quota: number
  received: number
  remaining: number
  uom: string
  enforcement: string
  status: 'OK' | 'WARNING' | 'EXCEEDED'
}

export interface QuotaOverviewResponse {
  year: number
  quotas: QuotaRow[]
}

export interface IssuanceHistoryItem {
  id: number
  issued_at: string | null
  article_id: number | null
  article_no: string | null
  description: string | null
  batch_id: number | null
  batch_code: string | null
  quantity: number
  uom: string
  issued_by: string | null
  note: string | null
}

export interface IssuanceHistoryResponse {
  items: IssuanceHistoryItem[]
  total: number
  page: number
  per_page: number
}

export interface IssuanceBatch {
  id: number
  batch_code: string
  expiry_date: string
  available: number
}

export interface IssuanceArticleLookupItem {
  id: number
  article_no: string
  description: string
  base_uom: string
  decimal_display: boolean
  has_batch: boolean
  batches?: IssuanceBatch[]
}

export interface IssuanceCheckPayload {
  article_id: number
  quantity: number
  batch_id?: number | null
}

export interface IssuanceCheckResult {
  status: 'OK' | 'WARNING' | 'NO_QUOTA' | 'BLOCKED'
  message: string
  quota: number | null
  received: number | null
  remaining: number | null
  uom: string | null
  enforcement: string | null
}

export interface CreateIssuancePayload {
  article_id: number
  quantity: number
  batch_id?: number | null
  note?: string | null
}

export interface CreateIssuanceResult {
  id: number
  employee_id: number
  article_id: number
  article_no: string
  description: string
  batch_id: number | null
  batch_code: string | null
  quantity: number
  uom: string
  issued_by: string
  issued_at: string
  note: string | null
  warning?: { code: string; message: string; check: IssuanceCheckResult }
}

export const employeesApi = {
  list: async (params: {
    page: number
    perPage: number
    q?: string
    includeInactive?: boolean
  }): Promise<EmployeeListResponse> => {
    const response = await client.get<EmployeeListResponse>('/employees', {
      params: {
        page: params.page,
        per_page: params.perPage,
        q: params.q?.trim() || undefined,
        include_inactive: params.includeInactive ?? false,
      },
    })
    return response.data
  },

  get: async (id: number): Promise<Employee> => {
    const response = await client.get<Employee>(`/employees/${id}`)
    return response.data
  },

  create: async (payload: EmployeeMutationPayload): Promise<Employee> => {
    const response = await client.post<Employee>('/employees', payload)
    return response.data
  },

  update: async (id: number, payload: Partial<EmployeeMutationPayload>): Promise<Employee> => {
    const response = await client.put<Employee>(`/employees/${id}`, payload)
    return response.data
  },

  deactivate: async (id: number): Promise<Employee> => {
    const response = await client.patch<Employee>(`/employees/${id}/deactivate`)
    return response.data
  },

  getQuotas: async (id: number): Promise<QuotaOverviewResponse> => {
    const response = await client.get<QuotaOverviewResponse>(`/employees/${id}/quotas`)
    return response.data
  },

  listIssuances: async (
    id: number,
    page: number,
    perPage: number
  ): Promise<IssuanceHistoryResponse> => {
    const response = await client.get<IssuanceHistoryResponse>(`/employees/${id}/issuances`, {
      params: { page, per_page: perPage },
    })
    return response.data
  },

  lookupArticles: async (q: string): Promise<IssuanceArticleLookupItem[]> => {
    const response = await client.get<IssuanceArticleLookupItem[]>(
      '/employees/lookups/articles',
      { params: { q } }
    )
    return response.data
  },

  checkIssuance: async (
    id: number,
    payload: IssuanceCheckPayload
  ): Promise<IssuanceCheckResult> => {
    const response = await client.post<IssuanceCheckResult>(
      `/employees/${id}/issuances/check`,
      payload
    )
    return response.data
  },

  createIssuance: async (
    id: number,
    payload: CreateIssuancePayload
  ): Promise<CreateIssuanceResult> => {
    const response = await client.post<CreateIssuanceResult>(
      `/employees/${id}/issuances`,
      payload
    )
    return response.data
  },
}
