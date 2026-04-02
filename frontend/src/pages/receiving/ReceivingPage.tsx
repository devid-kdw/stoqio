import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Box,
  Button,
  Checkbox,
  Divider,
  Group,
  Loader,
  NumberInput,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import axios from 'axios'

import { articlesApi, type ArticleLookupResult } from '../../api/articles'
import { ordersApi, type OrdersListItem, type ReceivingOrderDetail, type ReceivingOrderLine, type ReceivingOrderSummary } from '../../api/orders'
import { receivingApi, type CreateReceiptPayload, type ReceivingHistoryItem } from '../../api/receiving'
import { getActiveLocale } from '../../utils/locale'
import FullPageState from '../../components/shared/FullPageState'
import { CONNECTION_ERROR_MESSAGE, getApiErrorBody, isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast, showSuccessToast, showWarningToast } from '../../utils/toasts'
import { INTEGER_UOMS } from '../../utils/uom'

const BATCH_CODE_PATTERN = /^\d{4,5}$|^\d{9,12}$/

type PageTab = 'new' | 'history'
type ReceiptMode = 'linked' | 'adhoc'

interface LinkedHeaderState {
  deliveryNoteNumber: string
  note: string
}

interface LinkedHeaderErrors {
  deliveryNoteNumber?: string
  note?: string
}

interface LinkedLineState {
  quantity: number | string
  batchCode: string
  expiryDate: string
  skip: boolean
}

interface LinkedLineErrors {
  quantity?: string
  batchCode?: string
  expiryDate?: string
  line?: string
}

interface AdhocFormState {
  quantity: number | string
  batchCode: string
  expiryDate: string
  deliveryNoteNumber: string
  note: string
}

interface AdhocFormErrors {
  article?: string
  quantity?: string
  batchCode?: string
  expiryDate?: string
  deliveryNoteNumber?: string
  note?: string
}

const EMPTY_LINKED_HEADER: LinkedHeaderState = {
  deliveryNoteNumber: '',
  note: '',
}

const EMPTY_ADHOC_FORM: AdhocFormState = {
  quantity: '',
  batchCode: '',
  expiryDate: '',
  deliveryNoteNumber: '',
  note: '',
}

function formatQuantity(quantity: number, uom: string): string {
  if (INTEGER_UOMS.includes(uom)) {
    return Math.round(quantity).toString()
  }

  return quantity.toFixed(2)
}

function getQuantityStep(uom?: string): number {
  return uom && INTEGER_UOMS.includes(uom) ? 1 : 0.01
}

function getQuantityScale(uom?: string): number {
  return uom && INTEGER_UOMS.includes(uom) ? 0 : 3
}

function formatDate(value: string | null): string {
  if (!value) return '—'

  try {
    return new Date(value).toLocaleDateString(getActiveLocale())
  } catch {
    return '—'
  }
}

