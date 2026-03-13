import type {
  OrderArticleLookupItem,
  OrderDetailLine,
  OrderLineStatus,
  OrderStatus,
} from '../../api/orders'

export const INTEGER_UOMS = new Set(['kom', 'pak', 'pár'])

export type LookupState = 'idle' | 'loading' | 'found' | 'not-found'

export interface OrderLineDraft {
  key: string
  articleId: number | null
  selectedArticle: OrderArticleLookupItem | null
  articleOptions: OrderArticleLookupItem[]
  articleLookupState: LookupState
  supplierArticleCode: string
  orderedQty: number | string
  uom: string
  unitPrice: number | string
  deliveryDate: string
  note: string
}

export interface OrderLineFormErrors {
  article?: string
  supplierArticleCode?: string
  orderedQty?: string
  unitPrice?: string
  note?: string
  line?: string
}

export function createLineKey(): string {
  return crypto.randomUUID()
}

export function createEmptyOrderLineDraft(): OrderLineDraft {
  return {
    key: createLineKey(),
    articleId: null,
    selectedArticle: null,
    articleOptions: [],
    articleLookupState: 'idle',
    supplierArticleCode: '',
    orderedQty: '',
    uom: '',
    unitPrice: '',
    deliveryDate: '',
    note: '',
  }
}

export function createExistingOrderLineDraft(line: OrderDetailLine): OrderLineDraft {
  return {
    key: createLineKey(),
    articleId: line.article_id,
    selectedArticle: {
      article_id: line.article_id,
      article_no: line.article_no ?? '',
      description: line.description ?? '',
      uom: line.uom,
      supplier_article_code: line.supplier_article_code,
      last_price: line.unit_price,
    },
    articleOptions: [],
    articleLookupState: 'found',
    supplierArticleCode: line.supplier_article_code ?? '',
    orderedQty: line.ordered_qty,
    uom: line.uom,
    unitPrice: line.unit_price ?? '',
    deliveryDate: line.delivery_date ?? '',
    note: line.note ?? '',
  }
}

export function buildArticleOptionLabel(article: OrderArticleLookupItem): string {
  return `${article.article_no} - ${article.description}`
}

export function getArticleSelectData(line: OrderLineDraft): Array<{ value: string; label: string }> {
  const seen = new Set<number>()
  const items = [line.selectedArticle, ...line.articleOptions].filter(
    (article): article is OrderArticleLookupItem => article !== null
  )

  return items.reduce<Array<{ value: string; label: string }>>((acc, article) => {
    if (seen.has(article.article_id)) {
      return acc
    }

    seen.add(article.article_id)
    acc.push({
      value: String(article.article_id),
      label: buildArticleOptionLabel(article),
    })
    return acc
  }, [])
}

export function findArticleOption(
  line: OrderLineDraft,
  articleId: string | null
): OrderArticleLookupItem | null {
  if (!articleId) {
    return null
  }

  const numericArticleId = Number(articleId)
  const items = [line.selectedArticle, ...line.articleOptions].filter(
    (article): article is OrderArticleLookupItem => article !== null
  )

  return items.find((article) => article.article_id === numericArticleId) ?? null
}

export function normalizeOptionalText(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

export function formatDate(value: string | null): string {
  if (!value) {
    return '—'
  }

  try {
    return new Date(value).toLocaleDateString('hr-HR')
  } catch {
    return '—'
  }
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return '—'
  }

  try {
    return new Date(value).toLocaleString('hr-HR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return '—'
  }
}

export function formatMoney(value: number | null): string {
  if (value === null) {
    return '—'
  }

  return new Intl.NumberFormat('hr-HR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatQuantity(quantity: number, uom: string): string {
  if (INTEGER_UOMS.has(uom)) {
    return Math.round(quantity).toString()
  }

  return quantity.toFixed(2)
}

export function getQuantityStep(uom?: string): number {
  return uom && INTEGER_UOMS.has(uom) ? 1 : 0.01
}

export function getQuantityScale(uom?: string): number {
  return uom && INTEGER_UOMS.has(uom) ? 0 : 3
}

export function getOrderStatusLabel(status: OrderStatus): string {
  if (status === 'OPEN') {
    return 'Otvorena'
  }

  if (status === 'CLOSED') {
    return 'Zatvorena'
  }

  return status
}

export function getOrderLineStatusLabel(status: OrderLineStatus): string {
  if (status === 'OPEN') {
    return 'Otvorena'
  }

  if (status === 'CLOSED') {
    return 'Zatvorena'
  }

  if (status === 'REMOVED') {
    return 'Uklonjena'
  }

  return status
}

export function getOrderStatusColor(status: OrderStatus): string {
  if (status === 'OPEN') {
    return 'green'
  }

  if (status === 'CLOSED') {
    return 'gray'
  }

  return 'blue'
}

export function getOrderLineStatusColor(status: OrderLineStatus): string {
  if (status === 'OPEN') {
    return 'green'
  }

  if (status === 'CLOSED') {
    return 'gray'
  }

  if (status === 'REMOVED') {
    return 'red'
  }

  return 'blue'
}
