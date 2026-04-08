import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
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

import {
  ordersApi,
  type CreateOrderPayload,
  type OrdersListItem,
  type OrderSupplierLookupItem,
} from '../../api/orders'
import FullPageState from '../../components/shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import { getApiErrorBody, CONNECTION_ERROR_MESSAGE, isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import {
  createEmptyOrderLineDraft,
  findArticleOption,
  formatDateTime,
  formatMoney,
  getArticleSelectData,
  getOrderStatusColor,
  getOrderStatusLabel,
  getQuantityScale,
  getQuantityStep,
  normalizeOptionalText,
  type OrderLineDraft,
  type OrderLineFormErrors,
} from './orderUtils'

interface CreateHeaderErrors {
  orderNumber?: string
  supplierId?: string
  supplierConfirmationNumber?: string
  note?: string
  lines?: string
}

function buildSupplierSelectData(
  options: OrderSupplierLookupItem[],
  selectedSupplier: OrderSupplierLookupItem | null
): Array<{ value: string; label: string }> {
  const seen = new Set<number>()
  const items = [selectedSupplier, ...options].filter(
    (supplier): supplier is OrderSupplierLookupItem => supplier !== null
  )

  return items.reduce<Array<{ value: string; label: string }>>((acc, supplier) => {
    if (seen.has(supplier.id)) {
      return acc
    }

    seen.add(supplier.id)
    acc.push({
      value: String(supplier.id),
      label: `${supplier.name} (${supplier.internal_code})`,
    })
    return acc
  }, [])
}

