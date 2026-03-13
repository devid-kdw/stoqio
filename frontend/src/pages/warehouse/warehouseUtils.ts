import type {
  ArticleMutationPayload,
  ArticleUomLookupItem,
  ReorderStatus,
  WarehouseArticleDetail,
} from '../../api/articles'
import type { ApiErrorBody } from '../../utils/http'

const FALLBACK_INTEGER_UOMS = new Set(['kom', 'pak', 'pár'])
const ARTICLE_NO_RE = /^[A-Z0-9-]+$/

export interface WarehouseArticleFormState {
  articleNo: string
  description: string
  categoryId: string | null
  baseUom: string | null
  packSize: number | string
  packUom: string | null
  barcode: string
  manufacturer: string
  manufacturerArtNumber: string
  hasBatch: boolean
  reorderThreshold: number | string
  reorderCoverageDays: number | string
  density: number | string
  isActive: boolean
}

export interface WarehouseArticleFormErrors {
  articleNo?: string
  description?: string
  categoryId?: string
  baseUom?: string
  packSize?: string
  packUom?: string
  barcode?: string
  manufacturer?: string
  manufacturerArtNumber?: string
  reorderThreshold?: string
  reorderCoverageDays?: string
  density?: string
}

export function createArticleFormState(
  article?: WarehouseArticleDetail | null
): WarehouseArticleFormState {
  return {
    articleNo: article?.article_no ?? '',
    description: article?.description ?? '',
    categoryId: article?.category_id ? String(article.category_id) : null,
    baseUom: article?.base_uom ?? null,
    packSize: article?.pack_size ?? '',
    packUom: article?.pack_uom ?? null,
    barcode: article?.barcode ?? '',
    manufacturer: article?.manufacturer ?? '',
    manufacturerArtNumber: article?.manufacturer_art_number ?? '',
    hasBatch: article?.has_batch ?? false,
    reorderThreshold: article?.reorder_threshold ?? '',
    reorderCoverageDays: article?.reorder_coverage_days ?? '',
    density: article?.density ?? 1,
    isActive: article?.is_active ?? true,
  }
}

export function buildUomMap(uoms: ArticleUomLookupItem[]): Record<string, ArticleUomLookupItem> {
  return uoms.reduce<Record<string, ArticleUomLookupItem>>((acc, uom) => {
    acc[uom.code] = uom
    return acc
  }, {})
}

function parseOptionalNumber(value: number | string): number | null {
  if (value === '' || value === null || typeof value === 'undefined') {
    return null
  }

  const parsed = typeof value === 'number' ? value : Number.parseFloat(value)
  return Number.isNaN(parsed) ? null : parsed
}

function parseOptionalInteger(value: number | string): number | null {
  if (value === '' || value === null || typeof value === 'undefined') {
    return null
  }

  const parsed = typeof value === 'number' ? value : Number.parseInt(String(value), 10)
  return Number.isNaN(parsed) ? null : parsed
}

