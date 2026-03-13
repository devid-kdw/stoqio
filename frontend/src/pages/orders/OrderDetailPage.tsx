import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Loader,
  NumberInput,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { IconPencil, IconTrash } from '@tabler/icons-react'

import {
  ordersApi,
  type OrderDetail,
  type OrderDetailLine,
  type UpdateOrderHeaderPayload,
  type UpdateOrderLinePayload,
} from '../../api/orders'
import FullPageState from '../../components/shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import { CONNECTION_ERROR_MESSAGE, getApiErrorBody, isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import {
  createEmptyOrderLineDraft,
  createExistingOrderLineDraft,
  findArticleOption,
  formatDate,
  formatDateTime,
  formatMoney,
  formatQuantity,
  getArticleSelectData,
  getOrderLineStatusColor,
  getOrderLineStatusLabel,
  getOrderStatusColor,
  getOrderStatusLabel,
  getQuantityScale,
  getQuantityStep,
  normalizeOptionalText,
  type OrderLineDraft,
  type OrderLineFormErrors,
} from './orderUtils'

interface HeaderFormState {
  supplierConfirmationNumber: string
  note: string
}

interface HeaderFormErrors {
  supplierConfirmationNumber?: string
  note?: string
}

function validateLineDraft(line: OrderLineDraft): OrderLineFormErrors {
  const errors: OrderLineFormErrors = {}
  const orderedQty =
    typeof line.orderedQty === 'string' ? Number.parseFloat(line.orderedQty) : line.orderedQty
  const unitPrice =
    typeof line.unitPrice === 'string' ? Number.parseFloat(line.unitPrice) : line.unitPrice

  if (!line.articleId) {
    errors.article = 'Artikl je obavezan.'
  }

  if (line.supplierArticleCode.trim().length > 255) {
    errors.supplierArticleCode = 'Šifra dobavljača može imati najviše 255 znakova.'
  }

  if (line.orderedQty === '' || Number.isNaN(orderedQty) || orderedQty <= 0) {
    errors.orderedQty = 'Količina mora biti veća od 0.'
  }

  if (line.unitPrice === '' || Number.isNaN(unitPrice) || unitPrice < 0) {
    errors.unitPrice = 'Jedinična cijena mora biti 0 ili veća.'
  }

  if (line.note.trim().length > 1000) {
    errors.note = 'Napomena može imati najviše 1000 znakova.'
  }

  return errors
}