function formatDateTime(value: string | null): string {
  if (!value) return '—'

  try {
    return new Date(value).toLocaleString(getActiveLocale(), {
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

function normalizeOptionalText(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function createLinkedLineState(lines: ReceivingOrderLine[]): Record<number, LinkedLineState> {
  return lines.reduce<Record<number, LinkedLineState>>((acc, line) => {
    acc[line.id] = {
      quantity: '',
      batchCode: '',
      expiryDate: '',
      skip: false,
    }
    return acc
  }, {})
}

function getOrderStatusLabel(status: string): string {
  if (status === 'OPEN') return 'Otvorena'
  if (status === 'CLOSED') return 'Zatvorena'
  return status
}

export default function ReceivingPage() {
  const [activeTab, setActiveTab] = useState<PageTab>('new')
  const [receiptMode, setReceiptMode] = useState<ReceiptMode>('linked')
  const [fatalError, setFatalError] = useState(false)

  const [historyItems, setHistoryItems] = useState<ReceivingHistoryItem[]>([])
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)

  const [openOrders, setOpenOrders] = useState<OrdersListItem[]>([])
  const [openOrdersLoading, setOpenOrdersLoading] = useState(false)
  const [openOrdersError, setOpenOrdersError] = useState<string | null>(null)

  const [orderQuery, setOrderQuery] = useState('')
  const [orderSearchError, setOrderSearchError] = useState<string | null>(null)
  const [linkedOrderSummary, setLinkedOrderSummary] = useState<ReceivingOrderSummary | null>(null)
  const [linkedOrderDetail, setLinkedOrderDetail] = useState<ReceivingOrderDetail | null>(null)
  const [linkedOrderWarning, setLinkedOrderWarning] = useState<string | null>(null)
  const [linkedOrderLoading, setLinkedOrderLoading] = useState(false)
  const [linkedHeader, setLinkedHeader] = useState<LinkedHeaderState>(EMPTY_LINKED_HEADER)
  const [linkedHeaderErrors, setLinkedHeaderErrors] = useState<LinkedHeaderErrors>({})
  const [linkedLineState, setLinkedLineState] = useState<Record<number, LinkedLineState>>({})
  const [linkedLineErrors, setLinkedLineErrors] = useState<Record<number, LinkedLineErrors>>({})
  const [linkedFormError, setLinkedFormError] = useState<string | null>(null)
  const [linkedSubmitting, setLinkedSubmitting] = useState(false)

  const [articleQuery, setArticleQuery] = useState('')
  const [resolvedArticle, setResolvedArticle] = useState<ArticleLookupResult | null>(null)
  const [articleLookupState, setArticleLookupState] = useState<'idle' | 'loading' | 'found' | 'not-found'>('idle')
  const [adhocForm, setAdhocForm] = useState<AdhocFormState>(EMPTY_ADHOC_FORM)
  const [adhocErrors, setAdhocErrors] = useState<AdhocFormErrors>({})
  const [adhocSubmitting, setAdhocSubmitting] = useState(false)

  const articleLookupDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleFatalError = useCallback(() => {
    setFatalError(true)
  }, [])


  const loadOpenOrders = useCallback(async () => {
    setOpenOrdersLoading(true)
    setOpenOrdersError(null)

    try {
      const response = await runWithRetry(() => ordersApi.listOpenOrdersPreload())
      setOpenOrders(response.items)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        handleFatalError()
        return
      }

      const message =
        getApiErrorBody(error)?.message ?? 'Učitavanje narudžbenica nije uspjelo.'
      setOpenOrdersError(message)
    } finally {
      setOpenOrdersLoading(false)
    }
  }, [handleFatalError])

  const clearLinkedReceiptForm = useCallback((lines: ReceivingOrderLine[]) => {
    setLinkedHeader(EMPTY_LINKED_HEADER)
    setLinkedHeaderErrors({})
    setLinkedLineState(createLinkedLineState(lines))
    setLinkedLineErrors({})
    setLinkedFormError(null)
  }, [])

  const setLinkedOrderData = useCallback(
    (summary: ReceivingOrderSummary, detail: ReceivingOrderDetail) => {
      setLinkedOrderSummary(summary)
      setLinkedOrderDetail(detail)
      setLinkedOrderWarning(
        summary.status !== 'OPEN' || detail.status !== 'OPEN'
          ? 'This order is already closed.'
          : null
      )
      setOrderSearchError(null)
      clearLinkedReceiptForm(detail.lines)
    },
    [clearLinkedReceiptForm]
  )

  const clearLinkedOrderData = useCallback(() => {
    setLinkedOrderSummary(null)
    setLinkedOrderDetail(null)
    setLinkedOrderWarning(null)
    clearLinkedReceiptForm([])
  }, [clearLinkedReceiptForm])

  const handleOrderSelect = useCallback(
    async (orderId: number, orderItem: OrdersListItem) => {
      setLinkedOrderLoading(true)
      setOrderSearchError(null)

      try {
        const detail = await runWithRetry(() => ordersApi.getReceivingDetail(orderId))
        const summary: ReceivingOrderSummary = {
          id: orderItem.id,
          order_number: orderItem.order_number,
          status: detail.status,
          supplier_id: orderItem.supplier_id,
          supplier_name: orderItem.supplier_name,
          open_line_count: detail.lines.length,
          created_at: orderItem.created_at,
        }
        setLinkedOrderData(summary, detail)
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          handleFatalError()
          return
        }

        const apiError = getApiErrorBody(error)
        setOrderSearchError(apiError?.message ?? 'Učitavanje narudžbenice nije uspjelo.')
        clearLinkedOrderData()
      } finally {
        setLinkedOrderLoading(false)
      }
    },
    [clearLinkedOrderData, handleFatalError, setLinkedOrderData]
  )

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true)

    try {
      const data = await runWithRetry(() => receivingApi.getHistory(1, 50))
      setHistoryItems(data.items)
      setHistoryLoaded(true)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        handleFatalError()
        return
      }

      const message =
        getApiErrorBody(error)?.message ?? 'Učitavanje povijesti zaprimanja nije uspjelo.'
      showErrorToast(message)
    } finally {
      setHistoryLoading(false)
    }
  }, [handleFatalError])

  useEffect(() => {
    if (activeTab === 'history' && !historyLoaded) {
      void loadHistory()
    }
  }, [activeTab, historyLoaded, loadHistory])

  useEffect(() => {
    void loadOpenOrders()
  }, [loadOpenOrders])

  useEffect(() => {
    return () => {
      if (articleLookupDebounceRef.current) {
        clearTimeout(articleLookupDebounceRef.current)
      }
    }
  }, [])

  const refreshHistoryAfterSuccess = useCallback(async () => {
    await loadHistory()
  }, [loadHistory])

  const refreshCurrentOrder = useCallback(async () => {
    if (!linkedOrderSummary) {
      return
    }

    setLinkedOrderLoading(true)

    try {
      const detail = await runWithRetry(() => ordersApi.getReceivingDetail(linkedOrderSummary.id))
      const nextSummary: ReceivingOrderSummary = {
        ...linkedOrderSummary,
        status: detail.status,
        open_line_count: detail.lines.length,
      }
      setLinkedOrderData(nextSummary, detail)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        handleFatalError()
        return
      }

      const message =
        getApiErrorBody(error)?.message ?? 'Osvježavanje detalja narudžbenice nije uspjelo.'
      showErrorToast(message)
    } finally {
      setLinkedOrderLoading(false)
    }
  }, [handleFatalError, linkedOrderSummary, setLinkedOrderData])

  const resolveArticle = useCallback(
    async (query: string) => {
      const normalizedQuery = query.trim()
      if (!normalizedQuery) {
        setResolvedArticle(null)
        setArticleLookupState('idle')
        setAdhocErrors((prev) => ({
          ...prev,
          article: undefined,
          batchCode: undefined,
          expiryDate: undefined,
        }))
        return
      }

      setArticleLookupState('loading')
      setAdhocErrors((prev) => ({
        ...prev,
        article: undefined,
      }))

      try {
        const article = await runWithRetry(() => articlesApi.lookup(normalizedQuery))
        setResolvedArticle(article)
        setArticleLookupState('found')
        setAdhocErrors((prev) => ({
          ...prev,
          article: undefined,
        }))
        if (!article.has_batch) {
          setAdhocForm((prev) => ({
            ...prev,
            batchCode: '',
            expiryDate: '',
          }))
        }
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          handleFatalError()
          return
        }

        const apiError = getApiErrorBody(error)
        const notFound = axios.isAxiosError(error) && error.response?.status === 404
        if (apiError?.error === 'ARTICLE_NOT_FOUND' || notFound) {
          setResolvedArticle(null)
          setArticleLookupState('not-found')
          setAdhocErrors((prev) => ({
            ...prev,
            article: 'Article not found.',
            batchCode: undefined,
            expiryDate: undefined,
          }))
          return
        }

        setResolvedArticle(null)
        setArticleLookupState('idle')
        showErrorToast(apiError?.message ?? 'Dohvat artikla nije uspio.')
      }
    },
    [handleFatalError]
  )

  const handleArticleQueryChange = (value: string) => {
    setArticleQuery(value)

    if (resolvedArticle && value.trim().toUpperCase() !== resolvedArticle.article_no.toUpperCase()) {
      setResolvedArticle(null)
      setArticleLookupState('idle')
      setAdhocForm((prev) => ({
        ...prev,
        batchCode: '',
        expiryDate: '',
      }))
    }

    setAdhocErrors((prev) => ({
      ...prev,
      article: undefined,
      batchCode: undefined,
      expiryDate: undefined,
    }))

    if (articleLookupDebounceRef.current) {
      clearTimeout(articleLookupDebounceRef.current)
    }

    articleLookupDebounceRef.current = setTimeout(() => {
      void resolveArticle(value)
    }, 400)
  }

  const handleArticleBlur = () => {
    if (articleLookupDebounceRef.current) {
      clearTimeout(articleLookupDebounceRef.current)
    }

    if (articleLookupState !== 'found') {
      void resolveArticle(articleQuery)
    }
  }

  const validateLinkedReceipt = (): {
    headerErrors: LinkedHeaderErrors
    lineErrors: Record<number, LinkedLineErrors>
    formError: string | null
  } => {
    const headerErrors: LinkedHeaderErrors = {}
    const lineErrors: Record<number, LinkedLineErrors> = {}

    if (!linkedOrderDetail || linkedOrderDetail.lines.length === 0) {
      return {
        headerErrors,
        lineErrors,
        formError: 'Potrebno je zaprimiti barem jednu stavku.',
      }
    }

    const deliveryNoteNumber = linkedHeader.deliveryNoteNumber.trim()
    if (!deliveryNoteNumber) {
      headerErrors.deliveryNoteNumber = 'Broj dostavnice je obavezan.'
    } else if (deliveryNoteNumber.length > 100) {
      headerErrors.deliveryNoteNumber = 'Broj dostavnice smije imati najvise 100 znakova.'
    }

    if (linkedHeader.note.trim().length > 1000) {
      headerErrors.note = 'Napomena smije imati najvise 1000 znakova.'
    }

    let receivedLineCount = 0

    linkedOrderDetail.lines.forEach((line) => {
      const state = linkedLineState[line.id] ?? {
        quantity: '',
        batchCode: '',
        expiryDate: '',
        skip: false,
      }

      if (state.skip) {
        return
      }

      receivedLineCount += 1
      const errors: LinkedLineErrors = {}
      const quantity = typeof state.quantity === 'string' ? parseFloat(state.quantity) : state.quantity

      if (state.quantity === '' || state.quantity === null || state.quantity === undefined) {
        errors.quantity = 'Kolicina je obavezna.'
      } else if (Number.isNaN(quantity) || quantity <= 0) {
        errors.quantity = 'Kolicina mora biti veca od 0.'
      }

      if (line.has_batch) {
        const batchCode = state.batchCode.trim()
        if (!batchCode) {
          errors.batchCode = 'Batch code je obavezan.'
        } else if (!BATCH_CODE_PATTERN.test(batchCode)) {
          errors.batchCode = 'Batch code ima neispravan format.'
        }

        if (!state.expiryDate) {
          errors.expiryDate = 'Datum isteka je obavezan.'
        }
      }

      if (Object.keys(errors).length > 0) {
        lineErrors[line.id] = errors
      }
    })

    if (receivedLineCount === 0) {
      return {
        headerErrors,
        lineErrors,
        formError: 'Potrebno je zaprimiti barem jednu stavku.',
      }
    }

    return {
      headerErrors,
      lineErrors,
      formError: null,
    }
  }

  const validateAdhocReceipt = (): AdhocFormErrors => {
    const errors: AdhocFormErrors = {}

    if (!articleQuery.trim()) {
      errors.article = 'Broj artikla je obavezan.'
    } else if (articleLookupState === 'not-found') {
      errors.article = 'Article not found.'
    } else if (articleLookupState !== 'found' || !resolvedArticle) {
      errors.article = 'Artikl jos nije razrijesen. Pricekaj dovrsetak pretrage.'
    }

    const quantity = typeof adhocForm.quantity === 'string'
      ? parseFloat(adhocForm.quantity)
      : adhocForm.quantity

    if (adhocForm.quantity === '' || adhocForm.quantity === null || adhocForm.quantity === undefined) {
      errors.quantity = 'Kolicina je obavezna.'
    } else if (Number.isNaN(quantity) || quantity <= 0) {
      errors.quantity = 'Kolicina mora biti veca od 0.'
    }

    if (!adhocForm.deliveryNoteNumber.trim()) {
      errors.deliveryNoteNumber = 'Broj dostavnice je obavezan.'
    } else if (adhocForm.deliveryNoteNumber.trim().length > 100) {
      errors.deliveryNoteNumber = 'Broj dostavnice smije imati najvise 100 znakova.'
    }

    if (!adhocForm.note.trim()) {
      errors.note = 'A note is required for ad-hoc receipts.'
    } else if (adhocForm.note.trim().length > 1000) {
      errors.note = 'Napomena smije imati najvise 1000 znakova.'
    }

    if (resolvedArticle?.has_batch) {
      const batchCode = adhocForm.batchCode.trim()
      if (!batchCode) {
        errors.batchCode = 'Batch code je obavezan.'
      } else if (!BATCH_CODE_PATTERN.test(batchCode)) {
        errors.batchCode = 'Batch code ima neispravan format.'
      }

      if (!adhocForm.expiryDate) {
        errors.expiryDate = 'Datum isteka je obavezan.'
      }
    }

    return errors
  }

  const handleLinkedSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!linkedOrderDetail || !linkedOrderSummary) {
      setLinkedFormError('Potrebno je zaprimiti barem jednu stavku.')
      return
    }

    if (linkedOrderWarning) {
      showWarningToast(linkedOrderWarning)
      return
    }

    const validation = validateLinkedReceipt()
    setLinkedHeaderErrors(validation.headerErrors)
    setLinkedLineErrors(validation.lineErrors)
    setLinkedFormError(validation.formError)

    if (
      Object.keys(validation.headerErrors).length > 0 ||
      Object.keys(validation.lineErrors).length > 0 ||
      validation.formError
    ) {
      return
    }

    const payload: CreateReceiptPayload = {
      delivery_note_number: linkedHeader.deliveryNoteNumber.trim(),
      note: normalizeOptionalText(linkedHeader.note),
      lines: linkedOrderDetail.lines.map((line) => {
        const state = linkedLineState[line.id]

        if (state?.skip) {
          return {
            order_line_id: line.id,
            skip: true,
          }
        }

        const quantity = typeof state.quantity === 'string' ? parseFloat(state.quantity) : state.quantity
        return {
          order_line_id: line.id,
          article_id: line.article_id,
          quantity,
          uom: line.uom,
          batch_code: line.has_batch ? state.batchCode.trim() : null,
          expiry_date: line.has_batch ? state.expiryDate : null,
        }
      }),
    }

    setLinkedSubmitting(true)

    try {
      await runWithRetry(() => receivingApi.submit(payload))
      showSuccessToast('Receipt recorded.')
      await refreshCurrentOrder()
      await refreshHistoryAfterSuccess()
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        handleFatalError()
        return
      }

      const apiError = getApiErrorBody(error)
      const message = apiError?.message ?? 'Zaprimanje nije moglo biti evidentirano.'
      const lineIndex = apiError?.details?.line_index

      if (apiError?.error === 'BATCH_EXPIRY_MISMATCH' && typeof lineIndex === 'number') {
        const line = linkedOrderDetail.lines[lineIndex]
        if (line) {
          setLinkedLineErrors((prev) => ({
            ...prev,
            [line.id]: {
              ...prev[line.id],
              batchCode: message,
            },
          }))
        }
        showErrorToast(message)
        return
      }

      if (apiError?.error === 'ORDER_CLOSED') {
        setLinkedOrderWarning(message)
        showWarningToast(message)
        await refreshCurrentOrder()
        return
      }

      if (message === 'At least one line must be received.') {
        setLinkedFormError(message)
        return
      }

      if (typeof lineIndex === 'number') {
        const line = linkedOrderDetail.lines[lineIndex]
        if (line) {
          setLinkedLineErrors((prev) => ({
            ...prev,
            [line.id]: {
              ...prev[line.id],
              line: message,
            },
          }))
        }
      }

      showErrorToast(message)
    } finally {
      setLinkedSubmitting(false)
    }
  }

  const clearAdhocForm = useCallback(() => {
    setArticleQuery('')
    setResolvedArticle(null)
    setArticleLookupState('idle')
    setAdhocForm(EMPTY_ADHOC_FORM)
    setAdhocErrors({})
  }, [])

  const handleAdhocSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const errors = validateAdhocReceipt()
    setAdhocErrors(errors)

    if (Object.keys(errors).length > 0 || !resolvedArticle) {
      return
    }

    const quantity = typeof adhocForm.quantity === 'string'
      ? parseFloat(adhocForm.quantity)
      : adhocForm.quantity

    const payload: CreateReceiptPayload = {
      delivery_note_number: adhocForm.deliveryNoteNumber.trim(),
      note: adhocForm.note.trim(),
      lines: [
        {
          order_line_id: null,
          article_id: resolvedArticle.id,
          quantity,
          uom: resolvedArticle.base_uom,
          batch_code: resolvedArticle.has_batch ? adhocForm.batchCode.trim() : null,
          expiry_date: resolvedArticle.has_batch ? adhocForm.expiryDate : null,
        },
      ],
    }

    setAdhocSubmitting(true)

    try {
      await runWithRetry(() => receivingApi.submit(payload))
      showSuccessToast('Receipt recorded.')
      clearAdhocForm()
      await refreshHistoryAfterSuccess()
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        handleFatalError()
        return
      }

      const apiError = getApiErrorBody(error)
      const message = apiError?.message ?? 'Zaprimanje nije moglo biti evidentirano.'

      if (apiError?.error === 'BATCH_EXPIRY_MISMATCH') {
        setAdhocErrors((prev) => ({
          ...prev,
          batchCode: message,
        }))
        showErrorToast(message)
        return
      }

      if (apiError?.error === 'ARTICLE_NOT_FOUND') {
        setAdhocErrors((prev) => ({
          ...prev,
          article: message,
        }))
        return
      }

      if (message === 'A note is required for ad-hoc receipts.') {
        setAdhocErrors((prev) => ({
          ...prev,
          note: message,
        }))
        return
      }

      showErrorToast(message)
    } finally {
      setAdhocSubmitting(false)
    }
  }

  if (fatalError) {
    return (
      <FullPageState
        title="Greška povezivanja"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => window.location.reload()}
      />
    )
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end">
        <Stack gap={4}>
          <Title order={2}>Zaprimanje</Title>
          <Text c="dimmed" size="sm">
            Evidentiraj ulaz robe po narudžbenici ili kao ad-hoc zaprimanje.
          </Text>
        </Stack>
      </Group>

      <Tabs value={activeTab} onChange={(value) => setActiveTab((value as PageTab | null) ?? 'new')}>
        <Tabs.List>
          <Tabs.Tab value="new">Novo zaprimanje</Tabs.Tab>
          <Tabs.Tab value="history">Povijest</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="new" pt="md">
          <Paper withBorder radius="lg" p="xl">
            <Stack gap="lg">
              <Group justify="space-between" align="flex-start">
                <Stack gap={4}>
                  <Title order={4}>Novi unos</Title>
                  <Text c="dimmed" size="sm">
                    Odaberi zaprimanje povezano s narudžbenicom ili jednokratni ad-hoc unos.
                  </Text>
                </Stack>
                <SegmentedControl
                  value={receiptMode}
                  onChange={(value) => setReceiptMode(value as ReceiptMode)}
                  data={[
                    { label: 'Po narudžbenici', value: 'linked' },
                    { label: 'Ad-hoc zaprimanje', value: 'adhoc' },
                  ]}
                />
              </Group>

              {receiptMode === 'linked' ? (
                <Stack gap="lg">
                  <Paper withBorder radius="md" p="lg">
                    <Stack gap="md">
                      <div>
                        <Text fw={600} mb={6}>
                          Odabir narudžbenice
                        </Text>
                        <Text c="dimmed" size="sm">
                          Odaberi otvorenu narudžbenicu ili pretraži po broju ili dobavljaču.
                        </Text>
                      </div>

                      {openOrdersError ? (
                        <Group justify="space-between" align="center">
                          <Text size="sm" c="red">{openOrdersError}</Text>
                          <Button
                            size="xs"
                            variant="default"
                            onClick={() => void loadOpenOrders()}
                          >
                            Pokušaj ponovno
                          </Button>
                        </Group>
                      ) : (
                        <Select
                          label="Broj narudžbenice"
                          placeholder={openOrdersLoading ? 'Učitavanje…' : 'Odaberi narudžbenicu'}
                          searchable
                          clearable
                          disabled={openOrdersLoading}
                          data={openOrders.map((o) => ({
                            value: String(o.id),
                            label: o.order_number,
                          }))}
                          onSearchChange={setOrderQuery}
                          onChange={(value) => {
                            setOrderSearchError(null)
                            if (!value) {
                              clearLinkedOrderData()
                              return
                            }
                            const orderId = Number(value)
                            const orderItem = openOrders.find((o) => o.id === orderId)
                            if (orderItem) void handleOrderSelect(orderId, orderItem)
                          }}
                          error={orderSearchError}
                          nothingFoundMessage={orderQuery.trim() ? 'Nema rezultata.' : undefined}
                          filter={({ options, search }) => {
                            const q = search.trim().toLowerCase()
                            if (!q) return options
                            return options.filter((opt) => {
                              if (!('value' in opt)) return false
                              const order = openOrders.find((o) => String(o.id) === opt.value)
                              if (!order) return false
                              return (
                                order.order_number.toLowerCase().includes(q) ||
                                (order.supplier_name ?? '').toLowerCase().includes(q)
                              )
                            })
                          }}
                          renderOption={({ option }) => {
                            const order = openOrders.find((o) => String(o.id) === option.value)
                            return (
                              <Stack gap={2}>
                                <Text size="sm" fw={600}>{option.label}</Text>
                                {order?.supplier_name ? (
                                  <Text size="xs" c="dimmed">{order.supplier_name}</Text>
                                ) : null}
                              </Stack>
                            )
                          }}
                          maxDropdownHeight={280}
                          rightSection={linkedOrderLoading ? <Loader size={16} /> : undefined}
                        />
                      )}
                    </Stack>
                  </Paper>

                  {linkedOrderSummary ? (
                    <Paper withBorder radius="md" p="lg">
                      <Stack gap="md">
                        <Group justify="space-between" align="flex-start">
                          <Stack gap={4}>
                            <Group gap="xs">
                              <Text fw={600}>{linkedOrderSummary.order_number}</Text>
                              <Badge color={linkedOrderSummary.status === 'OPEN' ? 'green' : 'gray'}>
                                {getOrderStatusLabel(linkedOrderSummary.status)}
                              </Badge>
                            </Group>
                            <Text size="sm" c="dimmed">
                              Dobavljač: {linkedOrderSummary.supplier_name ?? '—'}
                            </Text>
                          </Stack>

                          <Stack gap={2} align="flex-end">
                            <Text size="sm">Otvorene stavke: {linkedOrderSummary.open_line_count}</Text>
                            <Text size="sm" c="dimmed">
                              Kreirano: {formatDate(linkedOrderSummary.created_at)}
                            </Text>
                          </Stack>
                        </Group>

                        {linkedOrderWarning ? (
                          <Alert
                            color="yellow"
                            icon={<IconAlertTriangle size={16} />}
                            title="Upozorenje"
                          >
                            {linkedOrderWarning}
                          </Alert>
                        ) : null}

                        {linkedOrderLoading ? (
                          <Group justify="center" py="xl">
                            <Loader />
                          </Group>
                        ) : linkedOrderDetail?.lines.length ? (
                          <form onSubmit={handleLinkedSubmit}>
                            <Stack gap="lg">
                              <Divider />

                              <Group grow align="flex-start">
                                <TextInput
                                  label="Broj dostavnice"
                                  value={linkedHeader.deliveryNoteNumber}
                                  onChange={(event) => {
                                    setLinkedHeader((prev) => ({
                                      ...prev,
                                      deliveryNoteNumber: event.currentTarget.value,
                                    }))
                                    setLinkedHeaderErrors((prev) => ({
                                      ...prev,
                                      deliveryNoteNumber: undefined,
                                    }))
                                  }}
                                  error={linkedHeaderErrors.deliveryNoteNumber}
                                  disabled={linkedSubmitting || Boolean(linkedOrderWarning)}
                                  withAsterisk
                                />
                                <Textarea
                                  label="Napomena"
                                  value={linkedHeader.note}
                                  onChange={(event) => {
                                    setLinkedHeader((prev) => ({
                                      ...prev,
                                      note: event.currentTarget.value,
                                    }))
                                    setLinkedHeaderErrors((prev) => ({
                                      ...prev,
                                      note: undefined,
                                    }))
                                  }}
                                  error={linkedHeaderErrors.note}
                                  disabled={linkedSubmitting || Boolean(linkedOrderWarning)}
                                  autosize
                                  minRows={2}
                                />
                              </Group>

                              <div>
                                <Text fw={600} mb="sm">
                                  Otvorene stavke
                                </Text>
                                <Box style={{ overflowX: 'auto' }}>
                                  <Table striped highlightOnHover withTableBorder withColumnBorders style={{ minWidth: 1120 }}>
                                    <Table.Thead>
                                      <Table.Tr>
                                        <Table.Th>Artikl</Table.Th>
                                        <Table.Th>Opis</Table.Th>
                                        <Table.Th>Naručeno</Table.Th>
                                        <Table.Th>Zaprimljeno</Table.Th>
                                        <Table.Th>Preostalo</Table.Th>
                                        <Table.Th>UOM</Table.Th>
                                        <Table.Th>Zaprimljena količina</Table.Th>
                                        <Table.Th>Batch code</Table.Th>
                                        <Table.Th>Expiry date</Table.Th>
                                        <Table.Th>Preskoči</Table.Th>
                                      </Table.Tr>
                                    </Table.Thead>
                                    <Table.Tbody>
                                      {linkedOrderDetail.lines.map((line) => {
                                        const state = linkedLineState[line.id] ?? {
                                          quantity: '',
                                          batchCode: '',
                                          expiryDate: '',
                                          skip: false,
                                        }
                                        const errors = linkedLineErrors[line.id] ?? {}
                                        const disabled = linkedSubmitting || Boolean(linkedOrderWarning) || state.skip

                                        return (
                                          <Table.Tr
                                            key={line.id}
                                            style={state.skip ? { backgroundColor: '#f8f9fa' } : undefined}
                                          >
                                            <Table.Td>{line.article_no}</Table.Td>
                                            <Table.Td>{line.description}</Table.Td>
                                            <Table.Td>{formatQuantity(line.ordered_qty, line.uom)}</Table.Td>
                                            <Table.Td>{formatQuantity(line.received_qty, line.uom)}</Table.Td>
                                            <Table.Td>{formatQuantity(line.remaining_qty, line.uom)}</Table.Td>
                                            <Table.Td>{line.uom}</Table.Td>
                                            <Table.Td>
                                              <Stack gap={4}>
                                                <NumberInput
                                                  value={state.quantity}
                                                  onChange={(value) => {
                                                    setLinkedLineState((prev) => ({
                                                      ...prev,
                                                      [line.id]: {
                                                        ...prev[line.id],
                                                        quantity: value,
                                                      },
                                                    }))
                                                    setLinkedLineErrors((prev) => ({
                                                      ...prev,
                                                      [line.id]: {
                                                        ...prev[line.id],
                                                        quantity: undefined,
                                                        line: undefined,
                                                      },
                                                    }))
                                                  }}
                                                  min={0}
                                                  step={getQuantityStep(line.uom)}
                                                  decimalScale={getQuantityScale(line.uom)}
                                                  allowNegative={false}
                                                  hideControls
                                                  disabled={disabled}
                                                  error={errors.quantity}
                                                />
                                                {errors.line ? (
                                                  <Text c="red" size="xs">
                                                    {errors.line}
                                                  </Text>
                                                ) : null}
                                              </Stack>
                                            </Table.Td>
                                            <Table.Td>
                                              {line.has_batch ? (
                                                <TextInput
                                                  value={state.batchCode}
                                                  onChange={(event) => {
                                                    setLinkedLineState((prev) => ({
                                                      ...prev,
                                                      [line.id]: {
                                                        ...prev[line.id],
                                                        batchCode: event.currentTarget.value,
                                                      },
                                                    }))
                                                    setLinkedLineErrors((prev) => ({
                                                      ...prev,
                                                      [line.id]: {
                                                        ...prev[line.id],
                                                        batchCode: undefined,
                                                        line: undefined,
                                                      },
                                                    }))
                                                  }}
                                                  disabled={disabled}
                                                  error={errors.batchCode}
                                                />
                                              ) : (
                                                <Text c="dimmed" size="sm">
                                                  —
                                                </Text>
                                              )}
                                            </Table.Td>
                                            <Table.Td>
                                              {line.has_batch ? (
                                                <TextInput
                                                  type="date"
                                                  value={state.expiryDate}
                                                  onChange={(event) => {
                                                    setLinkedLineState((prev) => ({
                                                      ...prev,
                                                      [line.id]: {
                                                        ...prev[line.id],
                                                        expiryDate: event.currentTarget.value,
                                                      },
                                                    }))
                                                    setLinkedLineErrors((prev) => ({
                                                      ...prev,
                                                      [line.id]: {
                                                        ...prev[line.id],
                                                        expiryDate: undefined,
                                                        line: undefined,
                                                      },
                                                    }))
                                                  }}
                                                  disabled={disabled}
                                                  error={errors.expiryDate}
                                                />
                                              ) : (
                                                <Text c="dimmed" size="sm">
                                                  —
                                                </Text>
                                              )}
                                            </Table.Td>
                                            <Table.Td>
                                              <Checkbox
                                                checked={state.skip}
                                                onChange={(event) => {
                                                  const checked = event.currentTarget.checked
                                                  setLinkedLineState((prev) => ({
                                                    ...prev,
                                                    [line.id]: {
                                                      ...prev[line.id],
                                                      skip: checked,
                                                    },
                                                  }))
                                                  setLinkedLineErrors((prev) => ({
                                                    ...prev,
                                                    [line.id]: checked ? {} : prev[line.id],
                                                  }))
                                                  setLinkedFormError(null)
                                                }}
                                                disabled={linkedSubmitting || Boolean(linkedOrderWarning)}
                                              />
                                            </Table.Td>
                                          </Table.Tr>
                                        )
                                      })}
                                    </Table.Tbody>
                                  </Table>
                                </Box>
                              </div>

                              {linkedFormError ? (
                                <Text c="red" size="sm">
                                  {linkedFormError}
                                </Text>
                              ) : null}

                              <Group justify="flex-end">
                                <Button
                                  type="submit"
                                  loading={linkedSubmitting}
                                  disabled={linkedSubmitting || Boolean(linkedOrderWarning)}
                                >
                                  Confirm Receipt
                                </Button>
                              </Group>
                            </Stack>
                          </form>
                        ) : (
                          <Text c="dimmed" ta="center" py="xl">
                            Nema otvorenih stavki za zaprimanje.
                          </Text>
                        )}
                      </Stack>
                    </Paper>
                  ) : (
                    <Paper withBorder radius="md" p="xl">
                      <Text c="dimmed" ta="center">
                        Unesi broj narudžbenice kako bi se prikazale otvorene stavke za zaprimanje.
                      </Text>
                    </Paper>
                  )}
                </Stack>
              ) : (
                <Paper withBorder radius="md" p="lg">
                  <form onSubmit={handleAdhocSubmit}>
                    <Stack gap="lg">
                      <Group grow align="flex-start">
                        <TextInput
                          label="Broj artikla"
                          value={articleQuery}
                          onChange={(event) => handleArticleQueryChange(event.currentTarget.value)}
                          onBlur={handleArticleBlur}
                          placeholder="Unesi broj artikla ili barkod"
                          rightSection={articleLookupState === 'loading' ? <Loader size="xs" /> : null}
                          error={adhocErrors.article}
                          withAsterisk
                          disabled={adhocSubmitting}
                        />
                        <TextInput
                          label="UOM"
                          value={resolvedArticle?.base_uom ?? ''}
                          readOnly
                          placeholder="Automatski"
                        />
                      </Group>

                      {resolvedArticle ? (
                        <Paper withBorder radius="md" p="md" bg="gray.0">
                          <Stack gap={4}>
                            <Text fw={600}>{resolvedArticle.article_no}</Text>
                            <Text size="sm">{resolvedArticle.description}</Text>
                            <Text c="dimmed" size="sm">
                              Batch tracking: {resolvedArticle.has_batch ? 'Da' : 'Ne'}
                            </Text>
                          </Stack>
                        </Paper>
                      ) : null}

                      <Group grow align="flex-start">
                        <NumberInput
                          label="Količina"
                          value={adhocForm.quantity}
                          onChange={(value) => {
                            setAdhocForm((prev) => ({
                              ...prev,
                              quantity: value,
                            }))
                            setAdhocErrors((prev) => ({
                              ...prev,
                              quantity: undefined,
                            }))
                          }}
                          min={0}
                          step={getQuantityStep(resolvedArticle?.base_uom)}
                          decimalScale={getQuantityScale(resolvedArticle?.base_uom)}
                          allowNegative={false}
                          hideControls
                          error={adhocErrors.quantity}
                          withAsterisk
                          disabled={adhocSubmitting}
                        />
                        <TextInput
                          label="Broj dostavnice"
                          value={adhocForm.deliveryNoteNumber}
                          onChange={(event) => {
                            setAdhocForm((prev) => ({
                              ...prev,
                              deliveryNoteNumber: event.currentTarget.value,
                            }))
                            setAdhocErrors((prev) => ({
                              ...prev,
                              deliveryNoteNumber: undefined,
                            }))
                          }}
                          error={adhocErrors.deliveryNoteNumber}
                          withAsterisk
                          disabled={adhocSubmitting}
                        />
                      </Group>

                      {resolvedArticle?.has_batch ? (
                        <Group grow align="flex-start">
                          <TextInput
                            label="Batch code"
                            value={adhocForm.batchCode}
                            onChange={(event) => {
                              setAdhocForm((prev) => ({
                                ...prev,
                                batchCode: event.currentTarget.value,
                              }))
                              setAdhocErrors((prev) => ({
                                ...prev,
                                batchCode: undefined,
                              }))
                            }}
                            error={adhocErrors.batchCode}
                            withAsterisk
                            disabled={adhocSubmitting}
                          />
                          <TextInput
                            label="Expiry date"
                            type="date"
                            value={adhocForm.expiryDate}
                            onChange={(event) => {
                              setAdhocForm((prev) => ({
                                ...prev,
                                expiryDate: event.currentTarget.value,
                              }))
                              setAdhocErrors((prev) => ({
                                ...prev,
                                expiryDate: undefined,
                              }))
                            }}
                            error={adhocErrors.expiryDate}
                            withAsterisk
                            disabled={adhocSubmitting}
                          />
                        </Group>
                      ) : null}

                      <Textarea
                        label="Napomena"
                        value={adhocForm.note}
                        onChange={(event) => {
                          setAdhocForm((prev) => ({
                            ...prev,
                            note: event.currentTarget.value,
                          }))
                          setAdhocErrors((prev) => ({
                            ...prev,
                            note: undefined,
                          }))
                        }}
                        error={adhocErrors.note}
                        autosize
                        minRows={3}
                        withAsterisk
                        disabled={adhocSubmitting}
                      />

                      <Group justify="flex-end">
                        <Button type="submit" loading={adhocSubmitting} disabled={adhocSubmitting}>
                          Confirm Receipt
                        </Button>
                      </Group>
                    </Stack>
                  </form>
                </Paper>
              )}
            </Stack>
          </Paper>
        </Tabs.Panel>

        <Tabs.Panel value="history" pt="md">
          <Paper withBorder radius="lg" p="xl">
            <Stack gap="md">
              <div>
                <Title order={4}>Povijest zaprimanja</Title>
                <Text c="dimmed" size="sm">
                  Najnovija zaprimanja su prikazana prva.
                </Text>
              </div>

              {historyLoading ? (
                <Group justify="center" py="xl">
                  <Loader />
                </Group>
              ) : historyLoaded && historyItems.length === 0 ? (
                <Text c="dimmed" ta="center" py="xl">
                  Nema evidentiranih zaprimanja.
                </Text>
              ) : historyLoaded ? (
                <Box style={{ overflowX: 'auto' }}>
                  <Table striped highlightOnHover withTableBorder withColumnBorders style={{ minWidth: 980 }}>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Datum</Table.Th>
                        <Table.Th>Narudžbenica</Table.Th>
                        <Table.Th>Artikl</Table.Th>
                        <Table.Th>Količina</Table.Th>
                        <Table.Th>UOM</Table.Th>
                        <Table.Th>Batch</Table.Th>
                        <Table.Th>Broj dostavnice</Table.Th>
                        <Table.Th>Zaprimio</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {historyItems.map((item) => (
                        <Table.Tr key={item.id}>
                          <Table.Td>{formatDateTime(item.received_at)}</Table.Td>
                          <Table.Td>{item.order_number}</Table.Td>
                          <Table.Td>
                            <Stack gap={0}>
                              <Text size="sm" fw={500}>
                                {item.article_no ?? '—'}
                              </Text>
                              <Text size="xs" c="dimmed">
                                {item.description ?? '—'}
                              </Text>
                            </Stack>
                          </Table.Td>
                          <Table.Td>{formatQuantity(item.quantity, item.uom)}</Table.Td>
                          <Table.Td>{item.uom}</Table.Td>
                          <Table.Td>{item.batch_code ?? '—'}</Table.Td>
                          <Table.Td>{item.delivery_note_number ?? '—'}</Table.Td>
                          <Table.Td>{item.received_by ?? '—'}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Box>
              ) : (
                <Text c="dimmed" ta="center" py="xl">
                  Povijest još nije učitana.
                </Text>
              )}
            </Stack>
          </Paper>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}
