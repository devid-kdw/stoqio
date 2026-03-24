import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Checkbox,
  Group,
  Loader,
  Modal,
  Pagination,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'

import {
  articlesApi,
  type ArticleCategoryLookupItem,
  type SupplierLookupItem,
  type ArticleUomLookupItem,
  type WarehouseArticleListItem,
} from '../../api/articles'
import FullPageState from '../../components/shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import {
  getApiErrorBody,
  isNetworkOrServerError,
  runWithRetry,
} from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import WarehouseArticleForm from './WarehouseArticleForm'
import {
  buildArticlePayload,
  buildUomMap,
  createArticleFormState,
  formatOptionalQuantity,
  formatQuantity,
  getReorderStatusColor,
  getReorderStatusLabel,
  getReorderStatusTint,
  mapArticleApiErrorToFormErrors,
  translateArticleApiMessage,
  validateArticleForm,
  type WarehouseArticleFormErrors,
  type WarehouseArticleFormState,
} from './warehouseUtils'

const PAGE_SIZE = 50
const WAREHOUSE_CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'

function ReorderIndicator({ status }: { status: WarehouseArticleListItem['reorder_status'] }) {
  return (
    <Group gap={8} wrap="nowrap">
      <span
        aria-hidden="true"
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: getReorderStatusColor(status),
          display: 'inline-block',
        }}
      />
      <Text size="sm" c="dimmed">
        {getReorderStatusLabel(status)}
      </Text>
    </Group>
  )
}