export function normalizeOptionalText(value: string): string | null {
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function usesDecimalDisplay(
  uom: string | null | undefined,
  uomMap?: Record<string, ArticleUomLookupItem>
): boolean {
  if (!uom) {
    return true
  }

  const lookupValue = uomMap?.[uom]
  if (lookupValue) {
    return lookupValue.decimal_display
  }

  return !FALLBACK_INTEGER_UOMS.has(uom)
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

export function formatDecimal(value: number | null): string {
  if (value === null) {
    return '—'
  }

  return new Intl.NumberFormat('hr-HR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatQuantity(
  quantity: number,
  uom: string | null | undefined,
  uomMap?: Record<string, ArticleUomLookupItem>
): string {
  const formatted = new Intl.NumberFormat('hr-HR', {
    minimumFractionDigits: usesDecimalDisplay(uom, uomMap) ? 2 : 0,
    maximumFractionDigits: usesDecimalDisplay(uom, uomMap) ? 2 : 0,
  }).format(quantity)

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

export function getQuantityStep(
  uom: string | null | undefined,
  uomMap?: Record<string, ArticleUomLookupItem>
): number {
  return usesDecimalDisplay(uom, uomMap) ? 0.01 : 1
}

export function getQuantityScale(
  uom: string | null | undefined,
  uomMap?: Record<string, ArticleUomLookupItem>
): number {
  return usesDecimalDisplay(uom, uomMap) ? 3 : 0
}

export function getReorderStatusColor(status: ReorderStatus): string {
  if (status === 'RED') {
    return '#d9480f'
  }

  if (status === 'YELLOW') {
    return '#f08c00'
  }

  return '#adb5bd'
}

export function getReorderStatusLabel(status: ReorderStatus): string {
  if (status === 'RED') {
    return 'Crvena zona'
  }

  if (status === 'YELLOW') {
    return 'Žuta zona'
  }

  return 'Normalno'
}

export function getReorderStatusTint(status: ReorderStatus): string {
  if (status === 'RED') {
    return 'rgba(217, 72, 15, 0.06)'
  }

  if (status === 'YELLOW') {
    return 'rgba(240, 140, 0, 0.05)'
  }

  return 'transparent'
}

export function getTransactionTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    STOCK_RECEIPT: 'Primka na zalihu',
    OUTBOUND: 'Izlaz',
    SURPLUS_CONSUMED: 'Potrošen višak',
    STOCK_CONSUMED: 'Potrošena zaliha',
    INVENTORY_ADJUSTMENT: 'Inventurna korekcija',
    WRITEOFF: 'Otpis',
    PERSONAL_ISSUE: 'Osobno izdavanje',
  }

  return labels[type] ?? type
}

const ARTICLE_API_FIELD_LABELS: Record<string, string> = {
  article_no: 'Broj artikla',
  description: 'Opis',
  category_id: 'Kategorija',
  base_uom: 'Osnovna mjerna jedinica',
  pack_size: 'Veličina pakiranja',
  pack_uom: 'Jedinica pakiranja',
  reorder_threshold: 'Prag naručivanja',
  reorder_coverage_days: 'Pokrivenost u danima',
  density: 'Gustoća',
  has_batch: 'Praćenje po šaržama',
  is_active: 'Aktivnost artikla',
  page: 'Stranica',
  per_page: 'Broj stavki po stranici',
  include_inactive: 'Prikaži deaktivirane',
  q: 'Upit',
}

function getArticleApiFieldLabel(fieldName: string): string {
  return ARTICLE_API_FIELD_LABELS[fieldName] ?? fieldName
}

function detectArticleApiFieldName(message: string): string | null {
  const fieldMatch = message.match(/^([a-z_]+)/)
  return fieldMatch?.[1] ?? null
}

function translateUnsupportedFields(rawValue: string): string {
  return rawValue
    .split(',')
    .map((field) => getArticleApiFieldLabel(field.trim()))
    .join(', ')
}

export function translateArticleApiMessage(
  apiError: ApiErrorBody | null,
  fallbackMessage: string
): string {
  const message = apiError?.message?.trim()
  if (!message) {
    return fallbackMessage
  }

  if (message === 'Article number already exists.') {
    return 'Broj artikla već postoji.'
  }

  if (message === 'Article not found.') {
    return 'Artikl nije pronađen.'
  }

  if (message === "Query parameter 'q' is required.") {
    return "Parametar 'q' je obavezan."
  }

  if (message === 'Barcode generation is not implemented in Phase 9.') {
    return 'Generiranje barkoda nije implementirano u fazi 9.'
  }

  const unsupportedFieldsMatch = message.match(/^Unsupported fields: (.+)\.$/)
  if (unsupportedFieldsMatch) {
    return `Nepodržana polja: ${translateUnsupportedFields(unsupportedFieldsMatch[1])}.`
  }

  const forbiddenMatch = message.match(/^Role '(.+)' is not permitted for this endpoint\.$/)
  if (forbiddenMatch) {
    return `Uloga '${forbiddenMatch[1]}' nema pristup ovoj akciji.`
  }

  const fieldName = detectArticleApiFieldName(message)
  const fieldLabel = fieldName ? getArticleApiFieldLabel(fieldName) : null

  const requiredMatch = message.match(/^([a-z_]+) is required\.$/)
  if (requiredMatch && fieldLabel) {
    const requiredMessages: Record<string, string> = {
      article_no: 'Broj artikla je obavezan.',
      description: 'Opis artikla je obavezan.',
      category_id: 'Kategorija je obavezna.',
      base_uom: 'Osnovna mjerna jedinica je obavezna.',
    }

    return requiredMessages[requiredMatch[1]] ?? `${fieldLabel} je obavezan.`
  }

  const maxLengthMatch = message.match(/^([a-z_]+) must be (\d+) characters or fewer\.$/)
  if (maxLengthMatch && fieldLabel) {
    return `${fieldLabel} može imati najviše ${maxLengthMatch[2]} znakova.`
  }

  const validIntegerMatch = message.match(/^([a-z_]+) must be a valid integer\.$/)
  if (validIntegerMatch && fieldLabel) {
    return `${fieldLabel} mora biti ispravan cijeli broj.`
  }

  const validNumberMatch = message.match(/^([a-z_]+) must be a valid number\.$/)
  if (validNumberMatch && fieldLabel) {
    return `${fieldLabel} mora biti ispravan broj.`
  }

  const greaterThanZeroMatch = message.match(/^([a-z_]+) must be greater than zero\.$/)
  if (greaterThanZeroMatch && fieldLabel) {
    return `${fieldLabel} mora biti veći od 0.`
  }

  const greaterThanOrEqualZeroMatch = message.match(
    /^([a-z_]+) must be greater than or equal to zero\.$/
  )
  if (greaterThanOrEqualZeroMatch && fieldLabel) {
    return `${fieldLabel} mora biti veći ili jednak 0.`
  }

  const booleanMatch = message.match(/^([a-z_]+) must be a boolean\.$/)
  if (booleanMatch && fieldLabel) {
    return `${fieldLabel} mora biti logička vrijednost.`
  }

  const trueFalseMatch = message.match(/^([a-z_]+) must be 'true' or 'false'\.$/)
  if (trueFalseMatch && fieldLabel) {
    return `${fieldLabel} mora biti 'true' ili 'false'.`
  }

  const articleNoCharsMatch = message.match(
    /^([a-z_]+) may contain only letters, digits, and hyphens\.$/
  )
  if (articleNoCharsMatch && fieldLabel === 'Broj artikla') {
    return 'Broj artikla smije sadržavati samo slova, brojeve i crticu.'
  }

  const existingCategoryMatch = message.match(/^([a-z_]+) must reference an existing category\.$/)
  if (existingCategoryMatch && fieldLabel) {
    return `${fieldLabel} mora upućivati na postojeću kategoriju.`
  }

  const activeCategoryMatch = message.match(/^([a-z_]+) must reference an active category\.$/)
  if (activeCategoryMatch && fieldLabel) {
    return `${fieldLabel} mora upućivati na aktivnu kategoriju.`
  }

  const existingUomMatch = message.match(/^([a-z_]+) must reference an existing UOM code\.$/)
  if (existingUomMatch && fieldLabel) {
    return `${fieldLabel} mora upućivati na postojeću mjernu jedinicu.`
  }

  const activeUomMatch = message.match(/^([a-z_]+) must reference an active UOM code\.$/)
  if (activeUomMatch && fieldLabel) {
    return `${fieldLabel} mora upućivati na aktivnu mjernu jedinicu.`
  }

  return fallbackMessage || message
}

export function validateArticleForm(
  form: WarehouseArticleFormState
): WarehouseArticleFormErrors {
  const errors: WarehouseArticleFormErrors = {}
  const normalizedArticleNo = form.articleNo.trim().toUpperCase()
  const description = form.description.trim()
  const packSize = parseOptionalNumber(form.packSize)
  const reorderThreshold = parseOptionalNumber(form.reorderThreshold)
  const reorderCoverageDays = parseOptionalInteger(form.reorderCoverageDays)
  const density = parseOptionalNumber(form.density)

  if (!normalizedArticleNo) {
    errors.articleNo = 'Broj artikla je obavezan.'
  } else if (normalizedArticleNo.length > 50) {
    errors.articleNo = 'Broj artikla može imati najviše 50 znakova.'
  } else if (!ARTICLE_NO_RE.test(normalizedArticleNo)) {
    errors.articleNo = 'Broj artikla smije sadržavati samo slova, brojeve i crticu.'
  }

  if (!description) {
    errors.description = 'Opis artikla je obavezan.'
  } else if (description.length > 500) {
    errors.description = 'Opis artikla može imati najviše 500 znakova.'
  }

  if (!form.categoryId) {
    errors.categoryId = 'Kategorija je obavezna.'
  }

  if (!form.baseUom) {
    errors.baseUom = 'Osnovna mjerna jedinica je obavezna.'
  }

  if (form.packSize !== '' && (packSize === null || packSize <= 0)) {
    errors.packSize = 'Veličina pakiranja mora biti veća od 0.'
  }

  if (form.reorderThreshold !== '' && (reorderThreshold === null || reorderThreshold <= 0)) {
    errors.reorderThreshold = 'Prag naručivanja mora biti veći od 0.'
  }

  if (
    form.reorderCoverageDays !== '' &&
    (reorderCoverageDays === null || reorderCoverageDays <= 0 || !Number.isInteger(reorderCoverageDays))
  ) {
    errors.reorderCoverageDays = 'Pokrivenost mora biti cijeli broj veći od 0.'
  }

  if (density === null || density <= 0) {
    errors.density = 'Gustoća mora biti veća od 0.'
  }

  return errors
}

export function buildArticlePayload(form: WarehouseArticleFormState): ArticleMutationPayload {
  return {
    article_no: form.articleNo.trim().toUpperCase(),
    description: form.description.trim(),
    category_id: Number(form.categoryId),
    base_uom: String(form.baseUom),
    pack_size: parseOptionalNumber(form.packSize),
    pack_uom: form.packUom ?? null,
    barcode: normalizeOptionalText(form.barcode),
    manufacturer: normalizeOptionalText(form.manufacturer),
    manufacturer_art_number: normalizeOptionalText(form.manufacturerArtNumber),
    has_batch: form.hasBatch,
    reorder_threshold: parseOptionalNumber(form.reorderThreshold),
    reorder_coverage_days: parseOptionalInteger(form.reorderCoverageDays),
    density: parseOptionalNumber(form.density) ?? 1,
    is_active: form.isActive,
  }
}

export function mapArticleApiErrorToFormErrors(
  apiError: ApiErrorBody | null
): WarehouseArticleFormErrors {
  const message = apiError?.message ?? ''
  const normalizedMessage = message.toLowerCase()
  const translatedMessage = translateArticleApiMessage(apiError, '')

  if (
    apiError?.error === 'ARTICLE_ALREADY_EXISTS' ||
    normalizedMessage.includes('article number already exists') ||
    translatedMessage === 'Broj artikla već postoji.'
  ) {
    return { articleNo: translatedMessage || 'Broj artikla već postoji.' }
  }

  if (normalizedMessage.startsWith('article_no')) {
    return { articleNo: translatedMessage || message }
  }

  if (normalizedMessage.startsWith('description')) {
    return { description: translatedMessage || message }
  }

  if (normalizedMessage.startsWith('category_id')) {
    return { categoryId: translatedMessage || message }
  }

  if (normalizedMessage.startsWith('base_uom')) {
    return { baseUom: translatedMessage || message }
  }

  if (normalizedMessage.startsWith('pack_size')) {
    return { packSize: translatedMessage || message }
  }

  if (normalizedMessage.startsWith('pack_uom')) {
    return { packUom: translatedMessage || message }
  }

  if (normalizedMessage.startsWith('reorder_threshold')) {
    return { reorderThreshold: translatedMessage || message }
  }

  if (normalizedMessage.startsWith('reorder_coverage_days')) {
    return { reorderCoverageDays: translatedMessage || message }
  }

  if (normalizedMessage.startsWith('density')) {
    return { density: translatedMessage || message }
  }

  return {}
}
