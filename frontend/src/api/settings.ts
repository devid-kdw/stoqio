import client from './client'

export type SystemRole =
  | 'ADMIN'
  | 'MANAGER'
  | 'WAREHOUSE_STAFF'
  | 'VIEWER'
  | 'OPERATOR'

export type SettingsLanguage = 'hr' | 'en' | 'de' | 'hu' | string
export type SettingsQuotaScope =
  | 'GLOBAL_ARTICLE_OVERRIDE'
  | 'JOB_TITLE_CATEGORY_DEFAULT'
  | string
export type SettingsQuotaEnforcement = 'WARN' | 'BLOCK' | string
export type SettingsBarcodeFormat = 'EAN-13' | 'Code128' | string
export type SettingsExportFormat = 'generic' | 'sap' | string

export interface SettingsGeneral {
  location_name: string
  timezone: string
  default_language: SettingsLanguage
}

export interface SettingsRoleDisplayName {
  role: SystemRole
  display_name: string
}

export interface SettingsUom {
  id: number
  code: string
  label_hr: string
  label_en: string | null
  decimal_display: boolean
}

export interface CreateSettingsUomPayload {
  code: string
  label_hr: string
  label_en?: string | null
  decimal_display?: boolean
}

export interface SettingsCategory {
  id: number
  key: string
  label_hr: string
  label_en: string | null
  is_personal_issue: boolean
}

export interface UpdateSettingsCategoryPayload {
  label_hr?: string
  label_en?: string | null
  is_personal_issue?: boolean
}

export interface SettingsQuota {
  id: number
  scope: SettingsQuotaScope
  job_title: string | null
  article_id: number | null
  article_no: string | null
  article_description: string | null
  category_id: number | null
  category_key: string | null
  category_label_hr: string | null
  category_label_en: string | null
  quantity: number
  uom: string
  enforcement: SettingsQuotaEnforcement
  reset_month: number
}

export interface SettingsQuotaPayload {
  scope?: SettingsQuotaScope
  job_title?: string | null
  category_id?: number | null
  article_id?: number | null
  employee_id?: number | null
  quantity: number | string
  uom: string
  reset_month?: number | string | null
  enforcement?: SettingsQuotaEnforcement
}

export interface SettingsQuotaDeleteResponse {
  id: number
  deleted: boolean
}

export interface SettingsBarcode {
  barcode_format: SettingsBarcodeFormat
  barcode_printer: string
}

export interface SettingsExport {
  export_format: SettingsExportFormat
}

export interface SettingsSupplier {
  id: number
  internal_code: string
  name: string
  contact_person: string | null
  phone: string | null
  email: string | null
  address: string | null
  iban: string | null
  note: string | null
  is_active: boolean
  created_at: string | null
}

export interface SettingsSuppliersResponse {
  items: SettingsSupplier[]
  total: number
  page: number
  per_page: number
}

export interface CreateSettingsSupplierPayload {
  internal_code: string
  name: string
  contact_person?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  iban?: string | null
  note?: string | null
}

export interface UpdateSettingsSupplierPayload {
  name?: string
  contact_person?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  iban?: string | null
  note?: string | null
}

export interface SettingsUser {
  id: number
  username: string
  role: SystemRole
  role_display_name: string
  is_active: boolean
  created_at: string | null
}

export interface CreateSettingsUserPayload {
  username: string
  password: string
  role: SystemRole
  is_active?: boolean
}

export interface UpdateSettingsUserPayload {
  role?: SystemRole
  is_active?: boolean
  password?: string
}

