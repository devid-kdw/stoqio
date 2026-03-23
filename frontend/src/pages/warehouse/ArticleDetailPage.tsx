import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Loader,
  Pagination,
  Paper,
  ScrollArea,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { IconX } from '@tabler/icons-react'

import {
  articlesApi,
  type ArticleAliasItem,
  type ArticleCategoryLookupItem,
  type SupplierLookupItem,
  type ArticleTransactionItem,
  type ArticleUomLookupItem,
  type WarehouseArticleDetail,
} from '../../api/articles'
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

  const [aliasInput, setAliasInput] = useState('')
  const [aliasSubmitting, setAliasSubmitting] = useState(false)
  const [aliasError, setAliasError] = useState<string | null>(null)
  const [aliasDeletingId, setAliasDeletingId] = useState<number | null>(null)

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
    [applyArticleState, articleId]
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
      const response = await runWithRetry(() => articlesApi.lookupSuppliers())
      setSupplierOptions(response)
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
          <Group>
            <Button variant="default" onClick={() => void handleBarcodePrint()} loading={barcodeSubmitting}>
              Ispis barkoda
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
                            <Button
                              size="xs"
                              variant="default"
                              onClick={() => void handleBatchBarcodePrint(batch.id, batch.batch_code)}
                              loading={batchBarcodeSubmittingId === batch.id}
                            >
                              Ispis barkoda
                            </Button>
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