export default function OrderDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN'

  const orderId = Number(id)

  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [pageLoading, setPageLoading] = useState(true)
  const [fatalError, setFatalError] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  const [headerForm, setHeaderForm] = useState<HeaderFormState>({
    supplierConfirmationNumber: '',
    note: '',
  })
  const [headerErrors, setHeaderErrors] = useState<HeaderFormErrors>({})
  const [showHeaderForm, setShowHeaderForm] = useState(false)
  const [headerSubmitting, setHeaderSubmitting] = useState(false)

  const [showAddLineForm, setShowAddLineForm] = useState(false)
  const [addLineDraft, setAddLineDraft] = useState<OrderLineDraft>(createEmptyOrderLineDraft())
  const [addLineErrors, setAddLineErrors] = useState<OrderLineFormErrors>({})
  const [addLineSubmitting, setAddLineSubmitting] = useState(false)
  const articleLookupTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [editingLineId, setEditingLineId] = useState<number | null>(null)
  const [editingLineDraft, setEditingLineDraft] = useState<OrderLineDraft | null>(null)
  const [editingLineErrors, setEditingLineErrors] = useState<OrderLineFormErrors>({})
  const [lineSubmittingId, setLineSubmittingId] = useState<number | null>(null)

  const [downloadingPdf, setDownloadingPdf] = useState(false)

  const resetInlineForms = useCallback(() => {
    setShowHeaderForm(false)
    setHeaderErrors({})
    setShowAddLineForm(false)
    setAddLineDraft(createEmptyOrderLineDraft())
    setAddLineErrors({})
    setEditingLineId(null)
    setEditingLineDraft(null)
    setEditingLineErrors({})
  }, [])

  const applyUpdatedOrder = useCallback(
    (nextOrder: OrderDetail) => {
      setOrder(nextOrder)
      setHeaderForm({
        supplierConfirmationNumber: nextOrder.supplier_confirmation_number ?? '',
        note: nextOrder.note ?? '',
      })
      resetInlineForms()
    },
    [resetInlineForms]
  )

  const loadOrder = useCallback(async () => {
    if (!Number.isInteger(orderId) || orderId <= 0) {
      setNotFound(true)
      setPageError('Narudžbenica nije pronađena.')
      setPageLoading(false)
      return
    }

    setPageLoading(true)
    setPageError(null)
    setFatalError(false)
    setNotFound(false)

    try {
      const response = await runWithRetry(() => ordersApi.getDetail(orderId))
      setOrder(response)
      setHeaderForm({
        supplierConfirmationNumber: response.supplier_confirmation_number ?? '',
        note: response.note ?? '',
      })
      resetInlineForms()
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      const apiError = getApiErrorBody(error)
      if (apiError?.error === 'ORDER_NOT_FOUND') {
        setNotFound(true)
        setPageError('Narudžbenica nije pronađena.')
      } else {
        setPageError(apiError?.message ?? 'Detalj narudžbenice nije dostupan.')
      }
    } finally {
      setPageLoading(false)
    }
  }, [orderId, resetInlineForms])

  useEffect(() => {
    void loadOrder()
  }, [loadOrder])

  useEffect(() => {
    return () => {
      if (articleLookupTimerRef.current) {
        clearTimeout(articleLookupTimerRef.current)
      }
    }
  }, [])

  const isOpenOrder = order?.status === 'OPEN'
  const canMutate = isAdmin && isOpenOrder

  const handleHeaderFormOpen = useCallback(() => {
    if (!order) {
      return
    }

    setHeaderForm({
      supplierConfirmationNumber: order.supplier_confirmation_number ?? '',
      note: order.note ?? '',
    })
    setHeaderErrors({})
    setShowHeaderForm(true)
    setShowAddLineForm(false)
    setEditingLineId(null)
    setEditingLineDraft(null)
  }, [order])

  const handleAddLineSearch = useCallback(
    (query: string) => {
      if (articleLookupTimerRef.current) {
        clearTimeout(articleLookupTimerRef.current)
      }

      const normalized = query.trim()
      if (!normalized) {
        setAddLineDraft((current) => ({
          ...current,
          articleOptions: [],
          articleLookupState: current.selectedArticle ? 'found' : 'idle',
        }))
        return
      }

      setAddLineDraft((current) => ({
        ...current,
        articleLookupState: 'loading',
      }))

      articleLookupTimerRef.current = setTimeout(async () => {
        try {
          const response = await runWithRetry(() =>
            ordersApi.lookupArticles(normalized, order?.supplier_id ?? undefined)
          )
          setAddLineDraft((current) => ({
            ...current,
            articleOptions: response.items,
            articleLookupState: response.items.length > 0 ? 'found' : 'not-found',
          }))
        } catch (error) {
          if (isNetworkOrServerError(error)) {
            setFatalError(true)
            return
          }

          setAddLineDraft((current) => ({
            ...current,
            articleLookupState: 'not-found',
          }))
          showErrorToast(getApiErrorBody(error)?.message ?? 'Dohvat artikala nije uspio.')
        }
      }, 300)
    },
    [order?.supplier_id]
  )

  const handleAddLineArticleChange = useCallback((value: string | null) => {
    setAddLineDraft((current) => {
      const selectedArticle = findArticleOption(current, value)

      if (!selectedArticle) {
        return {
          ...current,
          articleId: null,
          selectedArticle: null,
          supplierArticleCode: '',
          uom: '',
          unitPrice: '',
          articleLookupState: 'idle',
        }
      }

      return {
        ...current,
        articleId: selectedArticle.article_id,
        selectedArticle,
        supplierArticleCode: selectedArticle.supplier_article_code ?? '',
        uom: selectedArticle.uom ?? '',
        unitPrice: selectedArticle.last_price ?? '',
        articleLookupState: 'found',
      }
    })

    setAddLineErrors((current) => ({
      ...current,
      article: undefined,
      supplierArticleCode: undefined,
    }))
  }, [])

  const handleUpdateHeader = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextErrors: HeaderFormErrors = {}
    if (headerForm.supplierConfirmationNumber.trim().length > 255) {
      nextErrors.supplierConfirmationNumber =
        'Broj potvrde dobavljača može imati najviše 255 znakova.'
    }

    if (headerForm.note.trim().length > 1000) {
      nextErrors.note = 'Napomena može imati najviše 1000 znakova.'
    }

    setHeaderErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0 || !order) {
      return
    }

    setHeaderSubmitting(true)
    const payload: UpdateOrderHeaderPayload = {
      supplier_confirmation_number: normalizeOptionalText(headerForm.supplierConfirmationNumber),
      note: normalizeOptionalText(headerForm.note),
    }

    try {
      const response = await runWithRetry(() => ordersApi.updateHeader(order.id, payload))
      applyUpdatedOrder(response)
      showSuccessToast('Narudžbenica je ažurirana.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Ažuriranje narudžbenice nije uspjelo.')
    } finally {
      setHeaderSubmitting(false)
    }
  }

  const handleAddLine = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const nextErrors = validateLineDraft(addLineDraft)
    setAddLineErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0 || !order) {
      return
    }

    setAddLineSubmitting(true)

    try {
      const response = await runWithRetry(() =>
        ordersApi.addLine(order.id, {
          article_id: addLineDraft.articleId!,
          supplier_article_code: normalizeOptionalText(addLineDraft.supplierArticleCode),
          ordered_qty:
            typeof addLineDraft.orderedQty === 'string'
              ? Number.parseFloat(addLineDraft.orderedQty)
              : addLineDraft.orderedQty,
          uom: addLineDraft.uom,
          unit_price:
            typeof addLineDraft.unitPrice === 'string'
              ? Number.parseFloat(addLineDraft.unitPrice)
              : addLineDraft.unitPrice,
          delivery_date: normalizeOptionalText(addLineDraft.deliveryDate),
          note: normalizeOptionalText(addLineDraft.note),
        })
      )
      applyUpdatedOrder(response)
      showSuccessToast('Stavka je dodana.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      const apiError = getApiErrorBody(error)
      setAddLineErrors((current) => ({
        ...current,
        line: apiError?.message ?? 'Dodavanje stavke nije uspjelo.',
      }))
    } finally {
      setAddLineSubmitting(false)
    }
  }

  const handleStartLineEdit = useCallback((line: OrderDetailLine) => {
    setEditingLineId(line.id)
    setEditingLineDraft(createExistingOrderLineDraft(line))
    setEditingLineErrors({})
    setShowHeaderForm(false)
    setShowAddLineForm(false)
  }, [])

  const handleSaveLine = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!order || !editingLineId || !editingLineDraft) {
      return
    }

    const nextErrors = validateLineDraft(editingLineDraft)
    setEditingLineErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }

    setLineSubmittingId(editingLineId)
    const payload: UpdateOrderLinePayload = {
      supplier_article_code: normalizeOptionalText(editingLineDraft.supplierArticleCode),
      ordered_qty:
        typeof editingLineDraft.orderedQty === 'string'
          ? Number.parseFloat(editingLineDraft.orderedQty)
          : editingLineDraft.orderedQty,
      unit_price:
        typeof editingLineDraft.unitPrice === 'string'
          ? Number.parseFloat(editingLineDraft.unitPrice)
          : editingLineDraft.unitPrice,
      delivery_date: normalizeOptionalText(editingLineDraft.deliveryDate),
      note: normalizeOptionalText(editingLineDraft.note),
    }

    try {
      const response = await runWithRetry(() =>
        ordersApi.updateLine(order.id, editingLineId, payload)
      )
      applyUpdatedOrder(response)
      showSuccessToast('Stavka je ažurirana.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setEditingLineErrors((current) => ({
        ...current,
        line: getApiErrorBody(error)?.message ?? 'Ažuriranje stavke nije uspjelo.',
      }))
    } finally {
      setLineSubmittingId(null)
    }
  }

  const handleRemoveLine = async (line: OrderDetailLine) => {
    if (!order) {
      return
    }

    const confirmed = window.confirm(`Ukloniti stavku ${line.position}?`)
    if (!confirmed) {
      return
    }

    setLineSubmittingId(line.id)

    try {
      const response = await runWithRetry(() => ordersApi.removeLine(order.id, line.id))
      applyUpdatedOrder(response)
      showSuccessToast('Stavka je uklonjena.')
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Uklanjanje stavke nije uspjelo.')
    } finally {
      setLineSubmittingId(null)
    }
  }

  const handleDownloadPdf = async () => {
    if (!order) {
      return
    }

    setDownloadingPdf(true)

    try {
      await runWithRetry(() => ordersApi.downloadPdf(order.id, order.order_number))
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Preuzimanje PDF-a nije uspjelo.')
    } finally {
      setDownloadingPdf(false)
    }
  }

  if (fatalError) {
    return (
      <FullPageState
        title="Connection error"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Try again"
        onAction={() => window.location.reload()}
      />
    )
  }

  if (pageError) {
    return (
      <FullPageState
        title={notFound ? 'Narudžbenica nije pronađena.' : 'Detalj narudžbenice nije dostupan.'}
        message={pageError}
        actionLabel={notFound ? 'Natrag na popis' : 'Pokušaj ponovno'}
        onAction={notFound ? () => navigate('/orders') : () => void loadOrder()}
      />
    )
  }

  if (pageLoading || !order) {
    return (
      <Group justify="center" py="xl">
        <Loader />
      </Group>
    )
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Group gap="sm">
            <Title order={2}>{order.order_number}</Title>
            <Badge color={getOrderStatusColor(order.status)} variant="light">
              {getOrderStatusLabel(order.status)}
            </Badge>
          </Group>
          <Text c="dimmed" mt={4}>
            Dobavljač: {order.supplier_name ?? '—'}
          </Text>
        </div>

        <Group>
          <Button variant="light" color="gray" onClick={() => navigate('/orders')}>
            Natrag
          </Button>
          <Button variant="light" onClick={handleDownloadPdf} loading={downloadingPdf}>
            Generiraj PDF
          </Button>
          {canMutate ? (
            <>
              <Button variant="light" onClick={handleHeaderFormOpen}>
                Uredi narudžbenicu
              </Button>
              <Button
                onClick={() => {
                  setAddLineDraft(createEmptyOrderLineDraft())
                  setAddLineErrors({})
                  setShowAddLineForm((current) => !current)
                  setShowHeaderForm(false)
                  setEditingLineId(null)
                  setEditingLineDraft(null)
                }}
              >
                Dodaj stavku
              </Button>
            </>
          ) : null}
        </Group>
      </Group>

      <Group grow align="stretch">
        <Paper withBorder radius="lg" p="lg">
          <Stack gap="xs">
            <Title order={4}>Podaci narudžbenice</Title>
            <Text>
              <strong>Dobavljač:</strong> {order.supplier_name ?? '—'}
            </Text>
            <Text>
              <strong>Adresa:</strong> {order.supplier_address ?? '—'}
            </Text>
            <Text>
              <strong>Datum kreiranja:</strong> {formatDateTime(order.created_at)}
            </Text>
            <Text>
              <strong>Zadnja promjena:</strong> {formatDateTime(order.updated_at)}
            </Text>
            <Text>
              <strong>Broj potvrde dobavljača:</strong>{' '}
              {order.supplier_confirmation_number ?? '—'}
            </Text>
            <Text>
              <strong>Napomena:</strong> {order.note ?? '—'}
            </Text>
          </Stack>
        </Paper>

        <Paper withBorder radius="lg" p="lg">
          <Stack gap="sm">
            <Title order={4}>Sažetak</Title>
            <Text size="sm" c="dimmed">
              Ukupna vrijednost
            </Text>
            <Text size="2rem" fw={700}>
              {formatMoney(order.total_value)}
            </Text>
            <Text size="sm" c="dimmed">
              Otvorenih stavki: {order.lines.filter((line) => line.status === 'OPEN').length}
            </Text>
          </Stack>
        </Paper>
      </Group>

      {showHeaderForm && canMutate ? (
        <Paper withBorder radius="lg" p="lg">
          <form onSubmit={handleUpdateHeader}>
            <Stack gap="md">
              <Title order={4}>Uredi zaglavlje</Title>
              <Group grow align="flex-start">
                <TextInput
                  label="Broj potvrde dobavljača"
                  value={headerForm.supplierConfirmationNumber}
                  onChange={(event) => {
                    setHeaderForm((current) => ({
                      ...current,
                      supplierConfirmationNumber: event.currentTarget.value,
                    }))
                    setHeaderErrors((current) => ({
                      ...current,
                      supplierConfirmationNumber: undefined,
                    }))
                  }}
                  error={headerErrors.supplierConfirmationNumber}
                />
                <Textarea
                  label="Napomena"
                  autosize
                  minRows={2}
                  value={headerForm.note}
                  onChange={(event) => {
                    setHeaderForm((current) => ({
                      ...current,
                      note: event.currentTarget.value,
                    }))
                    setHeaderErrors((current) => ({
                      ...current,
                      note: undefined,
                    }))
                  }}
                  error={headerErrors.note}
                />
              </Group>
              <Group justify="flex-end">
                <Button type="button" variant="subtle" color="gray" onClick={resetInlineForms}>
                  Odustani
                </Button>
                <Button type="submit" loading={headerSubmitting}>
                  Spremi promjene
                </Button>
              </Group>
            </Stack>
          </form>
        </Paper>
      ) : null}

      {showAddLineForm && canMutate ? (
        <Paper withBorder radius="lg" p="lg">
          <form onSubmit={handleAddLine}>
            <Stack gap="md">
              <Title order={4}>Dodaj stavku</Title>

              <Group grow align="flex-start">
                <Select
                  label="Artikl"
                  placeholder="Pretraži po broju ili opisu"
                  searchable
                  clearable
                  value={addLineDraft.articleId ? String(addLineDraft.articleId) : null}
                  data={getArticleSelectData(addLineDraft)}
                  onSearchChange={handleAddLineSearch}
                  onChange={handleAddLineArticleChange}
                  nothingFoundMessage="Nema rezultata."
                  error={addLineErrors.article}
                  rightSection={
                    addLineDraft.articleLookupState === 'loading' ? <Loader size={16} /> : null
                  }
                />
                <TextInput
                  label="Šifra artikla dobavljača"
                  value={addLineDraft.supplierArticleCode}
                  onChange={(event) => {
                    setAddLineDraft((current) => ({
                      ...current,
                      supplierArticleCode: event.currentTarget.value,
                    }))
                    setAddLineErrors((current) => ({
                      ...current,
                      supplierArticleCode: undefined,
                    }))
                  }}
                  error={addLineErrors.supplierArticleCode}
                />
              </Group>

              <Group grow align="flex-start">
                <NumberInput
                  label="Količina"
                  min={0}
                  step={getQuantityStep(addLineDraft.uom)}
                  decimalScale={getQuantityScale(addLineDraft.uom)}
                  value={addLineDraft.orderedQty}
                  onChange={(value) => {
                    setAddLineDraft((current) => ({
                      ...current,
                      orderedQty: value,
                    }))
                    setAddLineErrors((current) => ({
                      ...current,
                      orderedQty: undefined,
                    }))
                  }}
                  error={addLineErrors.orderedQty}
                />
                <TextInput label="JM" value={addLineDraft.uom} readOnly placeholder="—" />
                <NumberInput
                  label="Jedinična cijena"
                  min={0}
                  step={0.01}
                  decimalScale={4}
                  value={addLineDraft.unitPrice}
                  onChange={(value) => {
                    setAddLineDraft((current) => ({
                      ...current,
                      unitPrice: value,
                    }))
                    setAddLineErrors((current) => ({
                      ...current,
                      unitPrice: undefined,
                    }))
                  }}
                  error={addLineErrors.unitPrice}
                />
                <TextInput
                  label="Datum isporuke"
                  type="date"
                  value={addLineDraft.deliveryDate}
                  onChange={(event) =>
                    setAddLineDraft((current) => ({
                      ...current,
                      deliveryDate: event.currentTarget.value,
                    }))
                  }
                />
              </Group>

              <Textarea
                label="Napomena stavke"
                autosize
                minRows={2}
                value={addLineDraft.note}
                onChange={(event) => {
                  setAddLineDraft((current) => ({
                    ...current,
                    note: event.currentTarget.value,
                  }))
                  setAddLineErrors((current) => ({
                    ...current,
                    note: undefined,
                  }))
                }}
                error={addLineErrors.note}
              />

              {addLineErrors.line ? (
                <Text c="red" size="sm">
                  {addLineErrors.line}
                </Text>
              ) : null}

              <Group justify="flex-end">
                <Button type="button" variant="subtle" color="gray" onClick={resetInlineForms}>
                  Odustani
                </Button>
                <Button type="submit" loading={addLineSubmitting}>
                  Dodaj stavku
                </Button>
              </Group>
            </Stack>
          </form>
        </Paper>
      ) : null}

      {editingLineDraft && editingLineId && canMutate ? (
        <Paper withBorder radius="lg" p="lg">
          <form onSubmit={handleSaveLine}>
            <Stack gap="md">
              <Title order={4}>Uredi stavku</Title>
              <Text size="sm" c="dimmed">
                Artikl: {editingLineDraft.selectedArticle?.article_no} •{' '}
                {editingLineDraft.selectedArticle?.description}
              </Text>

              <Group grow align="flex-start">
                <TextInput
                  label="Šifra artikla dobavljača"
                  value={editingLineDraft.supplierArticleCode}
                  onChange={(event) => {
                    setEditingLineDraft((current) =>
                      current
                        ? {
                            ...current,
                            supplierArticleCode: event.currentTarget.value,
                          }
                        : current
                    )
                    setEditingLineErrors((current) => ({
                      ...current,
                      supplierArticleCode: undefined,
                    }))
                  }}
                  error={editingLineErrors.supplierArticleCode}
                />
                <NumberInput
                  label="Količina"
                  min={0}
                  step={getQuantityStep(editingLineDraft.uom)}
                  decimalScale={getQuantityScale(editingLineDraft.uom)}
                  value={editingLineDraft.orderedQty}
                  onChange={(value) => {
                    setEditingLineDraft((current) =>
                      current
                        ? {
                            ...current,
                            orderedQty: value,
                          }
                        : current
                    )
                    setEditingLineErrors((current) => ({
                      ...current,
                      orderedQty: undefined,
                    }))
                  }}
                  error={editingLineErrors.orderedQty}
                />
                <TextInput label="JM" value={editingLineDraft.uom} readOnly />
                <NumberInput
                  label="Jedinična cijena"
                  min={0}
                  step={0.01}
                  decimalScale={4}
                  value={editingLineDraft.unitPrice}
                  onChange={(value) => {
                    setEditingLineDraft((current) =>
                      current
                        ? {
                            ...current,
                            unitPrice: value,
                          }
                        : current
                    )
                    setEditingLineErrors((current) => ({
                      ...current,
                      unitPrice: undefined,
                    }))
                  }}
                  error={editingLineErrors.unitPrice}
                />
                <TextInput
                  label="Datum isporuke"
                  type="date"
                  value={editingLineDraft.deliveryDate}
                  onChange={(event) =>
                    setEditingLineDraft((current) =>
                      current
                        ? {
                            ...current,
                            deliveryDate: event.currentTarget.value,
                          }
                        : current
                    )
                  }
                />
              </Group>

              <Textarea
                label="Napomena stavke"
                autosize
                minRows={2}
                value={editingLineDraft.note}
                onChange={(event) => {
                  setEditingLineDraft((current) =>
                    current
                      ? {
                          ...current,
                          note: event.currentTarget.value,
                        }
                      : current
                  )
                  setEditingLineErrors((current) => ({
                    ...current,
                    note: undefined,
                  }))
                }}
                error={editingLineErrors.note}
              />

              {editingLineErrors.line ? (
                <Text size="sm" c="red">
                  {editingLineErrors.line}
                </Text>
              ) : null}

              <Group justify="flex-end">
                <Button type="button" variant="subtle" color="gray" onClick={resetInlineForms}>
                  Odustani
                </Button>
                <Button type="submit" loading={lineSubmittingId === editingLineId}>
                  Spremi stavku
                </Button>
              </Group>
            </Stack>
          </form>
        </Paper>
      ) : null}

      <Paper withBorder radius="lg" p="lg">
        <Stack gap="md">
          <Title order={3}>Stavke narudžbenice</Title>

          {order.lines.length === 0 ? (
            <Text c="dimmed">Nema stavki.</Text>
          ) : (
            <ScrollArea>
              <Table withTableBorder verticalSpacing="sm" striped>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Poz.</Table.Th>
                    <Table.Th>Artikl</Table.Th>
                    <Table.Th>Opis</Table.Th>
                    <Table.Th>Šifra dobavljača</Table.Th>
                    <Table.Th>Naručeno</Table.Th>
                    <Table.Th>Zaprimljeno</Table.Th>
                    <Table.Th>JM</Table.Th>
                    <Table.Th>Jed. cijena</Table.Th>
                    <Table.Th>Ukupno</Table.Th>
                    <Table.Th>Datum isporuke</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Akcije</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {order.lines.map((line) => {
                    const canEditLine = canMutate && line.status === 'OPEN'

                    return (
                      <Table.Tr key={line.id} style={line.status === 'REMOVED' ? { opacity: 0.6 } : undefined}>
                        <Table.Td>{line.position}</Table.Td>
                        <Table.Td>{line.article_no ?? '—'}</Table.Td>
                        <Table.Td>
                          <Stack gap={2}>
                            <Text size="sm">{line.description ?? '—'}</Text>
                            {line.note ? (
                              <Text size="xs" c="dimmed">
                                {line.note}
                              </Text>
                            ) : null}
                          </Stack>
                        </Table.Td>
                        <Table.Td>{line.supplier_article_code ?? '—'}</Table.Td>
                        <Table.Td>{formatQuantity(line.ordered_qty, line.uom)}</Table.Td>
                        <Table.Td>{formatQuantity(line.received_qty, line.uom)}</Table.Td>
                        <Table.Td>{line.uom}</Table.Td>
                        <Table.Td>{line.unit_price === null ? '—' : formatMoney(line.unit_price)}</Table.Td>
                        <Table.Td>{formatMoney(line.total_price)}</Table.Td>
                        <Table.Td>{formatDate(line.delivery_date)}</Table.Td>
                        <Table.Td>
                          <Badge color={getOrderLineStatusColor(line.status)} variant="light">
                            {getOrderLineStatusLabel(line.status)}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          {canEditLine ? (
                            <Group gap="xs" wrap="nowrap">
                              <ActionIcon
                                variant="light"
                                color="blue"
                                aria-label={`Uredi stavku ${line.position}`}
                                onClick={() => handleStartLineEdit(line)}
                                loading={lineSubmittingId === line.id && editingLineId === line.id}
                              >
                                <IconPencil size={16} />
                              </ActionIcon>
                              <ActionIcon
                                variant="light"
                                color="red"
                                aria-label={`Ukloni stavku ${line.position}`}
                                onClick={() => void handleRemoveLine(line)}
                                loading={lineSubmittingId === line.id && editingLineId !== line.id}
                              >
                                <IconTrash size={16} />
                              </ActionIcon>
                            </Group>
                          ) : (
                            <Text c="dimmed" size="sm">
                              —
                            </Text>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    )
                  })}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          )}
        </Stack>
      </Paper>
    </Stack>
  )
}
