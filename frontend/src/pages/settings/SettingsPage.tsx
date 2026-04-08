import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react'
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Divider,
  Group,
  Loader,
  Modal,
  Pagination,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'

import {
  articlesApi,
  type ArticleCategoryLookupItem,
  type ArticleUomLookupItem,
} from '../../api/articles'
import {
  ordersApi,
  type OrderArticleLookupItem,
} from '../../api/orders'
import {
  settingsApi,
  type CreateSettingsSupplierPayload,
  type CreateSettingsUomPayload,
  type CreateSettingsUserPayload,
  type SettingsBarcode,
  type SettingsCategory,
  type SettingsExport,
  type SettingsGeneral,
  type SettingsQuota,
  type SettingsQuotaEnforcement,
  type SettingsQuotaScope,
  type SettingsRoleDisplayName,
  type SettingsSupplier,
  type SettingsUom,
  type SettingsUser,
  type SystemRole,
  type UpdateSettingsSupplierPayload,
  type UpdateSettingsUserPayload,
  type SettingsPrinterModel,
} from '../../api/settings'
import FullPageState from '../../components/shared/FullPageState'
import { getActiveLocale } from '../../utils/locale'
import { useAuthStore } from '../../store/authStore'
import {
  DEFAULT_ROLE_DISPLAY_NAMES,
  useSettingsStore,
} from '../../store/settingsStore'
import {
  getApiErrorBody,
  isNetworkOrServerError,
  runWithRetry,
} from '../../utils/http'
import { getTimezoneOptions } from '../../utils/setup'
import {
  showErrorToast,
  showSuccessToast,
  showWarningToast,
} from '../../utils/toasts'

const SETTINGS_CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'
const SUPPLIERS_PER_PAGE = 10

const ROLE_ORDER: SystemRole[] = [
  'ADMIN',
  'MANAGER',
  'WAREHOUSE_STAFF',
  'VIEWER',
  'OPERATOR',
]

const LANGUAGE_OPTIONS = [
  { value: 'hr', label: 'Hrvatski' },
  { value: 'en', label: 'English' },
  { value: 'de', label: 'Deutsch' },
  { value: 'hu', label: 'Magyar' },
]

const QUOTA_SCOPE_OPTIONS: Array<{ value: SettingsQuotaScope; label: string }> = [
  {
    value: 'GLOBAL_ARTICLE_OVERRIDE',
    label: 'Globalni override po artiklu',
  },
  {
    value: 'JOB_TITLE_CATEGORY_DEFAULT',
    label: 'Default po radnom mjestu i kategoriji',
  },
]

const ENFORCEMENT_OPTIONS: Array<{
  value: SettingsQuotaEnforcement
  label: string
}> = [
  { value: 'WARN', label: 'Upozorenje' },
  { value: 'BLOCK', label: 'Blokiraj' },
]

const BARCODE_OPTIONS = [
  { value: 'Code128', label: 'Code128' },
  { value: 'EAN-13', label: 'EAN-13' },
]

const LABEL_PRINTER_MODEL_OPTIONS: Array<{ value: SettingsPrinterModel; label: string }> = [
  { value: 'zebra_zpl', label: 'Zebra (ZPL)' },
]

const EXPORT_OPTIONS = [
  { value: 'generic', label: 'Generic' },
  { value: 'sap', label: 'SAP-compatible' },
]

const MONTH_OPTIONS = [
  { value: '1', label: '1 - siječanj' },
  { value: '2', label: '2 - veljača' },
  { value: '3', label: '3 - ožujak' },
  { value: '4', label: '4 - travanj' },
  { value: '5', label: '5 - svibanj' },
  { value: '6', label: '6 - lipanj' },
  { value: '7', label: '7 - srpanj' },
  { value: '8', label: '8 - kolovoz' },
  { value: '9', label: '9 - rujan' },
  { value: '10', label: '10 - listopad' },
  { value: '11', label: '11 - studeni' },
  { value: '12', label: '12 - prosinac' },
]

interface UomFormState {
  code: string
  label_hr: string
  label_en: string
  decimal_display: boolean
}

interface UomFormErrors {
  code?: string
  label_hr?: string
}

interface QuotaFormState {
  scope: SettingsQuotaScope
  job_title: string
  category_id: string | null
  article_id: string | null
  selectedArticle: OrderArticleLookupItem | null
  quantity: string
  uom: string | null
  enforcement: SettingsQuotaEnforcement
  reset_month: string
}

interface QuotaFormErrors {
  job_title?: string
  category_id?: string
  article_id?: string
  quantity?: string
  uom?: string
  reset_month?: string
}

interface SupplierFormState {
  internal_code: string
  name: string
  contact_person: string
  phone: string
  email: string
  address: string
  iban: string
  note: string
}

interface SupplierFormErrors {
  internal_code?: string
  name?: string
  note?: string
}

interface UserFormState {
  username: string
  password: string
  role: SystemRole | null
  is_active: boolean
}

interface UserFormErrors {
  username?: string
  password?: string
  role?: string
}

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <Paper withBorder radius="md" p="lg">
      <Stack gap="md">
        <div>
          <Title order={3}>{title}</Title>
          {description ? (
            <Text size="sm" c="dimmed" mt={4}>
              {description}
            </Text>
          ) : null}
        </div>
        {children}
      </Stack>
    </Paper>
  )
}

function createEmptyUomForm(): UomFormState {
  return {
    code: '',
    label_hr: '',
    label_en: '',
    decimal_display: false,
  }
}

function createEmptyQuotaForm(): QuotaFormState {
  return {
    scope: 'GLOBAL_ARTICLE_OVERRIDE',
    job_title: '',
    category_id: null,
    article_id: null,
    selectedArticle: null,
    quantity: '',
    uom: null,
    enforcement: 'WARN',
    reset_month: '1',
  }
}

function createEmptySupplierForm(): SupplierFormState {
  return {
    internal_code: '',
    name: '',
    contact_person: '',
    phone: '',
    email: '',
    address: '',
    iban: '',
    note: '',
  }
}

function createEmptyUserForm(): UserFormState {
  return {
    username: '',
    password: '',
    role: 'OPERATOR',
    is_active: true,
  }
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim()
  return normalized ? normalized : null
}

function roleDisplayNameMap(
  roles: SettingsRoleDisplayName[]
): Record<SystemRole, string> {
  const nextMap = { ...DEFAULT_ROLE_DISPLAY_NAMES }
  roles.forEach((role) => {
    nextMap[role.role] = role.display_name
  })
  return nextMap
}

function sortUoms(uoms: SettingsUom[]): SettingsUom[] {
  return [...uoms].sort((left, right) => left.code.localeCompare(right.code))
}

function sortUomLookupOptions(
  uoms: ArticleUomLookupItem[]
): ArticleUomLookupItem[] {
  return [...uoms].sort((left, right) => left.code.localeCompare(right.code))
}

function sortUsers(users: SettingsUser[]): SettingsUser[] {
  return [...users].sort((left, right) =>
    left.username.localeCompare(right.username, undefined, { sensitivity: 'base' })
  )
}

function sortQuotas(quotas: SettingsQuota[]): SettingsQuota[] {
  return [...quotas].sort((left, right) => {
    const leftScope = left.scope === 'GLOBAL_ARTICLE_OVERRIDE' ? 0 : 1
    const rightScope = right.scope === 'GLOBAL_ARTICLE_OVERRIDE' ? 0 : 1

    if (leftScope !== rightScope) {
      return leftScope - rightScope
    }

    const leftJobTitle = (left.job_title ?? '').toLowerCase()
    const rightJobTitle = (right.job_title ?? '').toLowerCase()
    if (leftJobTitle !== rightJobTitle) {
      return leftJobTitle.localeCompare(rightJobTitle)
    }

    const leftArticle = (left.article_no ?? '').toLowerCase()
    const rightArticle = (right.article_no ?? '').toLowerCase()
    if (leftArticle !== rightArticle) {
      return leftArticle.localeCompare(rightArticle)
    }

    const leftCategory = (left.category_key ?? '').toLowerCase()
    const rightCategory = (right.category_key ?? '').toLowerCase()
    if (leftCategory !== rightCategory) {
      return leftCategory.localeCompare(rightCategory)
    }

    return left.id - right.id
  })
}

function replaceItemById<T extends { id: number }>(items: T[], nextItem: T): T[] {
  return items.map((item) => (item.id === nextItem.id ? nextItem : item))
}

