import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ActionIcon,
  Badge,
  Button,
  Collapse,
  Group,
  Loader,
  Pagination,
  Paper,
  SegmentedControl,
  ScrollArea,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from '@mantine/core'
import { IconX, IconChevronDown, IconChevronUp } from '@tabler/icons-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts'

import {
  articlesApi,
  type ArticleAliasItem,
  type ArticleCategoryLookupItem,
  type ArticleStatsResponse,
  type SupplierLookupItem,
  type ArticleTransactionItem,
  type ArticleUomLookupItem,
  type StatPeriod,
  type WarehouseArticleDetail,
} from '../../api/articles'
import { settingsApi, type SettingsBarcode } from '../../api/settings'
import FullPageState from '../../components/shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import {
  getApiErrorBody,
  getApiErrorBodyAsync,
  isNetworkOrServerError,
  runWithRetry,
} from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import WarehouseArticleForm from './WarehouseArticleForm'
import {
  buildArticlePayload,
  buildUomMap,
  createArticleFormState,
  formatDate,
  formatDateTime,
  formatOptionalQuantity,
  formatQuantity,
  getReorderStatusColor,
  getReorderStatusLabel,
  getTransactionTypeLabel,
  mapArticleApiErrorToFormErrors,
  translateArticleApiMessage,
  validateArticleForm,
  type WarehouseArticleFormErrors,
  type WarehouseArticleFormState,
} from './warehouseUtils'

const TRANSACTIONS_PER_PAGE = 10
const WAREHOUSE_CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={4}>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Text fw={500}>{value}</Text>
    </Stack>
  )
}