export const settingsApi = {
  getGeneral: async (): Promise<SettingsGeneral> => {
    const response = await client.get<SettingsGeneral>('/settings/general')
    return response.data
  },

  updateGeneral: async (payload: SettingsGeneral): Promise<SettingsGeneral> => {
    const response = await client.put<SettingsGeneral>('/settings/general', payload)
    return response.data
  },

  getRoles: async (): Promise<SettingsRoleDisplayName[]> => {
    const response = await client.get<SettingsRoleDisplayName[]>('/settings/roles')
    return response.data
  },

  updateRoles: async (
    payload: SettingsRoleDisplayName[]
  ): Promise<SettingsRoleDisplayName[]> => {
    const response = await client.put<SettingsRoleDisplayName[]>('/settings/roles', payload)
    return response.data
  },

  getUoms: async (): Promise<SettingsUom[]> => {
    const response = await client.get<SettingsUom[]>('/settings/uom')
    return response.data
  },

  createUom: async (payload: CreateSettingsUomPayload): Promise<SettingsUom> => {
    const response = await client.post<SettingsUom>('/settings/uom', payload)
    return response.data
  },

  getCategories: async (): Promise<SettingsCategory[]> => {
    const response = await client.get<SettingsCategory[]>('/settings/categories')
    return response.data
  },

  updateCategory: async (
    categoryId: number,
    payload: UpdateSettingsCategoryPayload
  ): Promise<SettingsCategory> => {
    const response = await client.put<SettingsCategory>(
      `/settings/categories/${categoryId}`,
      payload
    )
    return response.data
  },

  getQuotas: async (): Promise<SettingsQuota[]> => {
    const response = await client.get<SettingsQuota[]>('/settings/quotas')
    return response.data
  },

  createQuota: async (payload: SettingsQuotaPayload): Promise<SettingsQuota> => {
    const response = await client.post<SettingsQuota>('/settings/quotas', payload)
    return response.data
  },

  updateQuota: async (
    quotaId: number,
    payload: SettingsQuotaPayload
  ): Promise<SettingsQuota> => {
    const response = await client.put<SettingsQuota>(`/settings/quotas/${quotaId}`, payload)
    return response.data
  },

  deleteQuota: async (quotaId: number): Promise<SettingsQuotaDeleteResponse> => {
    const response = await client.delete<SettingsQuotaDeleteResponse>(
      `/settings/quotas/${quotaId}`
    )
    return response.data
  },

  getBarcode: async (): Promise<SettingsBarcode> => {
    const response = await client.get<SettingsBarcode>('/settings/barcode')
    return response.data
  },

  updateBarcode: async (payload: SettingsBarcode): Promise<SettingsBarcode> => {
    const response = await client.put<SettingsBarcode>('/settings/barcode', payload)
    return response.data
  },

  getExport: async (): Promise<SettingsExport> => {
    const response = await client.get<SettingsExport>('/settings/export')
    return response.data
  },

  updateExport: async (payload: SettingsExport): Promise<SettingsExport> => {
    const response = await client.put<SettingsExport>('/settings/export', payload)
    return response.data
  },

  listSuppliers: async (params: {
    page: number
    perPage: number
    q?: string
    includeInactive?: boolean
  }): Promise<SettingsSuppliersResponse> => {
    const response = await client.get<SettingsSuppliersResponse>('/settings/suppliers', {
      params: {
        page: params.page,
        per_page: params.perPage,
        q: params.q?.trim() || undefined,
        include_inactive: params.includeInactive ?? false,
      },
    })
    return response.data
  },

  createSupplier: async (
    payload: CreateSettingsSupplierPayload
  ): Promise<SettingsSupplier> => {
    const response = await client.post<SettingsSupplier>('/settings/suppliers', payload)
    return response.data
  },

  updateSupplier: async (
    supplierId: number,
    payload: UpdateSettingsSupplierPayload
  ): Promise<SettingsSupplier> => {
    const response = await client.put<SettingsSupplier>(
      `/settings/suppliers/${supplierId}`,
      payload
    )
    return response.data
  },

  deactivateSupplier: async (supplierId: number): Promise<SettingsSupplier> => {
    const response = await client.patch<SettingsSupplier>(
      `/settings/suppliers/${supplierId}/deactivate`
    )
    return response.data
  },

  getUsers: async (): Promise<SettingsUser[]> => {
    const response = await client.get<SettingsUser[]>('/settings/users')
    return response.data
  },

  createUser: async (payload: CreateSettingsUserPayload): Promise<SettingsUser> => {
    const response = await client.post<SettingsUser>('/settings/users', payload)
    return response.data
  },

  updateUser: async (
    userId: number,
    payload: UpdateSettingsUserPayload
  ): Promise<SettingsUser> => {
    const response = await client.put<SettingsUser>(`/settings/users/${userId}`, payload)
    return response.data
  },

  deactivateUser: async (userId: number): Promise<SettingsUser> => {
    const response = await client.patch<SettingsUser>(`/settings/users/${userId}/deactivate`)
    return response.data
  },
}
