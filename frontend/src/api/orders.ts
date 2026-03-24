import client from './client'

export type OrderStatus = 'OPEN' | 'CLOSED' | string
export type OrderLineStatus = 'OPEN' | 'CLOSED' | 'REMOVED' | string

export interface OrderSupplierLookupItem {
  id: number
  internal_code: string
  name: string
}

export interface OrderSupplierLookupResponse {
  items: OrderSupplierLookupItem[]
}

export interface OrderArticleLookupItem {
  article_id: number
  article_no: string
  description: string
  uom: string | null
  supplier_article_code: string | null
  last_price: number | null
}

export interface OrderArticleLookupResponse {
  items: OrderArticleLookupItem[]
}

export interface OrdersListItem {
  id: number
  order_number: string
  supplier_id: number | null
  supplier_name: string | null
  status: OrderStatus
  line_count: number
  total_value: number
  created_at: string | null
}

export interface OrdersListResponse {
  items: OrdersListItem[]
  total: number
  page: number
  per_page: number
}

export interface OrderDetailLine {
  id: number
  position: number
  article_id: number
  article_no: string | null
  description: string | null
  supplier_article_code: string | null
  ordered_qty: number
  received_qty: number
  uom: string
  unit_price: number | null
  total_price: number
  delivery_date: string | null
  status: OrderLineStatus
  note: string | null
}

export interface OrderDetail {
  id: number
  order_number: string
  supplier_id: number | null
  supplier_name: string | null
  supplier_address: string | null
  supplier_confirmation_number: string | null
  status: OrderStatus
  note: string | null
  total_value: number
  created_at: string | null
  updated_at: string | null
  lines: OrderDetailLine[]
}

export interface CreateOrderLinePayload {
  article_id: number
  supplier_article_code?: string | null
  ordered_qty: number
  uom: string
  unit_price: number
  delivery_date?: string | null
  note?: string | null
}

export interface CreateOrderPayload {
  order_number?: string | null
  supplier_id: number
  supplier_confirmation_number?: string | null
  note?: string | null
  lines: CreateOrderLinePayload[]
}

export interface CreateOrderResponse {
  id: number
  order_number: string
  supplier_id: number | null
  supplier_name: string | null
  status: OrderStatus
  total_value: number
  created_at: string | null
}

export interface UpdateOrderHeaderPayload {
  supplier_confirmation_number?: string | null
  note?: string | null
}

export type AddOrderLinePayload = CreateOrderLinePayload

export interface UpdateOrderLinePayload {
  supplier_article_code?: string | null
  ordered_qty?: number
  unit_price?: number
  delivery_date?: string | null
  note?: string | null
}

export interface ReceivingOrderSummary {
  id: number
  order_number: string
  status: OrderStatus
  supplier_id: number | null
  supplier_name: string | null
  open_line_count: number
  created_at: string | null
}

export interface ReceivingOrderLine {
  id: number
  article_id: number
  article_no: string | null
  description: string | null
  has_batch: boolean
  ordered_qty: number
  received_qty: number
  remaining_qty: number
  status: OrderStatus
  is_open: boolean
  uom: string
  unit_price: number | null
  delivery_date: string | null
}

export interface ReceivingOrderDetail {
  id: number
  order_number: string
  status: OrderStatus
  supplier_id: number | null
  supplier_name: string | null
  supplier_confirmation_number: string | null
  note: string | null
  created_at: string | null
  lines: ReceivingOrderLine[]
}

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

export const ordersApi = {
  list: async (page = 1, perPage = 50): Promise<OrdersListResponse> => {
    const response = await client.get<OrdersListResponse>('/orders', {
      params: { page, per_page: perPage },
    })
    return response.data
  },

  getDetail: async (orderId: number): Promise<OrderDetail> => {
    const response = await client.get<OrderDetail>(`/orders/${orderId}`)
    return response.data
  },

  create: async (payload: CreateOrderPayload): Promise<CreateOrderResponse> => {
    const response = await client.post<CreateOrderResponse>('/orders', payload)
    return response.data
  },

  updateHeader: async (orderId: number, payload: UpdateOrderHeaderPayload): Promise<OrderDetail> => {
    const response = await client.patch<OrderDetail>(`/orders/${orderId}`, payload)
    return response.data
  },

  addLine: async (orderId: number, payload: AddOrderLinePayload): Promise<OrderDetail> => {
    const response = await client.post<OrderDetail>(`/orders/${orderId}/lines`, payload)
    return response.data
  },

  updateLine: async (
    orderId: number,
    lineId: number,
    payload: UpdateOrderLinePayload
  ): Promise<OrderDetail> => {
    const response = await client.patch<OrderDetail>(`/orders/${orderId}/lines/${lineId}`, payload)
    return response.data
  },

  removeLine: async (orderId: number, lineId: number): Promise<OrderDetail> => {
    const response = await client.delete<OrderDetail>(`/orders/${orderId}/lines/${lineId}`)
    return response.data
  },

  downloadPdf: async (orderId: number, fallbackOrderNumber?: string): Promise<void> => {
    const response = await client.get<Blob>(`/orders/${orderId}/pdf`, {
      responseType: 'blob',
    })

    const fallbackName = `${fallbackOrderNumber ?? `order-${orderId}`}.pdf`
    const filename = getPdfFilename(response.headers['content-disposition'], fallbackName)

    const objectUrl = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(objectUrl)
  },

  preloadSuppliers: async (): Promise<OrderSupplierLookupResponse> => {
    const response = await client.get<{ items: OrderSupplierLookupItem[]; total: number; page: number; per_page: number }>('/suppliers', {
      params: { per_page: 200 },
    })
    return { items: response.data.items }
  },

  lookupSuppliers: async (query: string): Promise<OrderSupplierLookupResponse> => {
    const response = await client.get<OrderSupplierLookupResponse>('/orders/lookups/suppliers', {
      params: { q: query },
    })
    return response.data
  },

  lookupArticles: async (
    query: string,
    supplierId?: number | null
  ): Promise<OrderArticleLookupResponse> => {
    const params: Record<string, string | number> = { q: query }
    if (supplierId) {
      params.supplier_id = supplierId
    }

    const response = await client.get<OrderArticleLookupResponse>('/orders/lookups/articles', {
      params,
    })
    return response.data
  },

  listOpenOrdersPreload: async (): Promise<OrdersListResponse> => {
    const response = await client.get<OrdersListResponse>('/orders', {
      params: { status: 'OPEN', per_page: 200 },
    })
    return response.data
  },

  lookupForReceiving: async (orderNumber: string): Promise<ReceivingOrderSummary> => {
    const response = await client.get<ReceivingOrderSummary>('/orders', {
      params: { q: orderNumber },
    })
    return response.data
  },

  getReceivingDetail: async (orderId: number): Promise<ReceivingOrderDetail> => {
    const response = await client.get<ReceivingOrderDetail>(`/orders/${orderId}`, {
      params: { view: 'receiving' },
    })
    return response.data
  },
}