export default function WarehousePage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN'

  const [articles, setArticles] = useState<WarehouseArticleListItem[]>([])
  const [categories, setCategories] = useState<ArticleCategoryLookupItem[]>([])
  const [uoms, setUoms] = useState<ArticleUomLookupItem[]>([])
  const [supplierOptions, setSupplierOptions] = useState<SupplierLookupItem[]>([])
  const [supplierOptionsLoading, setSupplierOptionsLoading] = useState(false)
  const [supplierOptionsError, setSupplierOptionsError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [searchInput, setSearchInput] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [listLoading, setListLoading] = useState(false)
  const [fatalError, setFatalError] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)

  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<WarehouseArticleFormState>(createArticleFormState())
  const [createErrors, setCreateErrors] = useState<WarehouseArticleFormErrors>({})
  const [createSubmitting, setCreateSubmitting] = useState(false)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const initialLoadDoneRef = useRef(false)
  const supplierOptionsLoadedRef = useRef(false)
  const uomMap = useMemo(() => buildUomMap(uoms), [uoms])

  const loadInitialData = useCallback(async () => {
    setPageLoading(true)
    setPageError(null)
    setFatalError(false)

    try {
      const [categoriesResponse, uomsResponse, listResponse] = await runWithRetry(() =>
        Promise.all([
          articlesApi.lookupCategories(),
          articlesApi.lookupUoms(),
          articlesApi.listWarehouse({
            page,
            perPage: PAGE_SIZE,
            q: debouncedQuery || undefined,
            category: selectedCategory,
            includeInactive: showInactive,
          }),
        ])
      )

      setCategories(categoriesResponse)
      setUoms(uomsResponse)
      setArticles(listResponse.items)
      setTotal(listResponse.total)
      initialLoadDoneRef.current = true
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setPageError(
        translateArticleApiMessage(getApiErrorBody(error), 'Skladište se ne može učitati.')
      )
    } finally {
      setPageLoading(false)
    }
  }, [debouncedQuery, page, selectedCategory, showInactive])

  const loadArticles = useCallback(async () => {
    if (!initialLoadDoneRef.current) {
      return
    }

    setListLoading(true)
    setPageError(null)
    setFatalError(false)

    try {
      const response = await runWithRetry(() =>
        articlesApi.listWarehouse({
          page,
          perPage: PAGE_SIZE,
          q: debouncedQuery || undefined,
          category: selectedCategory,
          includeInactive: showInactive,
        })
      )
      setArticles(response.items)
      setTotal(response.total)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setPageError(
        translateArticleApiMessage(getApiErrorBody(error), 'Popis artikala nije dostupan.')
      )
    } finally {
      setListLoading(false)
    }
  }, [debouncedQuery, page, selectedCategory, showInactive])

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(searchInput.trim())
      setPage(1)
    }, 300)

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [searchInput])

  useEffect(() => {
    if (!initialLoadDoneRef.current) {
      void loadInitialData()
      return
    }

    void loadArticles()
  }, [debouncedQuery, loadArticles, loadInitialData, page, selectedCategory, showInactive])

  const resetCreateForm = useCallback(() => {
    setCreateForm(createArticleFormState())
    setCreateErrors({})
  }, [])

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

  const handleOpenCreate = useCallback(() => {
    resetCreateForm()
    setCreateOpen(true)
    void ensureSupplierOptionsLoaded()
  }, [ensureSupplierOptionsLoaded, resetCreateForm])

  const handleCloseCreate = useCallback(() => {
    setCreateOpen(false)
    resetCreateForm()
  }, [resetCreateForm])

  const handleCreateFieldChange = useCallback(
    <K extends keyof WarehouseArticleFormState>(field: K, value: WarehouseArticleFormState[K]) => {
      setCreateForm((current) => ({
        ...current,
        [field]: value,
      }))
      setCreateErrors({})
    },
    []
  )

  const handleCreateSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()

      const validationErrors = validateArticleForm(createForm)
      if (Object.keys(validationErrors).length > 0) {
        setCreateErrors(validationErrors)
        return
      }

      setCreateSubmitting(true)

      try {
        await runWithRetry(() => articlesApi.create(buildArticlePayload(createForm)))
        showSuccessToast('Artikl je kreiran.')
        handleCloseCreate()
        navigate('/warehouse')
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        const apiError = getApiErrorBody(error)
        const fieldErrors = mapArticleApiErrorToFormErrors(apiError)

        if (Object.keys(fieldErrors).length > 0) {
          setCreateErrors(fieldErrors)
        } else {
          showErrorToast(
            translateArticleApiMessage(apiError, 'Spremanje artikla nije uspjelo.')
          )
        }
      } finally {
        setCreateSubmitting(false)
      }
    },
    [createForm, handleCloseCreate, navigate]
  )

  const handleRetry = useCallback(() => {
    if (!initialLoadDoneRef.current) {
      void loadInitialData()
      return
    }

    void loadArticles()
  }, [loadArticles, loadInitialData])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

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

  if (pageError) {
    return (
      <FullPageState
        title="Skladište se ne može učitati."
        message={pageError}
        actionLabel="Pokušaj ponovno"
        onAction={handleRetry}
      />
    )
  }

  return (
    <>
      <Modal
        opened={createOpen}
        onClose={handleCloseCreate}
        title="Novi artikl"
        size="xl"
        closeOnClickOutside={!createSubmitting}
        closeOnEscape={!createSubmitting}
      >
        <form onSubmit={handleCreateSubmit}>
          <Stack gap="lg">
            <WarehouseArticleForm
              form={createForm}
              errors={createErrors}
              categories={categories}
              uoms={uoms}
              supplierOptions={supplierOptions}
              supplierOptionsLoading={supplierOptionsLoading}
              supplierOptionsError={supplierOptionsError}
              disabled={createSubmitting}
              onRetrySuppliers={() => void loadSupplierOptions()}
              onChange={handleCreateFieldChange}
            />

            <Group justify="flex-end">
              <Button variant="default" onClick={handleCloseCreate} disabled={createSubmitting}>
                Odustani
              </Button>
              <Button type="submit" loading={createSubmitting}>
                Spremi artikl
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Stack gap="lg">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>Skladište</Title>
            <Text c="dimmed" mt={4}>
              Pregled artikala, zaliha, viškova i pragova naručivanja.
            </Text>
          </div>

          {isAdmin ? <Button onClick={handleOpenCreate}>Novi artikl</Button> : null}
        </Group>

        <Paper withBorder radius="lg" p="lg">
          <Stack gap="md">
            <Group align="flex-end" grow>
              <TextInput
                label="Pretraga"
                placeholder="Broj artikla ili opis"
                value={searchInput}
                onChange={(event) => setSearchInput(event.currentTarget.value)}
              />

              <Select
                label="Kategorija"
                placeholder="Sve kategorije"
                clearable
                searchable
                nothingFoundMessage="Nema rezultata."
                data={categories.map((category) => ({
                  value: category.key,
                  label: category.label_hr,
                }))}
                value={selectedCategory}
                onChange={(value) => {
                  setSelectedCategory(value)
                  setPage(1)
                }}
              />

              <Checkbox
                label="Prikaži deaktivirane"
                checked={showInactive}
                onChange={(event) => {
                  setShowInactive(event.currentTarget.checked)
                  setPage(1)
                }}
                mb={6}
              />
            </Group>

            {listLoading ? (
              <Group gap="xs">
                <Loader size="xs" />
                <Text size="sm" c="dimmed">
                  Osvježavanje popisa…
                </Text>
              </Group>
            ) : null}

            {articles.length === 0 ? (
              <Text c="dimmed" ta="center" py="xl">
                Nema pronađenih artikala.
              </Text>
            ) : (
              <ScrollArea>
                <Table highlightOnHover withTableBorder verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Broj artikla</Table.Th>
                      <Table.Th>Opis</Table.Th>
                      <Table.Th>Kategorija</Table.Th>
                      <Table.Th>Zaliha</Table.Th>
                      <Table.Th>Višak</Table.Th>
                      <Table.Th>Prag</Table.Th>
                      <Table.Th>Status</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {articles.map((article) => (
                      <Table.Tr
                        key={article.id}
                        onClick={() => navigate(`/warehouse/articles/${article.id}`)}
                        style={{
                          cursor: 'pointer',
                          opacity: article.is_active ? 1 : 0.58,
                          background: article.is_active
                            ? getReorderStatusTint(article.reorder_status)
                            : 'rgba(173, 181, 189, 0.08)',
                        }}
                      >
                        <Table.Td>
                          <Stack gap={4}>
                            <Text fw={600}>{article.article_no}</Text>
                            {!article.is_active ? (
                              <Text size="xs" c="dimmed">
                                Deaktiviran
                              </Text>
                            ) : null}
                          </Stack>
                        </Table.Td>
                        <Table.Td>{article.description}</Table.Td>
                        <Table.Td>{article.category_label_hr ?? '—'}</Table.Td>
                        <Table.Td>{formatQuantity(article.stock_total, article.base_uom, uomMap)}</Table.Td>
                        <Table.Td>
                          {formatOptionalQuantity(article.surplus_total, article.base_uom, uomMap)}
                        </Table.Td>
                        <Table.Td>
                          {article.reorder_threshold === null
                            ? '—'
                            : formatQuantity(article.reorder_threshold, article.base_uom, uomMap)}
                        </Table.Td>
                        <Table.Td>
                          <ReorderIndicator status={article.reorder_status} />
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            )}

            {articles.length > 0 && totalPages > 1 ? (
              <Group justify="space-between" align="center">
                <Text size="sm" c="dimmed">
                  Ukupno artikala: {total}
                </Text>
                <Pagination value={page} onChange={setPage} total={totalPages} />
              </Group>
            ) : null}
          </Stack>
        </Paper>
      </Stack>
    </>
  )
}