function OrdersTableSection({
  title,
  items,
  muted,
  onSelect,
}: {
  title: string
  items: OrdersListItem[]
  muted?: boolean
  onSelect: (orderId: number) => void
}) {
  if (items.length === 0) {
    return null
  }

  return (
    <Paper
      withBorder
      radius="lg"
      p="lg"
      style={{
        opacity: muted ? 0.66 : 1,
        background: muted
          ? 'linear-gradient(180deg, rgba(248, 249, 250, 1) 0%, rgba(244, 246, 248, 1) 100%)'
          : 'linear-gradient(180deg, rgba(250, 252, 255, 1) 0%, rgba(244, 248, 251, 1) 100%)',
      }}
    >
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={3}>{title}</Title>
          <Text size="sm" c="dimmed">
            {items.length}
          </Text>
        </Group>

        <ScrollArea>
          <Table striped highlightOnHover withTableBorder verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Broj</Table.Th>
                <Table.Th>Dobavljač</Table.Th>
                <Table.Th>Datum</Table.Th>
                <Table.Th>Stavke</Table.Th>
                <Table.Th>Ukupna vrijednost</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((order) => (
                <Table.Tr
                  key={order.id}
                  onClick={() => onSelect(order.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <Table.Td>
                    <Text fw={600}>{order.order_number}</Text>
                  </Table.Td>
                  <Table.Td>{order.supplier_name ?? '—'}</Table.Td>
                  <Table.Td>{formatDateTime(order.created_at)}</Table.Td>
                  <Table.Td>{order.line_count}</Table.Td>
                  <Table.Td>{formatMoney(order.total_value)}</Table.Td>
                  <Table.Td>
                    <Badge color={getOrderStatusColor(order.status)} variant="light">
                      {getOrderStatusLabel(order.status)}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      </Stack>
    </Paper>
  )
}

export default function OrdersPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN'

  const [orders, setOrders] = useState<OrdersListItem[]>([])
  const [pageLoading, setPageLoading] = useState(true)
  const [fatalError, setFatalError] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [orderNumber, setOrderNumber] = useState('')
  const [selectedSupplierId, setSelectedSupplierId] = useState<string | null>(null)
  const [selectedSupplier, setSelectedSupplier] = useState<OrderSupplierLookupItem | null>(null)
  const [supplierOptions, setSupplierOptions] = useState<OrderSupplierLookupItem[]>([])
  const [supplierQuery, setSupplierQuery] = useState('')
  const [supplierConfirmationNumber, setSupplierConfirmationNumber] = useState('')
  const [note, setNote] = useState('')
  const [lineDrafts, setLineDrafts] = useState<OrderLineDraft[]>([createEmptyOrderLineDraft()])
  const [headerErrors, setHeaderErrors] = useState<CreateHeaderErrors>({})
  const [lineErrors, setLineErrors] = useState<Record<string, OrderLineFormErrors>>({})
  const [submitting, setSubmitting] = useState(false)

  const articleLookupTimersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  const loadOrders = useCallback(async () => {
    setPageLoading(true)
    setPageError(null)
    setFatalError(false)

    try {
      const data = await runWithRetry(() => ordersApi.list(1, 50))
      setOrders(data.items)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setPageError(getApiErrorBody(error)?.message ?? 'Učitavanje narudžbenica nije uspjelo.')
    } finally {
      setPageLoading(false)
    }
  }, [])

  const loadSupplierOptions = useCallback(async () => {
    try {
      const response = await runWithRetry(() => ordersApi.preloadSuppliers())
      setSupplierOptions(response.items)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      showErrorToast(getApiErrorBody(error)?.message ?? 'Dohvat dobavljača nije uspio.')
    }
  }, [])

  useEffect(() => {
    void loadOrders()
    void loadSupplierOptions()
  }, [loadOrders, loadSupplierOptions])

  useEffect(() => {
    const articleLookupTimers = articleLookupTimersRef.current

    return () => {
      Object.values(articleLookupTimers).forEach((timer) => clearTimeout(timer))
    }
  }, [])

  const resetCreateForm = useCallback(() => {
    setOrderNumber('')
    setSelectedSupplierId(null)
    setSelectedSupplier(null)
    setSupplierQuery('')
    setSupplierConfirmationNumber('')
    setNote('')
    setLineDrafts([createEmptyOrderLineDraft()])
    setHeaderErrors({})
    setLineErrors({})
  }, [])

  const handleCloseCreateForm = useCallback(() => {
    setShowCreateForm(false)
    resetCreateForm()
  }, [resetCreateForm])

  const updateLineDraft = useCallback(
    (lineKey: string, updater: (line: OrderLineDraft) => OrderLineDraft) => {
      setLineDrafts((current) =>
        current.map((line) => (line.key === lineKey ? updater(line) : line))
      )
    },
    []
  )

  const setLineFieldError = useCallback(
    (lineKey: string, field: keyof OrderLineFormErrors, value: string | undefined) => {
      setLineErrors((current) => ({
        ...current,
        [lineKey]: {
          ...current[lineKey],
          [field]: value,
        },
      }))
    },
    []
  )

  const handleSupplierChange = useCallback(
    (value: string | null) => {
      setSelectedSupplierId(value)
      setHeaderErrors((current) => ({ ...current, supplierId: undefined }))

      if (!value) {
        setSelectedSupplier(null)
        return
      }

      const numericValue = Number(value)
      const nextSupplier =
        [selectedSupplier, ...supplierOptions]
          .filter((supplier): supplier is OrderSupplierLookupItem => supplier !== null)
          .find((supplier) => supplier.id === numericValue) ?? null

      setSelectedSupplier(nextSupplier)
    },
    [selectedSupplier, supplierOptions]
  )

  const handleArticleSearch = useCallback(
    (lineKey: string, query: string) => {
      const existingTimer = articleLookupTimersRef.current[lineKey]
      if (existingTimer) {
        clearTimeout(existingTimer)
      }

      const normalized = query.trim()
      if (!normalized) {
        updateLineDraft(lineKey, (line) => ({
          ...line,
          articleOptions: [],
          articleLookupState: line.selectedArticle ? 'found' : 'idle',
        }))
        return
      }

      updateLineDraft(lineKey, (line) => ({
        ...line,
        articleLookupState: 'loading',
      }))

      articleLookupTimersRef.current[lineKey] = setTimeout(async () => {
        try {
          const response = await runWithRetry(() =>
            ordersApi.lookupArticles(normalized, selectedSupplierId ? Number(selectedSupplierId) : undefined)
          )
          updateLineDraft(lineKey, (line) => ({
            ...line,
            articleOptions: response.items,
            articleLookupState: response.items.length > 0 ? 'found' : 'not-found',
          }))
        } catch (error) {
          if (isNetworkOrServerError(error)) {
            setFatalError(true)
            return
          }

          updateLineDraft(lineKey, (line) => ({
            ...line,
            articleLookupState: 'not-found',
          }))
          showErrorToast(getApiErrorBody(error)?.message ?? 'Dohvat artikala nije uspio.')
        }
      }, 300)
    },
    [selectedSupplierId, updateLineDraft]
  )

  const handleArticleChange = useCallback(
    (lineKey: string, value: string | null) => {
      updateLineDraft(lineKey, (line) => {
        const selectedArticle = findArticleOption(line, value)

        if (!selectedArticle) {
          return {
            ...line,
            articleId: null,
            selectedArticle: null,
            supplierArticleCode: '',
            uom: '',
            unitPrice: '',
            articleLookupState: 'idle',
          }
        }

        return {
          ...line,
          articleId: selectedArticle.article_id,
          selectedArticle,
          supplierArticleCode: selectedArticle.supplier_article_code ?? '',
          uom: selectedArticle.uom ?? '',
          unitPrice: selectedArticle.last_price ?? '',
          articleLookupState: 'found',
        }
      })

      setLineErrors((current) => ({
        ...current,
        [lineKey]: {
          ...current[lineKey],
          article: undefined,
          supplierArticleCode: undefined,
        },
      }))
    },
    [updateLineDraft]
  )

  const validateCreateForm = useCallback(() => {
    const nextHeaderErrors: CreateHeaderErrors = {}
    const nextLineErrors: Record<string, OrderLineFormErrors> = {}

    if (orderNumber.trim().length > 100) {
      nextHeaderErrors.orderNumber = 'Broj narudžbenice može imati najviše 100 znakova.'
    }

    if (!selectedSupplierId) {
      nextHeaderErrors.supplierId = 'Dobavljač je obavezan.'
    }

    if (supplierConfirmationNumber.trim().length > 255) {
      nextHeaderErrors.supplierConfirmationNumber =
        'Broj potvrde dobavljača može imati najviše 255 znakova.'
    }

    if (note.trim().length > 1000) {
      nextHeaderErrors.note = 'Napomena može imati najviše 1000 znakova.'
    }

    if (lineDrafts.length === 0) {
      nextHeaderErrors.lines = 'Dodaj barem jednu stavku.'
    }

    lineDrafts.forEach((line) => {
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

      if (Object.keys(errors).length > 0) {
        nextLineErrors[line.key] = errors
      }
    })

    return { nextHeaderErrors, nextLineErrors }
  }, [lineDrafts, note, orderNumber, selectedSupplierId, supplierConfirmationNumber])

  const handleCreateOrder = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const { nextHeaderErrors, nextLineErrors } = validateCreateForm()
    setHeaderErrors(nextHeaderErrors)
    setLineErrors(nextLineErrors)

    if (Object.keys(nextHeaderErrors).length > 0 || Object.keys(nextLineErrors).length > 0) {
      return
    }

    setSubmitting(true)

    const payload: CreateOrderPayload = {
      order_number: normalizeOptionalText(orderNumber),
      supplier_id: Number(selectedSupplierId),
      supplier_confirmation_number: normalizeOptionalText(supplierConfirmationNumber),
      note: normalizeOptionalText(note),
      lines: lineDrafts.map((line) => ({
        article_id: line.articleId!,
        supplier_article_code: normalizeOptionalText(line.supplierArticleCode),
        ordered_qty:
          typeof line.orderedQty === 'string' ? Number.parseFloat(line.orderedQty) : line.orderedQty,
        uom: line.uom,
        unit_price:
          typeof line.unitPrice === 'string' ? Number.parseFloat(line.unitPrice) : line.unitPrice,
        delivery_date: normalizeOptionalText(line.deliveryDate),
        note: normalizeOptionalText(line.note),
      })),
    }

    try {
      const response = await ordersApi.create(payload)
      showSuccessToast('Narudžbenica je kreirana.')
      navigate(`/orders/${response.id}`)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      const apiError = getApiErrorBody(error)
      const lineIndex = apiError?.details?.line_index

      if (apiError?.error === 'ORDER_NUMBER_EXISTS') {
        setHeaderErrors((current) => ({
          ...current,
          orderNumber: apiError.message ?? 'Broj narudžbenice već postoji.',
        }))
      } else if (typeof lineIndex === 'number' && lineDrafts[lineIndex]) {
        setLineFieldError(
          lineDrafts[lineIndex].key,
          'line',
          apiError?.message ?? 'Spremanje stavke nije uspjelo.'
        )
      } else {
        showErrorToast(apiError?.message ?? 'Spremanje narudžbenice nije uspjelo.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const openOrders = orders.filter((order) => order.status === 'OPEN')
  const closedOrders = orders.filter((order) => order.status !== 'OPEN')

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
        title="Narudžbenice se ne mogu učitati."
        message={pageError}
        actionLabel="Pokušaj ponovno"
        onAction={() => void loadOrders()}
      />
    )
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>Narudžbenice</Title>
          <Text c="dimmed" mt={4}>
            Pregled otvorenih i zatvorenih narudžbenica po dobavljaču.
          </Text>
        </div>

        {isAdmin ? (
          <Button
            onClick={() => {
              if (showCreateForm) {
                handleCloseCreateForm()
                return
              }

              setShowCreateForm(true)
            }}
          >
            {showCreateForm ? 'Zatvori obrazac' : 'Nova narudžbenica'}
          </Button>
        ) : null}
      </Group>

      {showCreateForm && isAdmin ? (
        <Paper withBorder radius="lg" p="lg">
          <form onSubmit={handleCreateOrder}>
            <Stack gap="lg">
              <Group justify="space-between" align="flex-start">
                <div>
                  <Title order={3}>Nova narudžbenica</Title>
                  <Text size="sm" c="dimmed" mt={4}>
                    Ručni broj je opcionalan. Ako ga ne uneseš, sustav će ga generirati.
                  </Text>
                </div>
                <Button type="button" variant="subtle" color="gray" onClick={handleCloseCreateForm}>
                  Odustani
                </Button>
              </Group>

              <Group grow align="flex-start">
                <TextInput
                  label="Broj narudžbenice"
                  value={orderNumber}
                  onChange={(event) => {
                    setOrderNumber(event.currentTarget.value)
                    setHeaderErrors((current) => ({ ...current, orderNumber: undefined }))
                  }}
                  error={headerErrors.orderNumber}
                />
                <Select
                  label="Dobavljač"
                  placeholder="Pretraži dobavljače"
                  searchable
                  clearable
                  value={selectedSupplierId}
                  data={buildSupplierSelectData(supplierOptions, selectedSupplier)}
                  onSearchChange={setSupplierQuery}
                  onChange={handleSupplierChange}
                  error={headerErrors.supplierId}
                  nothingFoundMessage={supplierQuery.trim() ? 'Nema rezultata.' : undefined}
                  filter={({ options, search }) => {
                    const q = search.trim().toLowerCase()
                    if (!q) return options
                    return options.filter(
                      (opt) =>
                        'value' in opt &&
                        opt.label?.toLowerCase().includes(q)
                    )
                  }}
                  maxDropdownHeight={260}
                />
              </Group>

              <Group grow align="flex-start">
                <TextInput
                  label="Broj potvrde dobavljača"
                  value={supplierConfirmationNumber}
                  onChange={(event) => {
                    setSupplierConfirmationNumber(event.currentTarget.value)
                    setHeaderErrors((current) => ({
                      ...current,
                      supplierConfirmationNumber: undefined,
                    }))
                  }}
                  error={headerErrors.supplierConfirmationNumber}
                />
                <Textarea
                  label="Napomena"
                  value={note}
                  autosize
                  minRows={2}
                  onChange={(event) => {
                    setNote(event.currentTarget.value)
                    setHeaderErrors((current) => ({ ...current, note: undefined }))
                  }}
                  error={headerErrors.note}
                />
              </Group>

              <Stack gap="md">
                <Group justify="space-between">
                  <div>
                    <Title order={4}>Stavke</Title>
                    <Text size="sm" c="dimmed">
                      Dodaj jednu ili više stavki prije spremanja.
                    </Text>
                  </div>
                  <Button
                    type="button"
                    variant="light"
                    onClick={() => setLineDrafts((current) => [...current, createEmptyOrderLineDraft()])}
                  >
                    Dodaj stavku
                  </Button>
                </Group>

                {headerErrors.lines ? (
                  <Text c="red" size="sm">
                    {headerErrors.lines}
                  </Text>
                ) : null}

                {lineDrafts.map((line, index) => (
                  <Paper key={line.key} withBorder radius="md" p="md">
                    <Stack gap="md">
                      <Group justify="space-between" align="flex-start">
                        <div>
                          <Text fw={600}>Stavka {index + 1}</Text>
                          {line.selectedArticle ? (
                            <Text size="sm" c="dimmed" mt={4}>
                              {line.selectedArticle.article_no} • {line.selectedArticle.description}
                            </Text>
                          ) : null}
                        </div>
                        <Button
                          type="button"
                          variant="subtle"
                          color="red"
                          disabled={lineDrafts.length === 1}
                          onClick={() => {
                            setLineDrafts((current) =>
                              current.filter((currentLine) => currentLine.key !== line.key)
                            )
                            setLineErrors((current) => {
                              const next = { ...current }
                              delete next[line.key]
                              return next
                            })
                          }}
                        >
                          Ukloni
                        </Button>
                      </Group>

                      <Group grow align="flex-start">
                        <Select
                          label="Artikl"
                          placeholder="Pretraži po broju ili opisu"
                          searchable
                          clearable
                          value={line.articleId ? String(line.articleId) : null}
                          data={getArticleSelectData(line)}
                          onSearchChange={(query) => handleArticleSearch(line.key, query)}
                          onChange={(value) => handleArticleChange(line.key, value)}
                          nothingFoundMessage="Nema rezultata."
                          error={lineErrors[line.key]?.article}
                          rightSection={
                            line.articleLookupState === 'loading' ? <Loader size={16} /> : null
                          }
                        />
                        <TextInput
                          label="Šifra artikla dobavljača"
                          value={line.supplierArticleCode}
                          onChange={(event) => {
                            updateLineDraft(line.key, (currentLine) => ({
                              ...currentLine,
                              supplierArticleCode: event.currentTarget.value,
                            }))
                            setLineFieldError(line.key, 'supplierArticleCode', undefined)
                          }}
                          error={lineErrors[line.key]?.supplierArticleCode}
                        />
                      </Group>

                      <Group grow align="flex-start">
                        <NumberInput
                          label="Količina"
                          min={0}
                          step={getQuantityStep(line.uom)}
                          decimalScale={getQuantityScale(line.uom)}
                          value={line.orderedQty}
                          onChange={(value) => {
                            updateLineDraft(line.key, (currentLine) => ({
                              ...currentLine,
                              orderedQty: value,
                            }))
                            setLineFieldError(line.key, 'orderedQty', undefined)
                          }}
                          error={lineErrors[line.key]?.orderedQty}
                        />
                        <TextInput label="JM" value={line.uom} readOnly placeholder="—" />
                        <NumberInput
                          label="Jedinična cijena"
                          min={0}
                          step={0.01}
                          decimalScale={4}
                          value={line.unitPrice}
                          onChange={(value) => {
                            updateLineDraft(line.key, (currentLine) => ({
                              ...currentLine,
                              unitPrice: value,
                            }))
                            setLineFieldError(line.key, 'unitPrice', undefined)
                          }}
                          error={lineErrors[line.key]?.unitPrice}
                        />
                        <TextInput
                          label="Datum isporuke"
                          type="date"
                          value={line.deliveryDate}
                          onChange={(event) =>
                            updateLineDraft(line.key, (currentLine) => ({
                              ...currentLine,
                              deliveryDate: event.currentTarget.value,
                            }))
                          }
                        />
                      </Group>

                      <Textarea
                        label="Napomena stavke"
                        autosize
                        minRows={2}
                        value={line.note}
                        onChange={(event) => {
                          updateLineDraft(line.key, (currentLine) => ({
                            ...currentLine,
                            note: event.currentTarget.value,
                          }))
                          setLineFieldError(line.key, 'note', undefined)
                        }}
                        error={lineErrors[line.key]?.note}
                      />

                      {lineErrors[line.key]?.line ? (
                        <Text size="sm" c="red">
                          {lineErrors[line.key]?.line}
                        </Text>
                      ) : null}
                    </Stack>
                  </Paper>
                ))}
              </Stack>

              <Group justify="flex-end">
                <Button type="submit" loading={submitting}>
                  Kreiraj narudžbenicu
                </Button>
              </Group>
            </Stack>
          </form>
        </Paper>
      ) : null}

      {pageLoading ? (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      ) : orders.length === 0 ? (
        <Paper withBorder radius="lg" p="xl">
          <Text ta="center" c="dimmed">
            Nema narudžbenica.
          </Text>
        </Paper>
      ) : (
        <Stack gap="lg">
          <OrdersTableSection
            title="Otvorene narudžbenice"
            items={openOrders}
            onSelect={(orderId) => navigate(`/orders/${orderId}`)}
          />
          <OrdersTableSection
            title="Zatvorene narudžbenice"
            items={closedOrders}
            muted
            onSelect={(orderId) => navigate(`/orders/${orderId}`)}
          />
        </Stack>
      )}
    </Stack>
  )
}
