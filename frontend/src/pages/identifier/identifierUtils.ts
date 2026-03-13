import type { ApiErrorBody } from '../../utils/http'

const IDENTIFIER_FIELD_LABELS: Record<string, string> = {
  q: 'Upit',
  search_term: 'Pojam pretrage',
  resolution_note: 'Napomena',
  status: 'Status',
}

export function normalizeOptionalText(value: string): string | null {
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

export function formatIdentifierQuantity(
  quantity: number,
  uom: string | null | undefined,
  decimalDisplay: boolean | null | undefined
): string {
  const digits = decimalDisplay === false ? 0 : 2
  const formatted = new Intl.NumberFormat('hr-HR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(quantity)

  return uom ? `${formatted} ${uom}` : formatted
}

export function formatIdentifierDateTime(value: string | null): string {
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

export function getIdentifierReportStatusLabel(status: string): string {
  if (status === 'OPEN') {
    return 'Otvoreno'
  }

  if (status === 'RESOLVED') {
    return 'Riješeno'
  }

  return status
}

export function getIdentifierReportStatusColor(status: string): string {
  if (status === 'OPEN') {
    return 'orange'
  }

  if (status === 'RESOLVED') {
    return 'green'
  }

  return 'gray'
}

export function validateMissingArticleReportTerm(value: string): string | null {
  const normalized = normalizeOptionalText(value)
  if (!normalized) {
    return 'Pojam pretrage je obavezan.'
  }

  if (normalized.length > 255) {
    return 'Pojam pretrage može imati najviše 255 znakova.'
  }

  return null
}

function getFieldLabel(fieldName: string): string {
  return IDENTIFIER_FIELD_LABELS[fieldName] ?? fieldName
}

function translateUnsupportedFields(rawValue: string): string {
  return rawValue
    .split(',')
    .map((field) => getFieldLabel(field.trim()))
    .join(', ')
}

export function translateIdentifierApiMessage(
  apiError: ApiErrorBody | null,
  fallbackMessage: string
): string {
  const message = apiError?.message?.trim()
  if (!message) {
    return fallbackMessage
  }

  if (message === 'Missing article report not found.') {
    return 'Prijava nedostajućeg artikla nije pronađena.'
  }

  if (message === "Query parameter 'q' is required.") {
    return "Parametar 'q' je obavezan."
  }

  const forbiddenMatch = message.match(/^Role '(.+)' is not permitted for this endpoint\.$/)
  if (forbiddenMatch) {
    return `Uloga '${forbiddenMatch[1]}' nema pristup ovoj akciji.`
  }

  const unsupportedFieldsMatch = message.match(/^Unsupported fields: (.+)\.$/)
  if (unsupportedFieldsMatch) {
    return `Nepodržana polja: ${translateUnsupportedFields(unsupportedFieldsMatch[1])}.`
  }

  const requiredMatch = message.match(/^([a-z_]+) is required\.$/)
  if (requiredMatch) {
    const fieldName = requiredMatch[1]
    const fieldLabel = getFieldLabel(fieldName)
    return `${fieldLabel} je obavezan.`
  }

  const maxLengthMatch = message.match(/^([a-z_]+) must be (\d+) characters or fewer\.$/)
  if (maxLengthMatch) {
    const [, fieldName, length] = maxLengthMatch
    const fieldLabel = getFieldLabel(fieldName)
    return `${fieldLabel} može imati najviše ${length} znakova.`
  }

  return message
}