function formatDateTime(iso: string | null): string {
  if (!iso) {
    return '—'
  }

  try {
    return new Date(iso).toLocaleString(getActiveLocale(), {
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

function scopeLabel(scope: SettingsQuotaScope): string {
  if (scope === 'GLOBAL_ARTICLE_OVERRIDE') {
    return 'Globalni override po artiklu'
  }
  return 'Default po radnom mjestu i kategoriji'
}

function enforcementLabel(value: SettingsQuotaEnforcement): string {
  if (value === 'BLOCK') {
    return 'Blokiraj'
  }
  if (value === 'WARN') {
    return 'Upozorenje'
  }
  return value
}

function supplierStatusLabel(isActive: boolean): string {
  return isActive ? 'Aktivan' : 'Neaktivan'
}

function quotaTargetLabel(quota: SettingsQuota): string {
  if (quota.scope === 'GLOBAL_ARTICLE_OVERRIDE') {
    if (!quota.article_no && !quota.article_description) {
      return '—'
    }
    return [quota.article_no, quota.article_description].filter(Boolean).join(' — ')
  }

  return quota.category_label_hr ?? quota.category_key ?? '—'
}

function toSupplierPayload(form: SupplierFormState): CreateSettingsSupplierPayload {
  return {
    internal_code: form.internal_code.trim(),
    name: form.name.trim(),
    contact_person: normalizeOptionalText(form.contact_person),
    phone: normalizeOptionalText(form.phone),
    email: normalizeOptionalText(form.email),
    address: normalizeOptionalText(form.address),
    iban: normalizeOptionalText(form.iban),
    note: normalizeOptionalText(form.note),
  }
}

function toSupplierUpdatePayload(form: SupplierFormState): UpdateSettingsSupplierPayload {
  return {
    name: form.name.trim(),
    contact_person: normalizeOptionalText(form.contact_person),
    phone: normalizeOptionalText(form.phone),
    email: normalizeOptionalText(form.email),
    address: normalizeOptionalText(form.address),
    iban: normalizeOptionalText(form.iban),
    note: normalizeOptionalText(form.note),
  }
}

function toUserPayload(form: UserFormState): CreateSettingsUserPayload {
  return {
    username: form.username.trim(),
    password: form.password,
    role: form.role ?? 'OPERATOR',
    is_active: form.is_active,
  }
}

function toUserUpdatePayload(form: UserFormState): UpdateSettingsUserPayload {
  return {
    role: form.role ?? 'OPERATOR',
    is_active: form.is_active,
    password: form.password.trim() ? form.password : undefined,
  }
}

function getUserPasswordMinLength(role: SystemRole): number {
  return role === 'ADMIN' ? 12 : 8
}

function quotaArticleLabel(article: OrderArticleLookupItem): string {
  return `${article.article_no} — ${article.description}`
}

export default function SettingsPage() {
  const currentUser = useAuthStore((state) => state.user)
  const applyGeneralSettings = useSettingsStore((state) => state.applyGeneralSettings)
  const applyRoleDisplayNames = useSettingsStore((state) => state.applyRoleDisplayNames)

  const timezoneOptions = useMemo(
    () => getTimezoneOptions().map((timezone) => ({ value: timezone, label: timezone })),
    []
  )

  const [pageLoading, setPageLoading] = useState(true)
  const [loadErrorMessage, setLoadErrorMessage] = useState<string | null>(null)

  const [generalForm, setGeneralForm] = useState<SettingsGeneral>({
    location_name: '',
    timezone: 'Europe/Berlin',
    default_language: 'hr',
  })
  const [generalSaving, setGeneralSaving] = useState(false)

  const [roles, setRoles] = useState<SettingsRoleDisplayName[]>([])
  const [rolesForm, setRolesForm] = useState<Record<SystemRole, string>>({
    ...DEFAULT_ROLE_DISPLAY_NAMES,
  })
  const [rolesSaving, setRolesSaving] = useState(false)

  const [uoms, setUoms] = useState<SettingsUom[]>([])
  const [uomLookupOptions, setUomLookupOptions] = useState<ArticleUomLookupItem[]>([])
  const [showAddUomForm, setShowAddUomForm] = useState(false)
  const [uomForm, setUomForm] = useState<UomFormState>(createEmptyUomForm())
  const [uomErrors, setUomErrors] = useState<UomFormErrors>({})
  const [uomSaving, setUomSaving] = useState(false)

  const [categories, setCategories] = useState<SettingsCategory[]>([])
  const [categoryLookupOptions, setCategoryLookupOptions] = useState<ArticleCategoryLookupItem[]>([])
  const [categorySavingId, setCategorySavingId] = useState<number | null>(null)

  const [quotas, setQuotas] = useState<SettingsQuota[]>([])
  const [quotaModalOpen, setQuotaModalOpen] = useState(false)
  const [quotaModalMode, setQuotaModalMode] = useState<'create' | 'edit'>('create')
  const [editingQuotaId, setEditingQuotaId] = useState<number | null>(null)
  const [quotaForm, setQuotaForm] = useState<QuotaFormState>(createEmptyQuotaForm())
  const [quotaErrors, setQuotaErrors] = useState<QuotaFormErrors>({})
  const [quotaSaving, setQuotaSaving] = useState(false)
  const [quotaDeleteTarget, setQuotaDeleteTarget] = useState<SettingsQuota | null>(null)
  const [quotaDeleteLoading, setQuotaDeleteLoading] = useState(false)
  const [quotaArticleSearchValue, setQuotaArticleSearchValue] = useState('')
  const [quotaArticleOptions, setQuotaArticleOptions] = useState<OrderArticleLookupItem[]>([])
  const [quotaArticleSearching, setQuotaArticleSearching] = useState(false)

  const [barcodeForm, setBarcodeForm] = useState<SettingsBarcode>({
    barcode_format: 'Code128',
    barcode_printer: '',
    label_printer_ip: '',
    label_printer_port: 9100,
    label_printer_model: 'zebra_zpl',
  })
  const [barcodeSaving, setBarcodeSaving] = useState(false)
  const [barcodeIpError, setBarcodeIpError] = useState<string | null>(null)

  const [exportForm, setExportForm] = useState<SettingsExport>({
    export_format: 'generic',
  })
  const [exportSaving, setExportSaving] = useState(false)

  const [suppliers, setSuppliers] = useState<SettingsSupplier[]>([])
  const [suppliersTotal, setSuppliersTotal] = useState(0)
  const [supplierPage, setSupplierPage] = useState(1)
  const [supplierSearchInput, setSupplierSearchInput] = useState('')
  const [supplierQuery, setSupplierQuery] = useState('')
  const [showInactiveSuppliers, setShowInactiveSuppliers] = useState(false)
  const [suppliersLoading, setSuppliersLoading] = useState(false)
  const [supplierModalOpen, setSupplierModalOpen] = useState(false)
  const [supplierModalMode, setSupplierModalMode] = useState<'create' | 'edit'>('create')
  const [editingSupplierId, setEditingSupplierId] = useState<number | null>(null)
  const [supplierForm, setSupplierForm] = useState<SupplierFormState>(createEmptySupplierForm())
  const [supplierErrors, setSupplierErrors] = useState<SupplierFormErrors>({})
  const [supplierSaving, setSupplierSaving] = useState(false)
  const [supplierDeactivateTarget, setSupplierDeactivateTarget] = useState<SettingsSupplier | null>(
    null
  )
  const [supplierDeactivateLoading, setSupplierDeactivateLoading] = useState(false)

  const [users, setUsers] = useState<SettingsUser[]>([])
  const [userModalOpen, setUserModalOpen] = useState(false)
  const [userModalMode, setUserModalMode] = useState<'create' | 'edit'>('create')
  const [editingUserId, setEditingUserId] = useState<number | null>(null)
  const [userForm, setUserForm] = useState<UserFormState>(createEmptyUserForm())
  const [userErrors, setUserErrors] = useState<UserFormErrors>({})
  const [userSaving, setUserSaving] = useState(false)
  const [userDeactivateTarget, setUserDeactivateTarget] = useState<SettingsUser | null>(null)
  const [userDeactivateLoading, setUserDeactivateLoading] = useState(false)

  const quotaArticleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const initialLoadStartedRef = useRef(false)
  const suppliersLoadedRef = useRef(false)
  const skipNextSuppliersEffectRef = useRef(false)

  const roleLabels = useMemo(() => roleDisplayNameMap(roles), [roles])
  const supplierTotalPages = Math.max(1, Math.ceil(suppliersTotal / SUPPLIERS_PER_PAGE))

  const roleOptions = useMemo(
    () =>
      ROLE_ORDER.map((role) => ({
        value: role,
        label: roleLabels[role] ?? role,
      })),
    [roleLabels]
  )

  const quotaCategoryOptions = useMemo(
    () =>
      categoryLookupOptions.map((category) => ({
        value: String(category.id),
        label: category.label_hr,
      })),
    [categoryLookupOptions]
  )

  const quotaUomOptions = useMemo(
    () =>
      uomLookupOptions.map((uom) => ({
        value: uom.code,
        label: `${uom.code} — ${uom.label_hr}`,
      })),
    [uomLookupOptions]
  )

  const mergedQuotaArticleOptions = useMemo(() => {
    const byId = new Map<number, OrderArticleLookupItem>()
    if (quotaForm.selectedArticle) {
      byId.set(quotaForm.selectedArticle.article_id, quotaForm.selectedArticle)
    }
    quotaArticleOptions.forEach((article) => {
      byId.set(article.article_id, article)
    })
    return Array.from(byId.values())
  }, [quotaArticleOptions, quotaForm.selectedArticle])

  const quotaArticleSelectData = useMemo(
    () =>
      mergedQuotaArticleOptions.map((article) => ({
        value: String(article.article_id),
        label: quotaArticleLabel(article),
      })),
    [mergedQuotaArticleOptions]
  )

  const loadSuppliers = useCallback(
    async (
      pageNumber = supplierPage,
      query = supplierQuery,
      includeInactive = showInactiveSuppliers
    ) => {
      setSuppliersLoading(true)

      try {
        const response = await runWithRetry(() =>
          settingsApi.listSuppliers({
            page: pageNumber,
            perPage: SUPPLIERS_PER_PAGE,
            q: query || undefined,
            includeInactive,
          })
        )

        setSuppliers(response.items)
        setSuppliersTotal(response.total)
        suppliersLoadedRef.current = true
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
          return
        }

        setLoadErrorMessage(
          getApiErrorBody(error)?.message ?? 'Greška pri učitavanju dobavljača.'
        )
      } finally {
        setSuppliersLoading(false)
      }
    },
    [showInactiveSuppliers, supplierPage, supplierQuery]
  )

  const loadInitialData = useCallback(async () => {
    setPageLoading(true)
    setLoadErrorMessage(null)

    try {
      const [
        general,
        rolesResponse,
        settingsUoms,
        settingsCategories,
        quotasResponse,
        barcode,
        exportSettings,
        suppliersResponse,
        usersResponse,
        quotaCategories,
        quotaUoms,
      ] = await runWithRetry(() =>
        Promise.all([
          settingsApi.getGeneral(),
          settingsApi.getRoles(),
          settingsApi.getUoms(),
          settingsApi.getCategories(),
          settingsApi.getQuotas(),
          settingsApi.getBarcode(),
          settingsApi.getExport(),
          settingsApi.listSuppliers({
            page: supplierPage,
            perPage: SUPPLIERS_PER_PAGE,
            q: supplierQuery || undefined,
            includeInactive: showInactiveSuppliers,
          }),
          settingsApi.getUsers(),
          articlesApi.lookupCategories(),
          articlesApi.lookupUoms(),
        ])
      )

      setGeneralForm(general)
      setRoles(rolesResponse)
      setRolesForm(roleDisplayNameMap(rolesResponse))
      await applyGeneralSettings(general)
      applyRoleDisplayNames(rolesResponse)
      setUoms(settingsUoms)
      setUomLookupOptions(quotaUoms)
      setCategories(settingsCategories)
      setCategoryLookupOptions(quotaCategories)
      setQuotas(sortQuotas(quotasResponse))
      setBarcodeForm(barcode)
      setExportForm(exportSettings)
      setSuppliers(suppliersResponse.items)
      setSuppliersTotal(suppliersResponse.total)
      setUsers(sortUsers(usersResponse))
      suppliersLoadedRef.current = true
      skipNextSuppliersEffectRef.current = true
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
      } else {
        setLoadErrorMessage(
          getApiErrorBody(error)?.message ?? 'Greška pri učitavanju postavki.'
        )
      }
    } finally {
      setPageLoading(false)
    }
  }, [
    applyGeneralSettings,
    applyRoleDisplayNames,
    showInactiveSuppliers,
    supplierPage,
    supplierQuery,
  ])

  useEffect(() => {
    if (initialLoadStartedRef.current) {
      return
    }

    initialLoadStartedRef.current = true
    void loadInitialData()
  }, [loadInitialData])

  useEffect(() => {
    if (!suppliersLoadedRef.current) {
      return
    }

    if (skipNextSuppliersEffectRef.current) {
      skipNextSuppliersEffectRef.current = false
      return
    }

    void loadSuppliers(supplierPage, supplierQuery, showInactiveSuppliers)
  }, [loadSuppliers, showInactiveSuppliers, supplierPage, supplierQuery])

  useEffect(() => {
    const timer = setTimeout(() => {
      setSupplierPage(1)
      setSupplierQuery(supplierSearchInput.trim())
    }, 400)

    return () => {
      clearTimeout(timer)
    }
  }, [supplierSearchInput])

  useEffect(() => {
    if (!quotaModalOpen || quotaForm.scope !== 'GLOBAL_ARTICLE_OVERRIDE') {
      setQuotaArticleSearching(false)
      return
    }

    if (quotaArticleTimerRef.current) {
      clearTimeout(quotaArticleTimerRef.current)
    }

    const normalized = quotaArticleSearchValue.trim()

    if (!normalized) {
      setQuotaArticleSearching(false)
      setQuotaArticleOptions([])
      return
    }

    setQuotaArticleSearching(true)

    quotaArticleTimerRef.current = setTimeout(async () => {
      try {
        const response = await runWithRetry(() => ordersApi.lookupArticles(normalized))
        setQuotaArticleOptions(response.items)
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
          return
        }

        showErrorToast(getApiErrorBody(error)?.message ?? 'Dohvat artikala nije uspio.')
        setQuotaArticleOptions([])
      } finally {
        setQuotaArticleSearching(false)
      }
    }, 300)

    return () => {
      if (quotaArticleTimerRef.current) {
        clearTimeout(quotaArticleTimerRef.current)
      }
    }
  }, [quotaArticleSearchValue, quotaForm.scope, quotaModalOpen])

  const handleGeneralSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setGeneralSaving(true)

    try {
      const response = await settingsApi.updateGeneral(generalForm)
      setGeneralForm(response)
      await applyGeneralSettings(response)
      showSuccessToast('Opće postavke su spremljene.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      showErrorToast(
        getApiErrorBody(error)?.message ?? 'Spremanje općih postavki nije uspjelo.'
      )
    } finally {
      setGeneralSaving(false)
    }
  }

  const handleRolesSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setRolesSaving(true)

    const payload = ROLE_ORDER.map((role) => ({
      role,
      display_name: rolesForm[role].trim(),
    }))

    try {
      const response = await settingsApi.updateRoles(payload)
      setRoles(response)
      setRolesForm(roleDisplayNameMap(response))
      applyRoleDisplayNames(response)
      showSuccessToast('Nazivi rola su spremljeni.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Spremanje rola nije uspjelo.')
    } finally {
      setRolesSaving(false)
    }
  }

  const handleCreateUom = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextErrors: UomFormErrors = {}
    if (!uomForm.code.trim()) {
      nextErrors.code = 'Šifra je obavezna.'
    }
    if (!uomForm.label_hr.trim()) {
      nextErrors.label_hr = 'Naziv (HR) je obavezan.'
    }

    setUomErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }

    setUomSaving(true)

    const payload: CreateSettingsUomPayload = {
      code: uomForm.code.trim(),
      label_hr: uomForm.label_hr.trim(),
      label_en: normalizeOptionalText(uomForm.label_en),
      decimal_display: uomForm.decimal_display,
    }

    try {
      const response = await settingsApi.createUom(payload)
      setUoms((current) => sortUoms([...current, response]))
      setUomLookupOptions((current) =>
        sortUomLookupOptions([
          ...current,
          {
            code: response.code,
            label_hr: response.label_hr,
            decimal_display: response.decimal_display,
          },
        ])
      )
      setShowAddUomForm(false)
      setUomForm(createEmptyUomForm())
      setUomErrors({})
      showSuccessToast('Nova jedinica mjere je dodana.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      const apiError = getApiErrorBody(error)
      if (apiError?.error === 'UOM_CODE_EXISTS') {
        setUomErrors({ code: 'Šifra jedinice već postoji.' })
      } else {
        showErrorToast(apiError?.message ?? 'Dodavanje jedinice mjere nije uspjelo.')
      }
    } finally {
      setUomSaving(false)
    }
  }

  const handleCategorySave = async (categoryId: number) => {
    const category = categories.find((item) => item.id === categoryId)
    if (!category) {
      return
    }

    setCategorySavingId(categoryId)

    try {
      const response = await settingsApi.updateCategory(categoryId, {
        label_hr: category.label_hr,
        label_en: normalizeOptionalText(category.label_en ?? ''),
        is_personal_issue: category.is_personal_issue,
      })

      setCategories((current) => replaceItemById(current, response))
      setCategoryLookupOptions((current) =>
        current.map((item) =>
          item.id === response.id
            ? { ...item, label_hr: response.label_hr }
            : item
        )
      )
      showSuccessToast(`Kategorija "${response.key}" je spremljena.`)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Spremanje kategorije nije uspjelo.')
    } finally {
      setCategorySavingId(null)
    }
  }

  const openCreateQuota = () => {
    setQuotaModalMode('create')
    setEditingQuotaId(null)
    setQuotaForm(createEmptyQuotaForm())
    setQuotaErrors({})
    setQuotaArticleSearchValue('')
    setQuotaArticleOptions([])
    setQuotaModalOpen(true)
  }

  const openEditQuota = (quota: SettingsQuota) => {
    const selectedArticle =
      quota.scope === 'GLOBAL_ARTICLE_OVERRIDE' && quota.article_id
        ? {
            article_id: quota.article_id,
            article_no: quota.article_no ?? '',
            description: quota.article_description ?? '',
            uom: quota.uom,
            supplier_article_code: null,
            last_price: null,
          }
        : null

    setQuotaModalMode('edit')
    setEditingQuotaId(quota.id)
    setQuotaForm({
      scope: quota.scope,
      job_title: quota.job_title ?? '',
      category_id: quota.category_id ? String(quota.category_id) : null,
      article_id: quota.article_id ? String(quota.article_id) : null,
      selectedArticle,
      quantity: String(quota.quantity),
      uom: quota.uom,
      enforcement: quota.enforcement,
      reset_month: String(quota.reset_month),
    })
    setQuotaErrors({})
    setQuotaArticleSearchValue('')
    setQuotaArticleOptions([])
    setQuotaModalOpen(true)
  }

  const handleQuotaScopeChange = (value: string | null) => {
    const nextScope =
      value === 'JOB_TITLE_CATEGORY_DEFAULT'
        ? 'JOB_TITLE_CATEGORY_DEFAULT'
        : 'GLOBAL_ARTICLE_OVERRIDE'

    setQuotaForm((current) => ({
      ...current,
      scope: nextScope,
      job_title: nextScope === 'JOB_TITLE_CATEGORY_DEFAULT' ? current.job_title : '',
      category_id: nextScope === 'JOB_TITLE_CATEGORY_DEFAULT' ? current.category_id : null,
      article_id: nextScope === 'GLOBAL_ARTICLE_OVERRIDE' ? current.article_id : null,
      selectedArticle:
        nextScope === 'GLOBAL_ARTICLE_OVERRIDE' ? current.selectedArticle : null,
    }))
    setQuotaArticleSearchValue('')
    setQuotaErrors({})
  }

  const validateQuotaForm = (): QuotaFormErrors => {
    const nextErrors: QuotaFormErrors = {}

    if (quotaForm.scope === 'GLOBAL_ARTICLE_OVERRIDE' && !quotaForm.article_id) {
      nextErrors.article_id = 'Artikl je obavezan.'
    }

    if (quotaForm.scope === 'JOB_TITLE_CATEGORY_DEFAULT') {
      if (!quotaForm.job_title.trim()) {
        nextErrors.job_title = 'Radno mjesto je obavezno.'
      }
      if (!quotaForm.category_id) {
        nextErrors.category_id = 'Kategorija je obavezna.'
      }
    }

    const quantity = Number.parseFloat(quotaForm.quantity)
    if (!quotaForm.quantity.trim() || Number.isNaN(quantity) || quantity <= 0) {
      nextErrors.quantity = 'Količina mora biti veća od 0.'
    }

    if (!quotaForm.uom) {
      nextErrors.uom = 'JM je obavezna.'
    }

    if (!quotaForm.reset_month) {
      nextErrors.reset_month = 'Mjesec resetiranja je obavezan.'
    }

    return nextErrors
  }

  const handleQuotaSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextErrors = validateQuotaForm()
    setQuotaErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }

    setQuotaSaving(true)

    const payload = {
      scope: quotaForm.scope,
      job_title:
        quotaForm.scope === 'JOB_TITLE_CATEGORY_DEFAULT'
          ? quotaForm.job_title.trim()
          : undefined,
      category_id:
        quotaForm.scope === 'JOB_TITLE_CATEGORY_DEFAULT' && quotaForm.category_id
          ? Number(quotaForm.category_id)
          : undefined,
      article_id:
        quotaForm.scope === 'GLOBAL_ARTICLE_OVERRIDE' && quotaForm.article_id
          ? Number(quotaForm.article_id)
          : undefined,
      quantity: quotaForm.quantity.trim(),
      uom: quotaForm.uom!,
      enforcement: quotaForm.enforcement,
      reset_month: Number(quotaForm.reset_month),
    }

    try {
      const response =
        quotaModalMode === 'create'
          ? await settingsApi.createQuota(payload)
          : await settingsApi.updateQuota(editingQuotaId!, payload)

      setQuotas((current) => {
        const nextQuotas =
          quotaModalMode === 'create'
            ? [...current, response]
            : replaceItemById(current, response)
        return sortQuotas(nextQuotas)
      })
      setQuotaModalOpen(false)
      setQuotaForm(createEmptyQuotaForm())
      setQuotaErrors({})
      setQuotaArticleSearchValue('')
      setQuotaArticleOptions([])
      showSuccessToast(
        quotaModalMode === 'create' ? 'Kvota je dodana.' : 'Kvota je spremljena.'
      )
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Spremanje kvote nije uspjelo.')
    } finally {
      setQuotaSaving(false)
    }
  }

  const handleQuotaDelete = async () => {
    if (!quotaDeleteTarget) {
      return
    }

    setQuotaDeleteLoading(true)

    try {
      await settingsApi.deleteQuota(quotaDeleteTarget.id)
      setQuotas((current) => current.filter((quota) => quota.id !== quotaDeleteTarget.id))
      setQuotaDeleteTarget(null)
      showSuccessToast('Kvota je obrisana.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Brisanje kvote nije uspjelo.')
    } finally {
      setQuotaDeleteLoading(false)
    }
  }

  const validateBarcodeIp = (ip: string): string | null => {
    const trimmed = ip.trim()
    if (trimmed === '') return null // allow clearing
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/
    if (!ipv4Regex.test(trimmed)) {
      return 'Unesite ispravnu IPv4 adresu ili ostavite prazno.'
    }
    return null
  }

  const handleBarcodeSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const ipValidationError = validateBarcodeIp(barcodeForm.label_printer_ip)
    if (ipValidationError) {
      setBarcodeIpError(ipValidationError)
      return
    }
    setBarcodeIpError(null)
    setBarcodeSaving(true)

    try {
      const response = await settingsApi.updateBarcode(barcodeForm)
      setBarcodeForm(response)
      showSuccessToast('Barcode postavke su spremljene.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Spremanje barcode postavki nije uspjelo.')
    } finally {
      setBarcodeSaving(false)
    }
  }

  const handleExportSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setExportSaving(true)

    try {
      const response = await settingsApi.updateExport(exportForm)
      setExportForm(response)
      showSuccessToast('Export postavke su spremljene.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Spremanje export postavki nije uspjelo.')
    } finally {
      setExportSaving(false)
    }
  }

  const openCreateSupplier = () => {
    setSupplierModalMode('create')
    setEditingSupplierId(null)
    setSupplierForm(createEmptySupplierForm())
    setSupplierErrors({})
    setSupplierModalOpen(true)
  }

  const openEditSupplier = (supplier: SettingsSupplier) => {
    setSupplierModalMode('edit')
    setEditingSupplierId(supplier.id)
    setSupplierForm({
      internal_code: supplier.internal_code,
      name: supplier.name,
      contact_person: supplier.contact_person ?? '',
      phone: supplier.phone ?? '',
      email: supplier.email ?? '',
      address: supplier.address ?? '',
      iban: supplier.iban ?? '',
      note: supplier.note ?? '',
    })
    setSupplierErrors({})
    setSupplierModalOpen(true)
  }

  const validateSupplierForm = (): SupplierFormErrors => {
    const nextErrors: SupplierFormErrors = {}

    if (supplierModalMode === 'create' && !supplierForm.internal_code.trim()) {
      nextErrors.internal_code = 'Interna šifra je obavezna.'
    }

    if (!supplierForm.name.trim()) {
      nextErrors.name = 'Naziv dobavljača je obavezan.'
    } else if (supplierForm.name.trim().length > 200) {
      nextErrors.name = 'Naziv može imati najviše 200 znakova.'
    }

    if (supplierForm.note.trim().length > 1000) {
      nextErrors.note = 'Napomena može imati najviše 1000 znakova.'
    }

    return nextErrors
  }

  const refreshSuppliers = async (pageNumber = supplierPage) => {
    await loadSuppliers(pageNumber, supplierQuery, showInactiveSuppliers)
  }

  const handleSupplierSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextErrors = validateSupplierForm()
    setSupplierErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }

    setSupplierSaving(true)

    try {
      if (supplierModalMode === 'create') {
        await settingsApi.createSupplier(toSupplierPayload(supplierForm))
        setSupplierModalOpen(false)
        setSupplierPage(1)
        await refreshSuppliers(1)
        showSuccessToast('Dobavljač je kreiran.')
      } else {
        await settingsApi.updateSupplier(editingSupplierId!, toSupplierUpdatePayload(supplierForm))
        setSupplierModalOpen(false)
        await refreshSuppliers()
        showSuccessToast('Dobavljač je spremljen.')
      }
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      const apiError = getApiErrorBody(error)
      if (apiError?.error === 'SUPPLIER_CODE_EXISTS') {
        setSupplierErrors({ internal_code: 'Interna šifra već postoji.' })
      } else {
        showErrorToast(apiError?.message ?? 'Spremanje dobavljača nije uspjelo.')
      }
    } finally {
      setSupplierSaving(false)
    }
  }

  const handleSupplierDeactivate = async () => {
    if (!supplierDeactivateTarget) {
      return
    }

    setSupplierDeactivateLoading(true)

    try {
      await settingsApi.deactivateSupplier(supplierDeactivateTarget.id)
      setSupplierDeactivateTarget(null)
      await refreshSuppliers()
      showSuccessToast('Dobavljač je deaktiviran.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Deaktivacija dobavljača nije uspjela.')
    } finally {
      setSupplierDeactivateLoading(false)
    }
  }

  const openCreateUser = () => {
    setUserModalMode('create')
    setEditingUserId(null)
    setUserForm(createEmptyUserForm())
    setUserErrors({})
    setUserModalOpen(true)
  }

  const openEditUser = (user: SettingsUser) => {
    setUserModalMode('edit')
    setEditingUserId(user.id)
    setUserForm({
      username: user.username,
      password: '',
      role: user.role,
      is_active: user.is_active,
    })
    setUserErrors({})
    setUserModalOpen(true)
  }

  const editingUser = editingUserId === null
    ? null
    : users.find((user) => user.id === editingUserId) ?? null
  const isAdminPromotion =
    userModalMode === 'edit'
    && userForm.role === 'ADMIN'
    && editingUser !== null
    && editingUser.role !== 'ADMIN'

  const validateUserForm = (): UserFormErrors => {
    const nextErrors: UserFormErrors = {}

    if (userModalMode === 'create') {
      if (!userForm.username.trim()) {
        nextErrors.username = 'Korisničko ime je obavezno.'
      } else if (userForm.username.trim().length > 50) {
        nextErrors.username = 'Korisničko ime može imati najviše 50 znakova.'
      }
    }

    if (!userForm.role) {
      nextErrors.role = 'Rola je obavezna.'
    }

    const passwordMinLength = getUserPasswordMinLength(userForm.role ?? 'OPERATOR')

    const hasPasswordReset = userForm.password.trim().length > 0

    if (userModalMode === 'create') {
      if (userForm.password.length < passwordMinLength) {
        nextErrors.password = `Lozinka mora imati najmanje ${passwordMinLength} znakova.`
      }
    } else if (isAdminPromotion && !hasPasswordReset) {
      nextErrors.password = 'Promocija u admin rolu zahtijeva novu lozinku od najmanje 12 znakova.'
    } else if (hasPasswordReset && userForm.password.length < passwordMinLength) {
      nextErrors.password = `Nova lozinka mora imati najmanje ${passwordMinLength} znakova.`
    }

    return nextErrors
  }

  const handleUserSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextErrors = validateUserForm()
    setUserErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }

    setUserSaving(true)

    try {
      const response =
        userModalMode === 'create'
          ? await settingsApi.createUser(toUserPayload(userForm))
          : await settingsApi.updateUser(editingUserId!, toUserUpdatePayload(userForm))

      setUsers((current) => {
        const nextUsers =
          userModalMode === 'create'
            ? [...current, response]
            : replaceItemById(current, response)
        return sortUsers(nextUsers)
      })
      setUserModalOpen(false)
      showSuccessToast(
        userModalMode === 'create'
          ? 'Korisnik je kreiran.'
          : 'Korisnički račun je spremljen.'
      )
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      const apiError = getApiErrorBody(error)
      if (apiError?.error === 'USERNAME_EXISTS') {
        setUserErrors({ username: 'Korisničko ime već postoji.' })
      } else if (apiError?.error === 'SELF_DEACTIVATION_FORBIDDEN') {
        showWarningToast(apiError.message ?? 'Ne možete deaktivirati vlastiti račun.')
      } else {
        showErrorToast(apiError?.message ?? 'Spremanje korisnika nije uspjelo.')
      }
    } finally {
      setUserSaving(false)
    }
  }

  const handleUserDeactivate = async () => {
    if (!userDeactivateTarget) {
      return
    }

    setUserDeactivateLoading(true)

    try {
      const response = await settingsApi.deactivateUser(userDeactivateTarget.id)
      setUsers((current) => sortUsers(replaceItemById(current, response)))
      setUserDeactivateTarget(null)
      showSuccessToast('Korisnički račun je deaktiviran.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setLoadErrorMessage(SETTINGS_CONNECTION_ERROR_MESSAGE)
        return
      }

      const apiError = getApiErrorBody(error)
      if (apiError?.error === 'SELF_DEACTIVATION_FORBIDDEN') {
        showWarningToast(apiError.message ?? 'Ne možete deaktivirati vlastiti račun.')
      } else {
        showErrorToast(apiError?.message ?? 'Deaktivacija korisnika nije uspjela.')
      }
    } finally {
      setUserDeactivateLoading(false)
    }
  }

  const handleRetry = () => {
    suppliersLoadedRef.current = false
    void loadInitialData()
  }

  if (pageLoading) {
    return <FullPageState title="Učitavanje…" loading />
  }

  if (loadErrorMessage) {
    return (
      <FullPageState
        title={
          loadErrorMessage === SETTINGS_CONNECTION_ERROR_MESSAGE
            ? 'Greška pri povezivanju'
            : 'Greška pri učitavanju'
        }
        message={loadErrorMessage}
        actionLabel="Pokušaj ponovno"
        onAction={handleRetry}
      />
    )
  }

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>Postavke</Title>
        <Text c="dimmed" size="sm" mt={4}>
          Administracija instalacijskih postavki, dobavljača i korisnika.
        </Text>
      </div>

      <SettingsSection
        title="1. General"
        description="Naziv lokacije, jezik sučelja i operativna vremenska zona."
      >
        <form onSubmit={handleGeneralSave}>
          <Stack gap="md">
            <SimpleGrid cols={{ base: 1, md: 3 }}>
              <TextInput
                label="Naziv lokacije"
                value={generalForm.location_name}
                onChange={(event) =>
                  setGeneralForm((current) => ({
                    ...current,
                    location_name: event.currentTarget.value,
                  }))
                }
                required
              />
              <Select
                label="Zadani jezik sučelja"
                data={LANGUAGE_OPTIONS}
                value={generalForm.default_language}
                onChange={(value) =>
                  setGeneralForm((current) => ({
                    ...current,
                    default_language: value ?? 'hr',
                  }))
                }
                allowDeselect={false}
              />
              <Select
                label="Operativna vremenska zona"
                data={timezoneOptions}
                value={generalForm.timezone}
                onChange={(value) =>
                  setGeneralForm((current) => ({
                    ...current,
                    timezone: value ?? current.timezone,
                  }))
                }
                searchable
                allowDeselect={false}
              />
            </SimpleGrid>

            <Group justify="flex-end">
              <Button type="submit" loading={generalSaving}>
                Spremi General
              </Button>
            </Group>
          </Stack>
        </form>
      </SettingsSection>

      <SettingsSection
        title="2. Roles"
        description="Display nazivi sistemskih rola za UI prikaz."
      >
        <form onSubmit={handleRolesSave}>
          <Stack gap="md">
            <SimpleGrid cols={{ base: 1, md: 2 }}>
              {ROLE_ORDER.map((role) => (
                <TextInput
                  key={role}
                  label={role}
                  value={rolesForm[role]}
                  onChange={(event) =>
                    setRolesForm((current) => ({
                      ...current,
                      [role]: event.currentTarget.value,
                    }))
                  }
                  required
                />
              ))}
            </SimpleGrid>

            <Group justify="flex-end">
              <Button type="submit" loading={rolesSaving}>
                Spremi Roles
              </Button>
            </Group>
          </Stack>
        </form>
      </SettingsSection>

      <SettingsSection
        title="3. UOM Catalog"
        description="Katalog jedinica mjere i dodavanje novih unosa."
      >
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Text size="sm" c="dimmed">
              Postojeće jedinice mjere dostupne za artikle i kvote.
            </Text>
            <Button
              variant={showAddUomForm ? 'default' : 'filled'}
              onClick={() => {
                if (showAddUomForm) {
                  setShowAddUomForm(false)
                  setUomForm(createEmptyUomForm())
                  setUomErrors({})
                } else {
                  setShowAddUomForm(true)
                }
              }}
            >
              {showAddUomForm ? 'Zatvori formu' : 'Dodaj jedinicu'}
            </Button>
          </Group>

          <Paper withBorder radius="md">
            <ScrollArea>
              <Table highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Šifra</Table.Th>
                    <Table.Th>Naziv (HR)</Table.Th>
                    <Table.Th>Naziv (EN)</Table.Th>
                    <Table.Th>Decimalni prikaz</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {uoms.length === 0 ? (
                    <Table.Tr>
                      <Table.Td colSpan={4}>
                        <Text ta="center" c="dimmed" py="md">
                          Nema jedinica mjere.
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ) : (
                    uoms.map((uom) => (
                      <Table.Tr key={uom.id}>
                        <Table.Td>{uom.code}</Table.Td>
                        <Table.Td>{uom.label_hr}</Table.Td>
                        <Table.Td>{uom.label_en || '—'}</Table.Td>
                        <Table.Td>{uom.decimal_display ? 'Da' : 'Ne'}</Table.Td>
                      </Table.Tr>
                    ))
                  )}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </Paper>

          {showAddUomForm ? (
            <Paper withBorder radius="md" p="md">
              <form onSubmit={handleCreateUom}>
                <Stack gap="md">
                  <SimpleGrid cols={{ base: 1, md: 4 }}>
                    <TextInput
                      label="Šifra"
                      value={uomForm.code}
                      onChange={(event) =>
                        setUomForm((current) => ({
                          ...current,
                          code: event.currentTarget.value,
                        }))
                      }
                      error={uomErrors.code}
                      required
                    />
                    <TextInput
                      label="Naziv (HR)"
                      value={uomForm.label_hr}
                      onChange={(event) =>
                        setUomForm((current) => ({
                          ...current,
                          label_hr: event.currentTarget.value,
                        }))
                      }
                      error={uomErrors.label_hr}
                      required
                    />
                    <TextInput
                      label="Naziv (EN)"
                      value={uomForm.label_en}
                      onChange={(event) =>
                        setUomForm((current) => ({
                          ...current,
                          label_en: event.currentTarget.value,
                        }))
                      }
                    />
                    <Checkbox
                      mt={30}
                      label="Decimalni prikaz"
                      checked={uomForm.decimal_display}
                      onChange={(event) =>
                        setUomForm((current) => ({
                          ...current,
                          decimal_display: event.currentTarget.checked,
                        }))
                      }
                    />
                  </SimpleGrid>

                  <Group justify="flex-end">
                    <Button type="submit" loading={uomSaving}>
                      Spremi jedinicu
                    </Button>
                  </Group>
                </Stack>
              </form>
            </Paper>
          ) : null}
        </Stack>
      </SettingsSection>

      <SettingsSection
        title="4. Article Categories"
        description="HR/EN nazivi kategorija i oznaka osobnog izdavanja."
      >
        <Paper withBorder radius="md">
          <ScrollArea>
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Key</Table.Th>
                  <Table.Th>Naziv (HR)</Table.Th>
                  <Table.Th>Naziv (EN)</Table.Th>
                  <Table.Th>Osobno izdavanje</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {categories.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={5}>
                      <Text ta="center" c="dimmed" py="md">
                        Nema kategorija.
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  categories.map((category) => (
                    <Table.Tr key={category.id}>
                      <Table.Td>{category.key}</Table.Td>
                      <Table.Td>
                        <TextInput
                          value={category.label_hr}
                          onChange={(event) =>
                            setCategories((current) =>
                              current.map((item) =>
                                item.id === category.id
                                  ? { ...item, label_hr: event.currentTarget.value }
                                  : item
                              )
                            )
                          }
                        />
                      </Table.Td>
                      <Table.Td>
                        <TextInput
                          value={category.label_en ?? ''}
                          onChange={(event) =>
                            setCategories((current) =>
                              current.map((item) =>
                                item.id === category.id
                                  ? { ...item, label_en: event.currentTarget.value }
                                  : item
                              )
                            )
                          }
                        />
                      </Table.Td>
                      <Table.Td>
                        <Checkbox
                          checked={category.is_personal_issue}
                          onChange={(event) =>
                            setCategories((current) =>
                              current.map((item) =>
                                item.id === category.id
                                  ? {
                                      ...item,
                                      is_personal_issue: event.currentTarget.checked,
                                    }
                                  : item
                              )
                            )
                          }
                        />
                      </Table.Td>
                      <Table.Td>
                        <Button
                          size="xs"
                          loading={categorySavingId === category.id}
                          onClick={() => {
                            void handleCategorySave(category.id)
                          }}
                        >
                          Spremi
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        </Paper>
      </SettingsSection>

      <SettingsSection
        title="5. Quotas"
        description="Globalni override po artiklu i default po radnom mjestu + kategoriji."
      >
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Text size="sm" c="dimmed">
              Kvote se primjenjuju odmah nakon spremanja.
            </Text>
            <Button onClick={openCreateQuota}>Dodaj kvotu</Button>
          </Group>

          <Paper withBorder radius="md">
            <ScrollArea>
              <Table highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Scope</Table.Th>
                    <Table.Th>Radno mjesto</Table.Th>
                    <Table.Th>Artikl / kategorija</Table.Th>
                    <Table.Th>Količina</Table.Th>
                    <Table.Th>JM</Table.Th>
                    <Table.Th>Pravilo</Table.Th>
                    <Table.Th>Reset</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {quotas.length === 0 ? (
                    <Table.Tr>
                      <Table.Td colSpan={8}>
                        <Text ta="center" c="dimmed" py="md">
                          Nema definiranih kvota.
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ) : (
                    quotas.map((quota) => (
                      <Table.Tr key={quota.id}>
                        <Table.Td>{scopeLabel(quota.scope)}</Table.Td>
                        <Table.Td>{quota.job_title || '—'}</Table.Td>
                        <Table.Td>{quotaTargetLabel(quota)}</Table.Td>
                        <Table.Td>{quota.quantity}</Table.Td>
                        <Table.Td>{quota.uom}</Table.Td>
                        <Table.Td>{enforcementLabel(quota.enforcement)}</Table.Td>
                        <Table.Td>{quota.reset_month}</Table.Td>
                        <Table.Td>
                          <Group gap="xs" justify="flex-end">
                            <Button
                              size="xs"
                              variant="light"
                              onClick={() => openEditQuota(quota)}
                            >
                              Uredi
                            </Button>
                            <Button
                              size="xs"
                              variant="subtle"
                              color="red"
                              onClick={() => setQuotaDeleteTarget(quota)}
                            >
                              Obriši
                            </Button>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))
                  )}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </Paper>
        </Stack>
      </SettingsSection>

      <SettingsSection
        title="6. Barcode"
        description="Format barkoda, naziv printera (PDF ispis) i konfiguracija direktnog label printera."
      >
        <form onSubmit={handleBarcodeSave}>
          <Stack gap="md">
            <SimpleGrid cols={{ base: 1, md: 2 }}>
              <Select
                label="Barcode format"
                data={BARCODE_OPTIONS}
                value={barcodeForm.barcode_format}
                onChange={(value) =>
                  setBarcodeForm((current) => ({
                    ...current,
                    barcode_format: value ?? current.barcode_format,
                  }))
                }
                allowDeselect={false}
              />
              <TextInput
                label="Naziv printera (PDF)"
                description="Naziv printera u OS-u hosta za PDF ispis barkoda."
                value={barcodeForm.barcode_printer}
                onChange={(event) =>
                  setBarcodeForm((current) => ({
                    ...current,
                    barcode_printer: event.currentTarget.value,
                  }))
                }
              />
            </SimpleGrid>

            <Divider label="Direktni label printer (ZPL)" labelPosition="left" />

            <SimpleGrid cols={{ base: 1, md: 3 }}>
              <TextInput
                label="IP adresa printera"
                description="IPv4 adresa label printera. Ostavite prazno ako printer nije konfiguriran."
                placeholder="npr. 192.168.1.100"
                value={barcodeForm.label_printer_ip}
                error={barcodeIpError}
                onChange={(event) => {
                  setBarcodeIpError(null)
                  setBarcodeForm((current) => ({
                    ...current,
                    label_printer_ip: event.currentTarget.value,
                  }))
                }}
              />
              <TextInput
                label="Port printera"
                description="Zadano: 9100"
                placeholder="9100"
                value={String(barcodeForm.label_printer_port)}
                onChange={(event) => {
                  const raw = event.currentTarget.value
                  const parsed = parseInt(raw, 10)
                  setBarcodeForm((current) => ({
                    ...current,
                    label_printer_port: Number.isNaN(parsed) ? current.label_printer_port : parsed,
                  }))
                }}
              />
              <Select
                label="Model printera"
                description="Protokol za slanje naljepnica."
                data={LABEL_PRINTER_MODEL_OPTIONS}
                value={barcodeForm.label_printer_model}
                onChange={(value) =>
                  setBarcodeForm((current) => ({
                    ...current,
                    label_printer_model: (value as SettingsPrinterModel) ?? current.label_printer_model,
                  }))
                }
                allowDeselect={false}
              />
            </SimpleGrid>

            <Group justify="flex-end">
              <Button type="submit" loading={barcodeSaving}>
                Spremi Barcode
              </Button>
            </Group>
          </Stack>
        </form>
      </SettingsSection>

      <SettingsSection
        title="7. Export"
        description="Format Excela za izvoz podataka."
      >
        <form onSubmit={handleExportSave}>
          <Stack gap="md">
            <Select
              label="Excel format"
              data={EXPORT_OPTIONS}
              value={exportForm.export_format}
              onChange={(value) =>
                setExportForm((current) => ({
                  ...current,
                  export_format: value ?? current.export_format,
                }))
              }
              allowDeselect={false}
              maw={360}
            />

            <Group justify="flex-end">
              <Button type="submit" loading={exportSaving}>
                Spremi Export
              </Button>
            </Group>
          </Stack>
        </form>
      </SettingsSection>

      <SettingsSection
        title="8. Suppliers"
        description="Pretraga, kreiranje, uređivanje i deaktivacija dobavljača."
      >
        <Stack gap="md">
          <Group justify="space-between" align="flex-end">
            <Group align="flex-end" style={{ flex: 1 }}>
              <TextInput
                label="Pretraga"
                placeholder="Pretraži po internoj šifri ili nazivu..."
                value={supplierSearchInput}
                onChange={(event) => setSupplierSearchInput(event.currentTarget.value)}
                style={{ flex: 1 }}
              />
              <Checkbox
                label="Prikaži neaktivne"
                checked={showInactiveSuppliers}
                onChange={(event) => {
                  setSupplierPage(1)
                  setShowInactiveSuppliers(event.currentTarget.checked)
                }}
              />
            </Group>
            <Button onClick={openCreateSupplier}>Novi dobavljač</Button>
          </Group>

          <Paper withBorder radius="md">
            {suppliersLoading ? (
              <Group justify="center" p="xl">
                <Loader size="sm" />
              </Group>
            ) : (
              <>
                <ScrollArea>
                  <Table highlightOnHover>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Interna šifra</Table.Th>
                        <Table.Th>Naziv</Table.Th>
                        <Table.Th>Kontakt osoba</Table.Th>
                        <Table.Th>Telefon</Table.Th>
                        <Table.Th>Status</Table.Th>
                        <Table.Th />
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {suppliers.length === 0 ? (
                        <Table.Tr>
                          <Table.Td colSpan={6}>
                            <Text ta="center" c="dimmed" py="md">
                              Nema dobavljača za zadane filtre.
                            </Text>
                          </Table.Td>
                        </Table.Tr>
                      ) : (
                        suppliers.map((supplier) => (
                          <Table.Tr key={supplier.id}>
                            <Table.Td>{supplier.internal_code}</Table.Td>
                            <Table.Td>{supplier.name}</Table.Td>
                            <Table.Td>{supplier.contact_person || '—'}</Table.Td>
                            <Table.Td>{supplier.phone || '—'}</Table.Td>
                            <Table.Td>
                              <Badge color={supplier.is_active ? 'green' : 'gray'}>
                                {supplierStatusLabel(supplier.is_active)}
                              </Badge>
                            </Table.Td>
                            <Table.Td>
                              <Group gap="xs" justify="flex-end">
                                <Button
                                  size="xs"
                                  variant="light"
                                  onClick={() => openEditSupplier(supplier)}
                                >
                                  Uredi
                                </Button>
                                <Button
                                  size="xs"
                                  variant="subtle"
                                  color="red"
                                  disabled={!supplier.is_active}
                                  onClick={() => setSupplierDeactivateTarget(supplier)}
                                >
                                  Deaktiviraj
                                </Button>
                              </Group>
                            </Table.Td>
                          </Table.Tr>
                        ))
                      )}
                    </Table.Tbody>
                  </Table>
                </ScrollArea>

                {suppliersTotal > SUPPLIERS_PER_PAGE ? (
                  <>
                    <Divider />
                    <Group justify="center" p="md">
                      <Pagination
                        value={supplierPage}
                        onChange={setSupplierPage}
                        total={supplierTotalPages}
                      />
                    </Group>
                  </>
                ) : null}
              </>
            )}
          </Paper>
        </Stack>
      </SettingsSection>

      <SettingsSection
        title="9. Users"
        description="Kreiranje, uređivanje i deaktivacija korisničkih računa."
      >
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Alert color="blue" variant="light" style={{ flex: 1 }}>
              Vlastiti račun nije moguće deaktivirati.
            </Alert>
            <Button onClick={openCreateUser}>Novi korisnik</Button>
          </Group>

          <Paper withBorder radius="md">
            <ScrollArea>
              <Table highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Korisničko ime</Table.Th>
                    <Table.Th>Rola</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Kreiran</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {users.length === 0 ? (
                    <Table.Tr>
                      <Table.Td colSpan={5}>
                        <Text ta="center" c="dimmed" py="md">
                          Nema korisnika.
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ) : (
                    users.map((user) => {
                      const isSelf = user.id === currentUser?.id
                      return (
                        <Table.Tr key={user.id}>
                          <Table.Td>{user.username}</Table.Td>
                          <Table.Td>{roleLabels[user.role] ?? user.role}</Table.Td>
                          <Table.Td>
                            <Badge color={user.is_active ? 'green' : 'gray'}>
                              {user.is_active ? 'Aktivan' : 'Neaktivan'}
                            </Badge>
                          </Table.Td>
                          <Table.Td>{formatDateTime(user.created_at)}</Table.Td>
                          <Table.Td>
                            <Group gap="xs" justify="flex-end">
                              <Button
                                size="xs"
                                variant="light"
                                onClick={() => openEditUser(user)}
                              >
                                Uredi
                              </Button>
                              <Button
                                size="xs"
                                variant="subtle"
                                color="red"
                                disabled={isSelf || !user.is_active}
                                onClick={() => setUserDeactivateTarget(user)}
                              >
                                Deaktiviraj
                              </Button>
                            </Group>
                            {isSelf ? (
                              <Text size="xs" c="dimmed" mt={4}>
                                Trenutni korisnik
                              </Text>
                            ) : null}
                          </Table.Td>
                        </Table.Tr>
                      )
                    })
                  )}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          </Paper>
        </Stack>
      </SettingsSection>

      <Modal
        opened={quotaModalOpen}
        onClose={() => setQuotaModalOpen(false)}
        title={quotaModalMode === 'create' ? 'Nova kvota' : 'Uredi kvotu'}
        size="lg"
      >
        <form onSubmit={handleQuotaSave}>
          <Stack gap="md">
            <Select
              label="Scope"
              data={QUOTA_SCOPE_OPTIONS}
              value={quotaForm.scope}
              onChange={handleQuotaScopeChange}
              allowDeselect={false}
            />

            {quotaForm.scope === 'GLOBAL_ARTICLE_OVERRIDE' ? (
              <Select
                label="Artikl"
                searchable
                value={quotaForm.article_id}
                onSearchChange={setQuotaArticleSearchValue}
                onChange={(value) => {
                  const selectedArticle =
                    mergedQuotaArticleOptions.find(
                      (article) => String(article.article_id) === value
                    ) ?? null
                  setQuotaForm((current) => ({
                    ...current,
                    article_id: value,
                    selectedArticle,
                  }))
                  setQuotaArticleSearchValue('')
                  setQuotaErrors((current) => ({ ...current, article_id: undefined }))
                }}
                data={quotaArticleSelectData}
                rightSection={quotaArticleSearching ? <Loader size="xs" /> : null}
                nothingFoundMessage={
                  quotaArticleSearchValue.trim()
                    ? 'Nema artikala za zadani pojam.'
                    : 'Počnite tipkati za pretragu artikala.'
                }
                error={quotaErrors.article_id}
              />
            ) : (
              <SimpleGrid cols={{ base: 1, md: 2 }}>
                <TextInput
                  label="Radno mjesto"
                  value={quotaForm.job_title}
                  onChange={(event) =>
                    setQuotaForm((current) => ({
                      ...current,
                      job_title: event.currentTarget.value,
                    }))
                  }
                  error={quotaErrors.job_title}
                />
                <Select
                  label="Kategorija"
                  data={quotaCategoryOptions}
                  value={quotaForm.category_id}
                  onChange={(value) =>
                    setQuotaForm((current) => ({
                      ...current,
                      category_id: value,
                    }))
                  }
                  error={quotaErrors.category_id}
                  searchable
                />
              </SimpleGrid>
            )}

            <SimpleGrid cols={{ base: 1, md: 4 }}>
              <TextInput
                label="Količina"
                value={quotaForm.quantity}
                onChange={(event) =>
                  setQuotaForm((current) => ({
                    ...current,
                    quantity: event.currentTarget.value,
                  }))
                }
                error={quotaErrors.quantity}
              />
              <Select
                label="JM"
                data={quotaUomOptions}
                value={quotaForm.uom}
                onChange={(value) =>
                  setQuotaForm((current) => ({
                    ...current,
                    uom: value,
                  }))
                }
                error={quotaErrors.uom}
                searchable
              />
              <Select
                label="Pravilo"
                data={ENFORCEMENT_OPTIONS}
                value={quotaForm.enforcement}
                onChange={(value) =>
                  setQuotaForm((current) => ({
                    ...current,
                    enforcement: (value ?? 'WARN') as SettingsQuotaEnforcement,
                  }))
                }
                allowDeselect={false}
              />
              <Select
                label="Reset mjesec"
                data={MONTH_OPTIONS}
                value={quotaForm.reset_month}
                onChange={(value) =>
                  setQuotaForm((current) => ({
                    ...current,
                    reset_month: value ?? '1',
                  }))
                }
                error={quotaErrors.reset_month}
                allowDeselect={false}
              />
            </SimpleGrid>

            <Group justify="flex-end">
              <Button
                type="button"
                variant="default"
                onClick={() => setQuotaModalOpen(false)}
              >
                Odustani
              </Button>
              <Button type="submit" loading={quotaSaving}>
                {quotaModalMode === 'create' ? 'Spremi kvotu' : 'Ažuriraj kvotu'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={quotaDeleteTarget !== null}
        onClose={() => setQuotaDeleteTarget(null)}
        title="Obriši kvotu"
        centered
      >
        <Stack gap="md">
          <Text>
            Obriši odabranu kvotu? Povijest izdanja ostaje sačuvana, ali se pravilo
            više neće primjenjivati na buduća izdavanja.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setQuotaDeleteTarget(null)}>
              Odustani
            </Button>
            <Button color="red" loading={quotaDeleteLoading} onClick={() => void handleQuotaDelete()}>
              Obriši
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={supplierModalOpen}
        onClose={() => setSupplierModalOpen(false)}
        title={supplierModalMode === 'create' ? 'Novi dobavljač' : 'Uredi dobavljača'}
        size="lg"
      >
        <form onSubmit={handleSupplierSave}>
          <Stack gap="md">
            <SimpleGrid cols={{ base: 1, md: 2 }}>
              <TextInput
                label="Interna šifra"
                value={supplierForm.internal_code}
                onChange={(event) =>
                  setSupplierForm((current) => ({
                    ...current,
                    internal_code: event.currentTarget.value,
                  }))
                }
                disabled={supplierModalMode === 'edit'}
                error={supplierErrors.internal_code}
                required={supplierModalMode === 'create'}
              />
              <TextInput
                label="Naziv"
                value={supplierForm.name}
                onChange={(event) =>
                  setSupplierForm((current) => ({
                    ...current,
                    name: event.currentTarget.value,
                  }))
                }
                error={supplierErrors.name}
                required
              />
              <TextInput
                label="Kontakt osoba"
                value={supplierForm.contact_person}
                onChange={(event) =>
                  setSupplierForm((current) => ({
                    ...current,
                    contact_person: event.currentTarget.value,
                  }))
                }
              />
              <TextInput
                label="Telefon"
                value={supplierForm.phone}
                onChange={(event) =>
                  setSupplierForm((current) => ({
                    ...current,
                    phone: event.currentTarget.value,
                  }))
                }
              />
              <TextInput
                label="Email"
                value={supplierForm.email}
                onChange={(event) =>
                  setSupplierForm((current) => ({
                    ...current,
                    email: event.currentTarget.value,
                  }))
                }
              />
              <TextInput
                label="IBAN"
                value={supplierForm.iban}
                onChange={(event) =>
                  setSupplierForm((current) => ({
                    ...current,
                    iban: event.currentTarget.value,
                  }))
                }
              />
            </SimpleGrid>

            <TextInput
              label="Adresa"
              value={supplierForm.address}
              onChange={(event) =>
                setSupplierForm((current) => ({
                  ...current,
                  address: event.currentTarget.value,
                }))
              }
            />

            <Textarea
              label="Napomena"
              value={supplierForm.note}
              onChange={(event) =>
                setSupplierForm((current) => ({
                  ...current,
                  note: event.currentTarget.value,
                }))
              }
              error={supplierErrors.note}
              minRows={3}
            />

            <Group justify="flex-end">
              <Button
                type="button"
                variant="default"
                onClick={() => setSupplierModalOpen(false)}
              >
                Odustani
              </Button>
              <Button type="submit" loading={supplierSaving}>
                {supplierModalMode === 'create' ? 'Spremi dobavljača' : 'Ažuriraj dobavljača'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={supplierDeactivateTarget !== null}
        onClose={() => setSupplierDeactivateTarget(null)}
        title="Deaktiviraj dobavljača"
        centered
      >
        <Stack gap="md">
          <Text>
            Deaktivirati ovog dobavljača? Više se neće pojavljivati u formama
            narudžbenica.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSupplierDeactivateTarget(null)}>
              Odustani
            </Button>
            <Button
              color="red"
              loading={supplierDeactivateLoading}
              onClick={() => void handleSupplierDeactivate()}
            >
              Deaktiviraj
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={userModalOpen}
        onClose={() => setUserModalOpen(false)}
        title={userModalMode === 'create' ? 'Novi korisnik' : 'Uredi korisnika'}
      >
        <form onSubmit={handleUserSave}>
          <Stack gap="md">
            <TextInput
              label="Korisničko ime"
              value={userForm.username}
              onChange={(event) =>
                setUserForm((current) => ({
                  ...current,
                  username: event.currentTarget.value,
                }))
              }
              disabled={userModalMode === 'edit'}
              error={userErrors.username}
              required={userModalMode === 'create'}
            />

            <TextInput
              label={userModalMode === 'create' ? 'Lozinka' : 'Nova lozinka'}
              type="password"
              value={userForm.password}
              onChange={(event) =>
                setUserForm((current) => ({
                  ...current,
                  password: event.currentTarget.value,
                }))
              }
              description={
                isAdminPromotion
                  ? 'Promocija u admin rolu zahtijeva novu lozinku.'
                  : userModalMode === 'edit'
                  ? `Ostavite prazno ako lozinku ne želite mijenjati. Ako je mijenjate, za odabranu rolu mora imati najmanje ${getUserPasswordMinLength(userForm.role ?? 'OPERATOR')} znakova.`
                  : `Lozinka mora imati najmanje ${getUserPasswordMinLength(userForm.role ?? 'OPERATOR')} znakova.`
              }
              error={userErrors.password}
              required={userModalMode === 'create' || isAdminPromotion}
            />

            <Select
              label="Rola"
              data={roleOptions}
              value={userForm.role}
              onChange={(value) =>
                setUserForm((current) => ({
                  ...current,
                  role: (value ?? 'OPERATOR') as SystemRole,
                }))
              }
              error={userErrors.role}
              allowDeselect={false}
            />

            <Checkbox
              label="Aktivan račun"
              checked={userForm.is_active}
              disabled={userModalMode === 'edit' && editingUserId === currentUser?.id}
              onChange={(event) =>
                setUserForm((current) => ({
                  ...current,
                  is_active: event.currentTarget.checked,
                }))
              }
            />

            {userModalMode === 'edit' && editingUserId === currentUser?.id ? (
              <Text size="sm" c="dimmed">
                Ne možete deaktivirati vlastiti račun.
              </Text>
            ) : null}

            <Group justify="flex-end">
              <Button
                type="button"
                variant="default"
                onClick={() => setUserModalOpen(false)}
              >
                Odustani
              </Button>
              <Button type="submit" loading={userSaving}>
                {userModalMode === 'create' ? 'Spremi korisnika' : 'Ažuriraj korisnika'}
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={userDeactivateTarget !== null}
        onClose={() => setUserDeactivateTarget(null)}
        title="Deaktiviraj korisnika"
        centered
      >
        <Stack gap="md">
          <Text>
            Deaktivirati korisnički račun{' '}
            <strong>{userDeactivateTarget?.username}</strong>?
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setUserDeactivateTarget(null)}>
              Odustani
            </Button>
            <Button color="red" loading={userDeactivateLoading} onClick={() => void handleUserDeactivate()}>
              Deaktiviraj
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}
