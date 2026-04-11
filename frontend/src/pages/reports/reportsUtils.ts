import type { ArticleUomLookupItem } from '../../api/articles'
import type { ReportReorderStatus, ReportTransactionType } from '../../api/reports'
import { INTEGER_UOMS } from '../../utils/uom'
import { getActiveLocale } from '../../utils/locale'

export function getTodayIsoDate(): string {
  // Uses UTC date intentionally to match server-side UTC date calculations.
  // Do not change to local date without updating backend report date handling.
  return new Date().toISOString().slice(0, 10)
}

export function getMonthStartIsoDate(): string {
  // Uses UTC date intentionally to match server-side UTC date calculations.
  // Do not change to local date without updating backend report date handling.
  const value = new Date()
  value.setUTCDate(1)
  return value.toISOString().slice(0, 10)
}

export function buildUomMap(uoms: ArticleUomLookupItem[]): Record<string, ArticleUomLookupItem> {
  return uoms.reduce<Record<string, ArticleUomLookupItem>>((accumulator, uom) => {
    accumulator[uom.code] = uom
    return accumulator
  }, {})
}

function usesDecimalDisplay(
  uom: string | null | undefined,
  uomMap?: Record<string, ArticleUomLookupItem>
): boolean {
  if (!uom) {
    return true
  }

  const entry = uomMap?.[uom]
  if (entry) {
    return entry.decimal_display
  }

  return !INTEGER_UOMS.includes(uom)
}

function formatNumber(value: number, decimals: number): string {
  return new Intl.NumberFormat(getActiveLocale(), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatDate(value: string | null): string {
  if (!value) {
    return '—'
  }

  try {
    return new Date(value).toLocaleDateString(getActiveLocale(), {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return '—'
  }
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return '—'
  }

  try {
    return new Date(value).toLocaleString(getActiveLocale(), {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return '—'
  }
}

export function formatQuantity(
  quantity: number,
  uom: string | null | undefined,
  uomMap?: Record<string, ArticleUomLookupItem>
): string {
  const decimals = usesDecimalDisplay(uom, uomMap) ? 2 : 0
  const formatted = formatNumber(quantity, decimals)
  return uom ? `${formatted} ${uom}` : formatted
}

export function formatOptionalQuantity(
  quantity: number | null,
  uom: string | null | undefined,
  uomMap?: Record<string, ArticleUomLookupItem>
): string {
  if (quantity === null || quantity === 0) {
    return '—'
  }

  return formatQuantity(quantity, uom, uomMap)
}

export function formatSignedQuantity(
  quantity: number,
  uom: string | null | undefined,
  uomMap?: Record<string, ArticleUomLookupItem>
): string {
  const decimals = usesDecimalDisplay(uom, uomMap) ? 2 : 0
  const prefix = quantity > 0 ? '+' : ''
  const formatted = formatNumber(quantity, decimals)
  return uom ? `${prefix}${formatted} ${uom}` : `${prefix}${formatted}`
}

export function formatDecimal(value: number | null, decimals = 2): string {
  if (value === null) {
    return '—'
  }

  return formatNumber(value, decimals)
}

export function formatCurrency(value: number | null): string {
  if (value === null) {
    return '—'
  }

  return `${formatNumber(value, 2)} €`
}

export function formatCoverageMonths(value: number | null | undefined): string {
  if (value === undefined) {
    return '—'
  }

  if (value === null) {
    return '∞'
  }

  return formatNumber(value, 1)
}

export function getReorderStatusLabel(status: ReportReorderStatus): string {
  if (status === 'RED') {
    return 'Crvena zona'
  }

  if (status === 'YELLOW') {
    return 'Žuta zona'
  }

  return 'Normalno'
}

export function getReorderStatusColor(status: ReportReorderStatus): string {
  if (status === 'RED') {
    return '#d9480f'
  }

  if (status === 'YELLOW') {
    return '#f08c00'
  }

  return '#2f9e44'
}

export function getReorderStatusBadgeColor(status: ReportReorderStatus): string {
  if (status === 'RED') {
    return 'red'
  }

  if (status === 'YELLOW') {
    return 'yellow'
  }

  return 'green'
}

export function getTransactionTypeLabel(type: ReportTransactionType): string {
  const labels: Record<string, string> = {
    STOCK_RECEIPT: 'Primka na zalihu',
    OUTBOUND: 'Izlaz',
    SURPLUS_CONSUMED: 'Potrošen višak',
    STOCK_CONSUMED: 'Potrošena zaliha',
    INVENTORY_ADJUSTMENT: 'Inventurna korekcija',
    PERSONAL_ISSUE: 'Osobno izdavanje',
  }

  return labels[type] ?? type
}
