import client from './client'

/**
 * Minimal Phase 7 order lookup response used by Receiving.
 * This is not a generic orders list/search contract.
 */
export interface ReceivingOrderSummary {
  id: number
  order_number: string
  status: 'OPEN' | 'CLOSED' | string
  supplier_id: number | null
  supplier_name: string | null
  open_line_count: number
  created_at: string | null
}

export interface ReceivingOrderLine {
  id: number
  article_id: number
  article_no: string
  description: string
  has_batch: boolean
  ordered_qty: number
  received_qty: number
  remaining_qty: number
  status: 'OPEN' | 'CLOSED' | string
  is_open: boolean
  uom: string
  unit_price: number | null
  delivery_date: string | null
}

export interface ReceivingOrderDetail {
  id: number
  order_number: string
  status: 'OPEN' | 'CLOSED' | string
  supplier_id: number | null
  supplier_name: string | null
  supplier_confirmation_number: string | null
  note: string | null
  created_at: string | null
  lines: ReceivingOrderLine[]
}

export const ordersApi = {
  /**
   * Exact order-number lookup used by Receiving.
   * GET /api/v1/orders?q={order_number}
   */
  lookupForReceiving: async (orderNumber: string): Promise<ReceivingOrderSummary> => {
    const response = await client.get<ReceivingOrderSummary>('/orders', {
      params: { q: orderNumber },
    })
    return response.data
  },

  /**
   * Receiving-oriented order detail.
   * GET /api/v1/orders/{id}
   */
  getReceivingDetail: async (orderId: number): Promise<ReceivingOrderDetail> => {
    const response = await client.get<ReceivingOrderDetail>(`/orders/${orderId}`)
    return response.data
  },
}