export default function ArticleDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN'

  const articleId = Number(id)

  const [article, setArticle] = useState<WarehouseArticleDetail | null>(null)
  const [categories, setCategories] = useState<ArticleCategoryLookupItem[]>([])
  const [uoms, setUoms] = useState<ArticleUomLookupItem[]>([])
  const [supplierOptions, setSupplierOptions] = useState<SupplierLookupItem[]>([])
  const [supplierOptionsLoading, setSupplierOptionsLoading] = useState(false)
  const [supplierOptionsError, setSupplierOptionsError] = useState<string | null>(null)
  const [transactions, setTransactions] = useState<ArticleTransactionItem[]>([])
  const [transactionsTotal, setTransactionsTotal] = useState(0)
  const [transactionPage, setTransactionPage] = useState(1)
  const [pageLoading, setPageLoading] = useState(true)
  const [transactionsLoading, setTransactionsLoading] = useState(false)
  const [fatalError, setFatalError] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState<WarehouseArticleFormState>(createArticleFormState())
  const [editErrors, setEditErrors] = useState<WarehouseArticleFormErrors>({})
  const [editSubmitting, setEditSubmitting] = useState(false)
  const [deactivateSubmitting, setDeactivateSubmitting] = useState(false)
  const [barcodeSubmitting, setBarcodeSubmitting] = useState(false)
  const [batchBarcodeSubmittingId, setBatchBarcodeSubmittingId] = useState<number | null>(null)
  // Direct-print loading states (ADMIN only)
  const [directPrintSubmitting, setDirectPrintSubmitting] = useState(false)
  const [batchDirectPrintSubmittingId, setBatchDirectPrintSubmittingId] = useState<number | null>(null)
  // Local barcode settings — ADMIN-only, loaded once on mount
  const [barcodeSettings, setBarcodeSettings] = useState<SettingsBarcode | null>(null)

  const [aliasInput, setAliasInput] = useState('')
  const [aliasSubmitting, setAliasSubmitting] = useState(false)
  const [aliasError, setAliasError] = useState<string | null>(null)
  const [aliasDeletingId, setAliasDeletingId] = useState<number | null>(null)

  // Statistics section state — lazy-loaded on first expand
  const [statsOpen, setStatsOpen] = useState(false)
  const [statsPeriod, setStatsPeriod] = useState<StatPeriod>(90)
  const [stats, setStats] = useState<ArticleStatsResponse | null>(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsError, setStatsError] = useState<string | null>(null)
  const statsLoadedForRef = useRef<{ articleId: number; period: StatPeriod } | null>(null)

  const initialLoadDoneRef = useRef(false)
  const supplierOptionsLoadedRef = useRef(false)
  const uomMap = useMemo(() => buildUomMap(uoms), [uoms])

  const applyArticleState = useCallback((nextArticle: WarehouseArticleDetail) => {
    setArticle(nextArticle)
    setEditForm(createArticleFormState(nextArticle))
    setEditErrors({})
    setEditMode(false)
  }, [])

  const loadInitialData = useCallback(
    async (page = 1) => {
      if (!Number.isInteger(articleId) || articleId <= 0) {
        setNotFound(true)
        setPageError('Artikl nije pronađen.')
        setPageLoading(false)
        return
      }

      setPageLoading(true)
      setPageError(null)
      setFatalError(false)
      setNotFound(false)
      initialLoadDoneRef.current = false

      try {
        const [detailResponse, categoriesResponse, uomsResponse, transactionsResponse] =
          await runWithRetry(() =>
            Promise.all([
              articlesApi.getDetail(articleId),
              articlesApi.lookupCategories(),
              articlesApi.lookupUoms(),
              articlesApi.listTransactions(articleId, page, TRANSACTIONS_PER_PAGE),
            ])
          )

        setCategories(categoriesResponse)
        setUoms(uomsResponse)
        applyArticleState(detailResponse)
        setTransactions(transactionsResponse.items)
        setTransactionsTotal(transactionsResponse.total)
        setTransactionPage(page)
        initialLoadDoneRef.current = true

        // Load barcode settings for ADMIN (fire-and-forget; does not block article render)
        if (isAdmin) {
          settingsApi.getBarcode().then(
            (settings) => { setBarcodeSettings(settings) },
            () => { /* silently ignore — printer config non-critical */ }
          )
        }
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        const apiError = getApiErrorBody(error)
        if (apiError?.error === 'ARTICLE_NOT_FOUND') {
          setNotFound(true)
          setPageError('Artikl nije pronađen.')
        } else {
          setPageError(
            translateArticleApiMessage(apiError, 'Detalj artikla nije dostupan.')
          )
        }
      } finally {
        setPageLoading(false)
      }
    },
    [applyArticleState, articleId, isAdmin]
  )

  const loadTransactions = useCallback(
    async (page: number) => {
      if (!initialLoadDoneRef.current) {
        return
      }

      setTransactionsLoading(true)
      setPageError(null)
      setFatalError(false)

      try {
        const response = await runWithRetry(() =>
          articlesApi.listTransactions(articleId, page, TRANSACTIONS_PER_PAGE)
        )
        setTransactions(response.items)
        setTransactionsTotal(response.total)
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        const apiError = getApiErrorBody(error)
        if (apiError?.error === 'ARTICLE_NOT_FOUND') {
          setNotFound(true)
          setPageError('Artikl nije pronađen.')
        } else {
          setPageError(
            translateArticleApiMessage(apiError, 'Povijest transakcija nije dostupna.')
          )
        }
      } finally {
        setTransactionsLoading(false)
      }
    },
    [articleId]
  )

  useEffect(() => {
    setTransactionPage(1)
    void loadInitialData(1)
  }, [articleId, loadInitialData])

  useEffect(() => {
    if (!initialLoadDoneRef.current) {
      return
    }

    void loadTransactions(transactionPage)
  }, [loadTransactions, transactionPage])

  const handleRetry = useCallback(() => {
    void loadInitialData(transactionPage)
  }, [loadInitialData, transactionPage])

  const loadSupplierOptions = useCallback(async () => {
    if (!isAdmin) {
      return
    }

    setSupplierOptionsLoading(true)
    setSupplierOptionsError(null)

    try {
      const response = await runWithRetry(() => articlesApi.lookupSuppliersPreload())
      setSupplierOptions(response.items)
      supplierOptionsLoadedRef.current = true
    } catch (error) {
      const message = isNetworkOrServerError(error)
        ? 'Popis dobavljača nije dostupan.'
        : translateArticleApiMessage(getApiErrorBody(error), 'Popis dobavljača nije dostupan.')

      setSupplierOptionsError(message)
      showErrorToast(message)
    } finally {
      setSupplierOptionsLoading(false)
    }
  }, [isAdmin])

  const ensureSupplierOptionsLoaded = useCallback(async () => {
    if (!isAdmin || supplierOptionsLoadedRef.current || supplierOptionsLoading) {
      return
    }

    await loadSupplierOptions()
  }, [isAdmin, loadSupplierOptions, supplierOptionsLoading])

  const handleEditFieldChange = useCallback(
    <K extends keyof WarehouseArticleFormState>(field: K, value: WarehouseArticleFormState[K]) => {
      setEditForm((current) => ({
        ...current,
        [field]: value,
      }))
      setEditErrors({})
    },
    []
  )

  const handleStartEdit = useCallback(() => {
    if (!article) {
      return
    }

    setEditForm(createArticleFormState(article))
    setEditErrors({})
    setEditMode(true)
    void ensureSupplierOptionsLoaded()
  }, [article, ensureSupplierOptionsLoaded])

  const handleCancelEdit = useCallback(() => {
    if (!article) {
      return
    }

    setEditForm(createArticleFormState(article))
    setEditErrors({})
    setEditMode(false)
  }, [article])

  const handleSave = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()

      if (!article) {
        return
      }

      const validationErrors = validateArticleForm(editForm)
      if (Object.keys(validationErrors).length > 0) {
        setEditErrors(validationErrors)
        return
      }

      setEditSubmitting(true)

      try {
        const updatedArticle = await runWithRetry(() =>
          articlesApi.update(article.id, buildArticlePayload(editForm))
        )
        applyArticleState(updatedArticle)
        showSuccessToast('Artikl je ažuriran.')
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        const apiError = getApiErrorBody(error)
        const fieldErrors = mapArticleApiErrorToFormErrors(apiError)

        if (Object.keys(fieldErrors).length > 0) {
          setEditErrors(fieldErrors)
        } else {
          showErrorToast(
            translateArticleApiMessage(apiError, 'Ažuriranje artikla nije uspjelo.')
          )
        }
      } finally {
        setEditSubmitting(false)
      }
    },
    [applyArticleState, article, editForm]
  )

  const handleDeactivate = useCallback(async () => {
    if (!article) {
      return
    }

    const confirmationLines = [
      'Deaktivirati ovaj artikl? Više se neće prikazivati na popisu aktivnih artikala.',
    ]
    if (article.has_pending_drafts) {
      confirmationLines.push(
        'Ovaj artikl ima otvorene draftove. Deaktivacija neće utjecati na postojeće draftove.'
      )
    }
    if (article.stock_total + article.surplus_total > 0) {
      confirmationLines.push('Ovaj artikl još uvijek ima zalihu na stanju.')
    }

    if (!window.confirm(confirmationLines.join('\n\n'))) {
      return
    }

    setDeactivateSubmitting(true)

    try {
      const updatedArticle = await runWithRetry(() => articlesApi.deactivate(article.id))
      applyArticleState(updatedArticle)
      showSuccessToast('Artikl je deaktiviran.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      showErrorToast(
        translateArticleApiMessage(
          getApiErrorBody(error),
          'Deaktivacija artikla nije uspjela.'
        )
      )
    } finally {
      setDeactivateSubmitting(false)
    }
  }, [applyArticleState, article])

  const handleBarcodePrint = useCallback(async () => {
    if (!article) {
      return
    }

    setBarcodeSubmitting(true)

    try {
      await runWithRetry(() => articlesApi.downloadBarcode(article.id, article.article_no))
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      const apiError = await getApiErrorBodyAsync(error)
      showErrorToast(
        translateArticleApiMessage(apiError, 'Ispis barkoda nije uspio.')
      )
    } finally {
      setBarcodeSubmitting(false)
    }
  }, [article])

  const handleDirectPrint = useCallback(async () => {
    if (!article) {
      return
    }

    setDirectPrintSubmitting(true)

    try {
      // Printing is a side effect on real hardware, so this must stay single-shot.
      await articlesApi.printArticleLabel(article.id)
      showSuccessToast('Naljepnica poslana na printer.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      const apiError = await getApiErrorBodyAsync(error)
      const knownErrors: Record<string, string> = {
        PRINTER_NOT_CONFIGURED: apiError?.message ?? 'Printer nije konfiguriran.',
        PRINTER_UNREACHABLE: apiError?.message ?? 'Printer nije dostupan.',
        PRINTER_MODEL_UNKNOWN: apiError?.message ?? 'Nepoznat model printera.',
      }
      const errorCode = apiError?.error ?? ''
      showErrorToast(knownErrors[errorCode] ?? apiError?.message ?? 'Ispis naljepnice nije uspio.')
    } finally {
      setDirectPrintSubmitting(false)
    }
  }, [article])

  const handleBatchBarcodePrint = useCallback(
    async (batchId: number, batchCode: string) => {
      if (!article) {
        return
      }

      setBatchBarcodeSubmittingId(batchId)

      try {
        await runWithRetry(() =>
          articlesApi.downloadBatchBarcode(batchId, {
            articleNo: article.article_no,
            batchCode,
          })
        )
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        const apiError = await getApiErrorBodyAsync(error)
        showErrorToast(
          translateArticleApiMessage(apiError, 'Ispis barkoda šarže nije uspio.')
        )
      } finally {
        setBatchBarcodeSubmittingId(null)
      }
    },
    [article]
  )

  const handleBatchDirectPrint = useCallback(
    async (batchId: number) => {
      if (!article) {
        return
      }

      setBatchDirectPrintSubmittingId(batchId)

      try {
        // Printing is a side effect on real hardware, so this must stay single-shot.
        await articlesApi.printBatchLabel(batchId)
        showSuccessToast('Naljepnica poslana na printer.')
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        const apiError = await getApiErrorBodyAsync(error)
        const knownErrors: Record<string, string> = {
          PRINTER_NOT_CONFIGURED: apiError?.message ?? 'Printer nije konfiguriran.',
          PRINTER_UNREACHABLE: apiError?.message ?? 'Printer nije dostupan.',
          PRINTER_MODEL_UNKNOWN: apiError?.message ?? 'Nepoznat model printera.',
        }
        const errorCode = apiError?.error ?? ''
        showErrorToast(knownErrors[errorCode] ?? apiError?.message ?? 'Ispis naljepnice šarže nije uspio.')
      } finally {
        setBatchDirectPrintSubmittingId(null)
      }
    },
    [article]
  )

  const handleAddAlias = useCallback(async () => {
    if (!article || !aliasInput.trim()) {
      return
    }

    setAliasSubmitting(true)
    setAliasError(null)

    try {
      const created = await runWithRetry(() =>
        articlesApi.createAlias(article.id, aliasInput.trim())
      )
      setArticle((prev): WarehouseArticleDetail | null =>
        prev ? { ...prev, aliases: [...prev.aliases, created] } : prev
      )
      setAliasInput('')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }
      const apiError = getApiErrorBody(error)
      if (apiError?.error === 'ALIAS_ALREADY_EXISTS') {
        setAliasError('Ovaj alternativni naziv već postoji.')
      } else {
        showErrorToast(translateArticleApiMessage(apiError, 'Dodavanje alternativnog naziva nije uspjelo.'))
      }
    } finally {
      setAliasSubmitting(false)
    }
  }, [article, aliasInput])

  const handleDeleteAlias = useCallback(
    async (aliasId: number) => {
      if (!article) {
        return
      }

      setAliasDeletingId(aliasId)

      try {
        await runWithRetry(() => articlesApi.deleteAlias(article.id, aliasId))
        setArticle((prev): WarehouseArticleDetail | null =>
          prev
            ? { ...prev, aliases: prev.aliases.filter((a: ArticleAliasItem) => a.id !== aliasId) }
            : prev
        )
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }
        showErrorToast(
          translateArticleApiMessage(
            getApiErrorBody(error),
            'Brisanje alternativnog naziva nije uspjelo.'
          )
        )
      } finally {
        setAliasDeletingId(null)
      }
    },
    [article]
  )

  const transactionTotalPages = Math.max(1, Math.ceil(transactionsTotal / TRANSACTIONS_PER_PAGE))

  const loadStats = useCallback(
    async (aid: number, period: StatPeriod) => {
      setStatsLoading(true)
      setStatsError(null)

      try {
        const result = await runWithRetry(() => articlesApi.getStats(aid, period))
        setStats(result)
        statsLoadedForRef.current = { articleId: aid, period }
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setStatsError('Greška pri povezivanju. Pokušajte ponovno.')
          return
        }
        setStatsError(
          translateArticleApiMessage(
            getApiErrorBody(error),
            'Statistika nije dostupna.'
          )
        )
      } finally {
        setStatsLoading(false)
      }
    },
    []
  )

  const handleToggleStats = useCallback(() => {
    const nextOpen = !statsOpen
    setStatsOpen(nextOpen)

    if (nextOpen) {
      const alreadyLoaded =
        statsLoadedForRef.current?.articleId === articleId &&
        statsLoadedForRef.current?.period === statsPeriod

      if (!alreadyLoaded) {
        void loadStats(articleId, statsPeriod)
      }
    }
  }, [articleId, loadStats, statsOpen, statsPeriod])

  const handleStatsPeriodChange = useCallback(
    (value: string) => {
      const next = Number(value) as StatPeriod
      setStatsPeriod(next)
      void loadStats(articleId, next)
    },
    [articleId, loadStats]
  )

  if (fatalError) {
    return (
      <FullPageState
        title="Greška pri povezivanju"
        message={WAREHOUSE_CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => window.location.reload()}
      />
    )
  }

  if (pageLoading) {
    return <FullPageState title="Učitavanje…" loading />
  }

  if (notFound) {
    return (
      <FullPageState
        title="Artikl nije pronađen."
        message={pageError ?? 'Traženi artikl nije dostupan.'}
        actionLabel="Natrag na skladište"
        onAction={() => navigate('/warehouse')}
      />
    )
  }

  if (pageError || !article) {
    return (
      <FullPageState
        title="Detalj artikla nije dostupan."
        message={pageError ?? 'Detalj artikla nije dostupan.'}
        actionLabel="Pokušaj ponovno"
        onAction={handleRetry}
      />
    )
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Button variant="subtle" px={0} onClick={() => navigate('/warehouse')}>
            Natrag na skladište
          </Button>
          <Group gap="sm" mt={6}>
            <Title order={2}>{article.article_no}</Title>
            <Badge color={article.is_active ? 'green' : 'gray'} variant="light">
              {article.is_active ? 'Aktivan' : 'Deaktiviran'}
            </Badge>
            <Badge
              variant="dot"
              styles={{
                root: {
                  color: getReorderStatusColor(article.reorder_status),
                },
              }}
            >
              {getReorderStatusLabel(article.reorder_status)}
            </Badge>
          </Group>
          <Text c="dimmed" mt={4}>
            {article.description}
          </Text>
        </div>

        {isAdmin ? (
          <Stack gap={4} align="flex-end">
            <Group>
              <Button variant="default" onClick={() => void handleBarcodePrint()} loading={barcodeSubmitting}>
                Ispis barkoda (PDF)
              </Button>
              <Button
                variant="filled"
                color="teal"
                onClick={() => void handleDirectPrint()}
                loading={directPrintSubmitting}
                disabled={!barcodeSettings?.label_printer_ip}
                title={!barcodeSettings?.label_printer_ip ? 'Printer nije konfiguriran' : undefined}
              >
                Pošalji na printer
              </Button>
              {!editMode ? (
                <>
                  <Button variant="default" onClick={handleStartEdit}>
                    Uredi
                  </Button>
                  <Button
                    color="red"
                    variant="light"
                    onClick={() => void handleDeactivate()}
                    loading={deactivateSubmitting}
                  >
                    Deaktiviraj
                  </Button>
                </>
              ) : null}
            </Group>
            {!barcodeSettings?.label_printer_ip ? (
              <Text size="xs" c="dimmed">
                Printer nije konfiguriran — postavite IP adresu u postavkama barkoda.
              </Text>
            ) : null}
          </Stack>
        ) : null}
      </Group>

      <Paper withBorder radius="lg" p="lg">
        <Stack gap="lg">
          <Group justify="space-between" align="center">
            <Title order={3}>Osnovni podaci</Title>
            {isAdmin && !editMode ? (
              <Text size="sm" c="dimmed">
                Uređivanje je dostupno samo administratoru.
              </Text>
            ) : null}
          </Group>

          {editMode ? (
            <form onSubmit={handleSave}>
              <Stack gap="lg">
                <WarehouseArticleForm
                  form={editForm}
                  errors={editErrors}
                  categories={categories}
                  uoms={uoms}
                  supplierOptions={supplierOptions}
                  supplierOptionsLoading={supplierOptionsLoading}
                  supplierOptionsError={supplierOptionsError}
                  disabled={editSubmitting}
                  onRetrySuppliers={() => void loadSupplierOptions()}
                  onChange={handleEditFieldChange}
                />

                <Group justify="flex-end">
                  <Button variant="default" onClick={handleCancelEdit} disabled={editSubmitting}>
                    Odustani
                  </Button>
                  <Button type="submit" loading={editSubmitting}>
                    Spremi
                  </Button>
                </Group>
              </Stack>
            </form>
          ) : (
            <SimpleGrid cols={{ base: 1, md: 2, lg: 3 }} spacing="lg">
              <DetailField label="Broj artikla" value={article.article_no} />
              <DetailField label="Opis" value={article.description} />
              <DetailField label="Kategorija" value={article.category_label_hr ?? '—'} />
              <DetailField label="Osnovna mjerna jedinica" value={article.base_uom ?? '—'} />
              <DetailField
                label="Veličina pakiranja"
                value={
                  article.pack_size === null
                    ? '—'
                    : formatQuantity(article.pack_size, article.pack_uom ?? article.base_uom, uomMap)
                }
              />
              <DetailField label="Jedinica pakiranja" value={article.pack_uom ?? '—'} />
              <DetailField label="Barkod" value={article.barcode ?? '—'} />
              <DetailField label="Proizvođač" value={article.manufacturer ?? '—'} />
              <DetailField label="Šifra proizvođača" value={article.manufacturer_art_number ?? '—'} />
              <DetailField label="Artikl sa šaržom" value={article.has_batch ? 'Da' : 'Ne'} />
              <DetailField
                label="Prag naručivanja"
                value={
                  article.reorder_threshold === null
                    ? '—'
                    : formatQuantity(article.reorder_threshold, article.base_uom, uomMap)
                }
              />
              <DetailField label="Kreirano" value={formatDateTime(article.created_at)} />
              <DetailField label="Zadnja promjena" value={formatDateTime(article.updated_at)} />
            </SimpleGrid>
          )}
        </Stack>
      </Paper>

      <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
        <Paper withBorder radius="lg" p="lg">
          <Stack gap={6}>
            <Text size="sm" c="dimmed">
              Zaliha
            </Text>
            <Text fw={700} size="xl">
              {formatQuantity(article.stock_total, article.base_uom, uomMap)}
            </Text>
          </Stack>
        </Paper>

        <Paper withBorder radius="lg" p="lg">
          <Stack gap={6}>
            <Text size="sm" c="dimmed">
              Višak
            </Text>
            <Text fw={700} size="xl">
              {formatOptionalQuantity(article.surplus_total, article.base_uom, uomMap)}
            </Text>
          </Stack>
        </Paper>

        <Paper withBorder radius="lg" p="lg">
          <Stack gap={6}>
            <Text size="sm" c="dimmed">
              Prag naručivanja
            </Text>
            <Text fw={700} size="xl">
              {article.reorder_threshold === null
                ? '—'
                : formatQuantity(article.reorder_threshold, article.base_uom, uomMap)}
            </Text>
          </Stack>
        </Paper>
      </SimpleGrid>

      {article.has_batch ? (
        <Paper withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Title order={3}>Šarže (FEFO)</Title>

            {!article.batches || article.batches.length === 0 ? (
              <Text c="dimmed">Nema aktivnih šarži.</Text>
            ) : (
              <ScrollArea>
                <Table withTableBorder verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Šifra šarže</Table.Th>
                      <Table.Th>Rok trajanja</Table.Th>
                      <Table.Th>Količina zalihe</Table.Th>
                      <Table.Th>Količina viška</Table.Th>
                      {isAdmin ? <Table.Th>Akcije</Table.Th> : null}
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {article.batches.map((batch) => (
                      <Table.Tr key={batch.id}>
                        <Table.Td>{batch.batch_code}</Table.Td>
                        <Table.Td>{formatDate(batch.expiry_date)}</Table.Td>
                        <Table.Td>{formatQuantity(batch.stock_total, article.base_uom, uomMap)}</Table.Td>
                        <Table.Td>
                          {formatOptionalQuantity(batch.surplus_total, article.base_uom, uomMap)}
                        </Table.Td>
                        {isAdmin ? (
                          <Table.Td>
                            <Group gap="xs">
                              <Button
                                size="xs"
                                variant="default"
                                onClick={() => void handleBatchBarcodePrint(batch.id, batch.batch_code)}
                                loading={batchBarcodeSubmittingId === batch.id}
                              >
                                PDF
                              </Button>
                              <Button
                                size="xs"
                                variant="filled"
                                color="teal"
                                onClick={() => void handleBatchDirectPrint(batch.id)}
                                loading={batchDirectPrintSubmittingId === batch.id}
                                disabled={!barcodeSettings?.label_printer_ip}
                                title={!barcodeSettings?.label_printer_ip ? 'Printer nije konfiguriran' : undefined}
                              >
                                Printer
                              </Button>
                            </Group>
                          </Table.Td>
                        ) : null}
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            )}
          </Stack>
        </Paper>
      ) : null}

      <Paper withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Title order={3}>Dobavljači</Title>

          {article.suppliers.length === 0 ? (
            <Text c="dimmed">Nema povezanih dobavljača.</Text>
          ) : (
            <ScrollArea>
              <Table withTableBorder verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Naziv dobavljača</Table.Th>
                    <Table.Th>Šifra artikla kod dobavljača</Table.Th>
                    <Table.Th>Preferirani</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {article.suppliers.map((supplier) => (
                    <Table.Tr key={supplier.id}>
                      <Table.Td>{supplier.supplier_name ?? '—'}</Table.Td>
                      <Table.Td>{supplier.supplier_article_code ?? '—'}</Table.Td>
                      <Table.Td>
                        {supplier.is_preferred ? (
                          <Badge color="green" variant="light">
                            Preferirani
                          </Badge>
                        ) : (
                          '—'
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          )}
        </Stack>
      </Paper>

      <Paper withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Title order={3}>Alternativni nazivi</Title>

          {article.aliases.length === 0 ? (
            <Text c="dimmed">Nema alternativnih naziva.</Text>
          ) : (
            <Group gap="xs" wrap="wrap">
              {article.aliases.map((alias) => (
                <Badge
                  key={alias.id}
                  variant="light"
                  size="lg"
                  rightSection={
                    isAdmin ? (
                      <ActionIcon
                        size="xs"
                        variant="transparent"
                        color="gray"
                        aria-label={`Ukloni ${alias.alias}`}
                        loading={aliasDeletingId === alias.id}
                        onClick={() => void handleDeleteAlias(alias.id)}
                      >
                        <IconX size={10} />
                      </ActionIcon>
                    ) : null
                  }
                >
                  {alias.alias}
                </Badge>
              ))}
            </Group>
          )}

          {isAdmin ? (
            <Stack gap={4}>
              <Group align="flex-start" gap="sm">
                <TextInput
                  placeholder="Novi alternativni naziv"
                  value={aliasInput}
                  onChange={(e) => {
                    setAliasInput(e.currentTarget.value)
                    setAliasError(null)
                  }}
                  error={aliasError}
                  disabled={aliasSubmitting}
                  style={{ flex: 1 }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      void handleAddAlias()
                    }
                  }}
                />
                <Button
                  onClick={() => void handleAddAlias()}
                  loading={aliasSubmitting}
                  disabled={!aliasInput.trim()}
                  mt={aliasError ? 0 : undefined}
                >
                  Dodaj
                </Button>
              </Group>
            </Stack>
          ) : null}
        </Stack>
      </Paper>

      {/* ── Statistics Section ─────────────────────────────────── */}
      <Paper withBorder radius="lg" p="lg">
        <UnstyledButton
          id="article-stats-toggle"
          onClick={handleToggleStats}
          style={{ width: '100%' }}
        >
          <Group justify="space-between" align="center">
            <Title order={3}>Statistika</Title>
            {statsOpen ? <IconChevronUp size={18} /> : <IconChevronDown size={18} />}
          </Group>
        </UnstyledButton>

        <Collapse in={statsOpen}>
          <Stack gap="md" mt="md">
            <Group>
              <SegmentedControl
                id="article-stats-period"
                value={String(statsPeriod)}
                onChange={handleStatsPeriodChange}
                disabled={statsLoading}
                data={[
                  { label: '30 dana', value: '30' },
                  { label: '90 dana', value: '90' },
                  { label: '180 dana', value: '180' },
                ]}
              />
              {statsLoading ? <Loader size="xs" /> : null}
            </Group>

            {statsError ? (
              <Text c="red">{statsError}</Text>
            ) : statsLoading && !stats ? (
              <Text c="dimmed">Učitavanje statistike…</Text>
            ) : stats &&
              stats.outbound_by_week.length === 0 &&
              stats.inbound_by_week.length === 0 &&
              stats.price_history.length === 0 ? (
              <Text c="dimmed">No transaction history available yet.</Text>
            ) : stats ? (
              <Stack gap="xl">
                <Stack gap="xs">
                  <Text fw={600}>Tjedni izlaz</Text>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={stats.outbound_by_week} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="week_start"
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v: string) => v.slice(5)}
                      />
                      <YAxis tick={{ fontSize: 11 }} />
                      <RechartsTooltip
                        formatter={(value) => [String(value), 'Izlaz']}
                        labelFormatter={(label) => `Tjedan: ${String(label)}`}
                      />
                      <Bar dataKey="quantity" name="Izlaz" fill="#f03e3e" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Stack>

                <Stack gap="xs">
                  <Text fw={600}>Tjedni ulaz</Text>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={stats.inbound_by_week} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="week_start"
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v: string) => v.slice(5)}
                      />
                      <YAxis tick={{ fontSize: 11 }} />
                      <RechartsTooltip
                        formatter={(value) => [String(value), 'Ulaz']}
                        labelFormatter={(label) => `Tjedan: ${String(label)}`}
                      />
                      <Bar dataKey="quantity" name="Ulaz" fill="#1c7ed6" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Stack>

                {stats.price_history.length > 0 ? (
                  <Stack gap="xs">
                    <Text fw={600}>Povijest cijene (primke)</Text>
                    <ResponsiveContainer width="100%" height={220}>
                      <LineChart data={stats.price_history} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 11 }}
                          tickFormatter={(v: string) => v.slice(0, 10)}
                        />
                        <YAxis tick={{ fontSize: 11 }} />
                        <RechartsTooltip
                          formatter={(value) => [String(value), 'Cijena/jed.']}
                          labelFormatter={(label) => String(label).slice(0, 10)}
                        />
                        <Line
                          type="monotone"
                          dataKey="unit_price"
                          name="Cijena/jed."
                          stroke="#37b24d"
                          strokeWidth={2}
                          dot={{ r: 4 }}
                          activeDot={{ r: 6 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </Stack>
                ) : null}
              </Stack>
            ) : null}
          </Stack>
        </Collapse>
      </Paper>

      <Paper withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Group justify="space-between">
            <Title order={3}>Povijest transakcija</Title>
            {transactionsLoading ? (
              <Group gap="xs">
                <Loader size="xs" />
                <Text size="sm" c="dimmed">
                  Učitavanje transakcija…
                </Text>
              </Group>
            ) : null}
          </Group>

          {transactions.length === 0 ? (
            <Text c="dimmed">Nema pronađenih transakcija.</Text>
          ) : (
            <ScrollArea>
              <Table withTableBorder verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Datum i vrijeme</Table.Th>
                    <Table.Th>Tip</Table.Th>
                    <Table.Th>Količina</Table.Th>
                    <Table.Th>Šarža</Table.Th>
                    <Table.Th>Referenca</Table.Th>
                    <Table.Th>Korisnik</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {transactions.map((transaction) => (
                    <Table.Tr key={transaction.id}>
                      <Table.Td>{formatDateTime(transaction.occurred_at)}</Table.Td>
                      <Table.Td>{getTransactionTypeLabel(transaction.type)}</Table.Td>
                      <Table.Td>{formatQuantity(transaction.quantity, transaction.uom, uomMap)}</Table.Td>
                      <Table.Td>{transaction.batch_code ?? '—'}</Table.Td>
                      <Table.Td>{transaction.reference ?? '—'}</Table.Td>
                      <Table.Td>{transaction.user ?? '—'}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          )}

          {transactions.length > 0 && transactionTotalPages > 1 ? (
            <Group justify="space-between" align="center">
              <Text size="sm" c="dimmed">
                Ukupno transakcija: {transactionsTotal}
              </Text>
              <Pagination value={transactionPage} onChange={setTransactionPage} total={transactionTotalPages} />
            </Group>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  )
}
