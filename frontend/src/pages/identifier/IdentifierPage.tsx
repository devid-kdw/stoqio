import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Divider,
  Group,
  Loader,
  Modal,
  Paper,
  ScrollArea,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Title,
  useMantineColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconAlertCircle,
  IconChecklist,
  IconSearch,
  IconSearchOff,
} from '@tabler/icons-react'

import {
  identifierApi,
  type IdentifierQueueStatusFilter,
  type IdentifierSearchItem,
  type MissingArticleReportItem,
} from '../../api/identifier'
import FullPageState from '../../components/shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import {
  getApiErrorBody,
  isNetworkOrServerError,
  runWithRetry,
} from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import {
  formatIdentifierDateTime,
  formatIdentifierPrice,
  formatIdentifierQuantity,
  getIdentifierReportStatusColor,
  getIdentifierReportStatusLabel,
  normalizeOptionalText,
  translateIdentifierApiMessage,
  validateMissingArticleReportTerm,
} from './identifierUtils'

const IDENTIFIER_CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'
const SEARCH_DEBOUNCE_MS = 300

type PageTab = 'search' | 'reports'

interface QueueState {
  items: MissingArticleReportItem[]
  total: number
  loading: boolean
  loaded: boolean
  error: string | null
}

const EMPTY_QUEUE_STATE: QueueState = {
  items: [],
  total: 0,
  loading: false,
  loaded: false,
  error: null,
}

function ResultMetaField({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={4}>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Text fw={500}>{value}</Text>
    </Stack>
  )
}

function isAvailabilityOnlyResult(
  item: IdentifierSearchItem
): item is Extract<IdentifierSearchItem, { in_stock: boolean }> {
  return 'in_stock' in item
}

function IdentifierResultCard({ item }: { item: IdentifierSearchItem }) {
  const theme = useMantineTheme()
  const { colorScheme } = useMantineColorScheme()
  const isDark = colorScheme === 'dark'

  return (
    <Paper
      withBorder
      radius="xl"
      p="lg"
      style={{
        background:
          isDark
            ? `linear-gradient(180deg, ${theme.colors.dark[6]} 0%, ${theme.colors.dark[7]} 100%)`
            : 'linear-gradient(180deg, rgba(250, 252, 255, 1) 0%, rgba(244, 248, 251, 1) 100%)',
      }}
    >
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Text size="sm" c="dimmed">
              Broj artikla
            </Text>
            <Title order={3}>{item.article_no}</Title>
          </div>

          {item.matched_via === 'alias' && item.matched_alias ? (
            <Badge color="blue" variant="light">
              Alias: {item.matched_alias}
            </Badge>
          ) : null}
        </Group>

        <div>
          <Text size="sm" c="dimmed" mb={4}>
            Opis
          </Text>
          <Text fw={500}>{item.description}</Text>
        </div>

        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="lg">
          <ResultMetaField label="Kategorija" value={item.category_label_hr ?? '—'} />
          <ResultMetaField label="JM" value={item.base_uom ?? '—'} />

          {isAvailabilityOnlyResult(item) ? (
            <>
              <ResultMetaField
                label="Dostupnost"
                value={item.in_stock ? 'Na stanju' : 'Nije na stanju'}
              />
              <ResultMetaField
                label="Naručeno"
                value={item.is_ordered ? 'Da' : 'Ne'}
              />
            </>
          ) : (
            <>
              <ResultMetaField
                label="Na stanju"
                value={formatIdentifierQuantity(
                  item.stock,
                  item.base_uom,
                  item.decimal_display
                )}
              />
              <ResultMetaField
                label="Naručeno"
                value={item.is_ordered ? 'Da' : 'Ne'}
              />
              <ResultMetaField
                label="Naručena količina"
                value={formatIdentifierQuantity(
                  item.ordered_quantity,
                  item.base_uom,
                  item.decimal_display
                )}
              />
              <ResultMetaField
                label="Zadnja nabavna cijena"
                value={formatIdentifierPrice(item.latest_purchase_price)}
              />
            </>
          )}
        </SimpleGrid>

        {item.matched_via === 'alias' && item.matched_alias ? (
          <>
            <Divider />
            <Text size="sm" c="dimmed">
              Pronađeno preko aliasa:{' '}
              <Text span c="inherit" fw={500}>
                {item.matched_alias}
              </Text>
            </Text>
          </>
        ) : null}
      </Stack>
    </Paper>
  )
}

export default function IdentifierPage() {
  const theme = useMantineTheme()
  const { colorScheme } = useMantineColorScheme()
  const isDark = colorScheme === 'dark'
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN'

  const [activeTab, setActiveTab] = useState<PageTab>('search')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [searchedQuery, setSearchedQuery] = useState('')
  const [searchResults, setSearchResults] = useState<IdentifierSearchItem[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [fatalError, setFatalError] = useState(false)

  const [reportModalOpen, setReportModalOpen] = useState(false)
  const [reportTerm, setReportTerm] = useState('')
  const [reportTermError, setReportTermError] = useState<string | null>(null)
  const [reportSubmitting, setReportSubmitting] = useState(false)

  const [reportStatusTab, setReportStatusTab] = useState<IdentifierQueueStatusFilter>('open')
  const [queueState, setQueueState] = useState<Record<IdentifierQueueStatusFilter, QueueState>>({
    open: { ...EMPTY_QUEUE_STATE },
    resolved: { ...EMPTY_QUEUE_STATE },
  })
  const [resolveModalOpen, setResolveModalOpen] = useState(false)
  const [reportToResolve, setReportToResolve] = useState<MissingArticleReportItem | null>(null)
  const [resolutionNote, setResolutionNote] = useState('')
  const [resolveSubmitting, setResolveSubmitting] = useState(false)

  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const searchRequestIdRef = useRef(0)

  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current)
    }

    searchDebounceRef.current = setTimeout(() => {
      setDebouncedQuery(searchInput.trim())
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current)
      }
    }
  }, [searchInput])

  useEffect(() => {
    const normalizedQuery = debouncedQuery.trim()
    const requestId = searchRequestIdRef.current + 1
    searchRequestIdRef.current = requestId

    if (normalizedQuery.length < 2) {
      setSearchResults([])
      setSearchedQuery('')
      setSearchError(null)
      setSearchLoading(false)
      return
    }

    setSearchLoading(true)
    setSearchError(null)

    void (async () => {
      try {
        const response = await runWithRetry(() => identifierApi.search(normalizedQuery))
        if (searchRequestIdRef.current !== requestId) {
          return
        }

        setSearchResults(response.items)
        setSearchedQuery(normalizedQuery)
      } catch (error) {
        if (searchRequestIdRef.current !== requestId) {
          return
        }

        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        setSearchResults([])
        setSearchedQuery(normalizedQuery)
        setSearchError(
          translateIdentifierApiMessage(getApiErrorBody(error), 'Pretraga nije dostupna.')
        )
      } finally {
        if (searchRequestIdRef.current === requestId) {
          setSearchLoading(false)
        }
      }
    })()
  }, [debouncedQuery])

  const loadReportQueue = useCallback(
    async (status: IdentifierQueueStatusFilter, options?: { force?: boolean }) => {
      const force = options?.force ?? false

      if (!force && (queueState[status].loaded || queueState[status].loading)) {
        return
      }

      setQueueState((current) => ({
        ...current,
        [status]: {
          ...current[status],
          loading: true,
          error: null,
        },
      }))

      try {
        const response = await runWithRetry(() => identifierApi.listReports(status))
        setQueueState((current) => ({
          ...current,
          [status]: {
            items: response.items,
            total: response.total,
            loading: false,
            loaded: true,
            error: null,
          },
        }))
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        setQueueState((current) => ({
          ...current,
          [status]: {
            ...current[status],
            loading: false,
            loaded: false,
            error: translateIdentifierApiMessage(
              getApiErrorBody(error),
              'Red prijava nije dostupan.'
            ),
          },
        }))
      }
    },
    [queueState]
  )

  useEffect(() => {
    if (!isAdmin || activeTab !== 'reports') {
      return
    }

    void loadReportQueue(reportStatusTab)
  }, [activeTab, isAdmin, loadReportQueue, reportStatusTab])

  const handleOpenReportModal = useCallback(() => {
    setReportTerm(searchedQuery)
    setReportTermError(null)
    setReportModalOpen(true)
  }, [searchedQuery])

  const handleCloseReportModal = useCallback(() => {
    if (reportSubmitting) {
      return
    }

    setReportModalOpen(false)
    setReportTermError(null)
  }, [reportSubmitting])

  const handleSubmitMissingReport = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()

      const validationError = validateMissingArticleReportTerm(reportTerm)
      if (validationError) {
        setReportTermError(validationError)
        return
      }

      const normalizedTerm = normalizeOptionalText(reportTerm)
      if (!normalizedTerm) {
        setReportTermError('Pojam pretrage je obavezan.')
        return
      }

      setReportSubmitting(true)

      try {
        await identifierApi.submitReport({
          search_term: normalizedTerm,
        })
        showSuccessToast('Prijava nedostajućeg artikla je poslana.')
        setReportModalOpen(false)
        setReportTermError(null)
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        const apiMessage = translateIdentifierApiMessage(
          getApiErrorBody(error),
          'Slanje prijave nije uspjelo.'
        )
        setReportTermError(apiMessage)
      } finally {
        setReportSubmitting(false)
      }
    },
    [reportTerm]
  )

  const openResolveModal = useCallback((report: MissingArticleReportItem) => {
    setReportToResolve(report)
    setResolutionNote(report.resolution_note ?? '')
    setResolveModalOpen(true)
  }, [])

  const closeResolveModal = useCallback(() => {
    if (resolveSubmitting) {
      return
    }

    setResolveModalOpen(false)
    setReportToResolve(null)
    setResolutionNote('')
  }, [resolveSubmitting])

  const handleResolveReport = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()

      if (!reportToResolve) {
        return
      }

      setResolveSubmitting(true)

      try {
        await identifierApi.resolveReport(reportToResolve.id, {
          resolution_note: normalizeOptionalText(resolutionNote),
        })
        showSuccessToast('Prijava je riješena.')
        closeResolveModal()
        await loadReportQueue('open', { force: true })
        if (queueState.resolved.loaded || reportStatusTab === 'resolved') {
          await loadReportQueue('resolved', { force: true })
        }
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        showErrorToast(
          translateIdentifierApiMessage(getApiErrorBody(error), 'Rješavanje prijave nije uspjelo.')
        )
      } finally {
        setResolveSubmitting(false)
      }
    },
    [closeResolveModal, loadReportQueue, queueState.resolved.loaded, reportStatusTab, reportToResolve, resolutionNote]
  )

  const currentQueueState = queueState[reportStatusTab]
  const shouldShowEmptyState =
    searchedQuery.length >= 2 &&
    !searchLoading &&
    !searchError &&
    searchResults.length === 0

  if (fatalError) {
    return (
      <FullPageState
        title="Greška pri povezivanju"
        message={IDENTIFIER_CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => window.location.reload()}
      />
    )
  }

  return (
    <>
      <Modal
        opened={reportModalOpen}
        onClose={handleCloseReportModal}
        title="Prijava nedostajućeg artikla"
        size="lg"
        closeOnClickOutside={!reportSubmitting}
        closeOnEscape={!reportSubmitting}
      >
        <form onSubmit={handleSubmitMissingReport}>
          <Stack gap="lg">
            <Text c="dimmed" size="sm">
              Unesite pojam koji tražite. Prijava se spaja s postojećom otvorenom prijavom ako je
              isti pojam već prijavljen.
            </Text>

            <TextInput
              label="Pojam pretrage"
              value={reportTerm}
              onChange={(event) => {
                setReportTerm(event.currentTarget.value)
                setReportTermError(null)
              }}
              error={reportTermError}
              disabled={reportSubmitting}
              autoFocus
              maxLength={255}
            />

            <Group justify="flex-end">
              <Button variant="default" onClick={handleCloseReportModal} disabled={reportSubmitting}>
                Odustani
              </Button>
              <Button type="submit" loading={reportSubmitting}>
                Pošalji prijavu
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal
        opened={resolveModalOpen}
        onClose={closeResolveModal}
        title="Riješi prijavu"
        size="lg"
        closeOnClickOutside={!resolveSubmitting}
        closeOnEscape={!resolveSubmitting}
      >
        <form onSubmit={handleResolveReport}>
          <Stack gap="lg">
            <Text c="dimmed" size="sm">
              {reportToResolve
                ? `Prijava za pojam "${reportToResolve.search_term}" bit će označena kao riješena.`
                : 'Prijava će biti označena kao riješena.'}
            </Text>

            <Textarea
              label="Napomena o rješenju"
              description="Nije obavezno"
              value={resolutionNote}
              onChange={(event) => setResolutionNote(event.currentTarget.value)}
              disabled={resolveSubmitting}
              minRows={4}
              maxLength={1000}
            />

            <Group justify="flex-end">
              <Button variant="default" onClick={closeResolveModal} disabled={resolveSubmitting}>
                Odustani
              </Button>
              <Button type="submit" loading={resolveSubmitting}>
                Riješi prijavu
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Stack gap="lg">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>Identifikator</Title>
            <Text c="dimmed" mt={4}>
              Brza pretraga artikala po broju, opisu, aliasu ili barkodu.
            </Text>
          </div>
        </Group>

        <Tabs
          value={activeTab}
          onChange={(value) => setActiveTab((value as PageTab | null) ?? 'search')}
        >
          <Tabs.List>
            <Tabs.Tab value="search" leftSection={<IconSearch size={16} />}>
              Pretraga
            </Tabs.Tab>
            {isAdmin ? (
              <Tabs.Tab value="reports" leftSection={<IconChecklist size={16} />}>
                Prijave
              </Tabs.Tab>
            ) : null}
          </Tabs.List>

          <Tabs.Panel value="search" pt="md">
            <Stack gap="lg">
              <Paper
                withBorder
                radius="xl"
                p="xl"
                style={{
                  background:
                    isDark
                      ? `linear-gradient(145deg, ${theme.colors.dark[6]} 0%, ${theme.colors.dark[7]} 100%)`
                      : 'linear-gradient(145deg, rgba(247, 251, 252, 1) 0%, rgba(239, 245, 247, 1) 100%)',
                }}
              >
                <Stack gap="md">
                  <div>
                    <Text size="sm" c="dimmed" fw={600} tt="uppercase">
                      Pretraga artikala
                    </Text>
                    <Title order={3} mt={6}>
                      Upišite najmanje 2 znaka
                    </Title>
                    <Text c="dimmed" mt={6}>
                      Rezultati se osvježavaju automatski dok tipkate.
                    </Text>
                  </div>

                  <TextInput
                    value={searchInput}
                    onChange={(event) => setSearchInput(event.currentTarget.value)}
                    placeholder="Broj artikla, opis, alias ili barkod"
                    size="xl"
                    autoFocus
                    leftSection={<IconSearch size={18} />}
                    styles={{
                      input: {
                        minHeight: 64,
                        fontSize: '1.1rem',
                        fontWeight: 500,
                      },
                    }}
                  />

                  <Text size="sm" c="dimmed">
                    Pretraga se ne šalje prije 2 unesena znaka.
                  </Text>
                </Stack>
              </Paper>

              {searchLoading ? (
                <Group gap="xs">
                  <Loader size="sm" />
                  <Text size="sm" c="dimmed">
                    Pretraživanje u tijeku…
                  </Text>
                </Group>
              ) : null}

              {searchError ? (
                <Alert color="red" icon={<IconAlertCircle size={16} />} title="Pretraga nije uspjela">
                  {searchError}
                </Alert>
              ) : null}

              {searchedQuery.length >= 2 && searchResults.length > 0 ? (
                <Group justify="space-between" align="center">
                  <Text size="sm" c="dimmed">
                    Pronađeno artikala: {searchResults.length}
                  </Text>
                  <Text size="sm" c="dimmed">
                    Upit: "{searchedQuery}"
                  </Text>
                </Group>
              ) : null}

              {searchedQuery.length >= 2 && searchLoading && searchResults.length === 0 ? (
                <Paper withBorder radius="xl" p="xl">
                  <Group justify="center" py="xl">
                    <Loader />
                  </Group>
                </Paper>
              ) : null}

              {searchedQuery.length >= 2 && searchResults.length > 0 ? (
                <Stack gap="md">
                  {searchResults.map((item) => (
                    <IdentifierResultCard key={item.id} item={item} />
                  ))}
                </Stack>
              ) : null}

              {shouldShowEmptyState ? (
                <Paper withBorder radius="xl" p="xl">
                  <Stack gap="md" align="center">
                    <IconSearchOff size={32} color="#868e96" />
                    <Text ta="center" size="lg" fw={500}>
                      Nema pronađenih artikala za '{searchedQuery}'.
                    </Text>
                    <Text ta="center" c="dimmed">
                      Ako pojam postoji u praksi, pošaljite prijavu kako bi ga ADMIN mogao povezati
                      s točnim artiklom.
                    </Text>
                    <Button onClick={handleOpenReportModal}>Prijavi nedostajući artikl</Button>
                  </Stack>
                </Paper>
              ) : null}
            </Stack>
          </Tabs.Panel>

          {isAdmin ? (
            <Tabs.Panel value="reports" pt="md">
              <Stack gap="lg">
                <Group justify="space-between" align="center">
                  <div>
                    <Title order={3}>Red prijava nedostajućih artikala</Title>
                    <Text c="dimmed" mt={4}>
                      ADMIN vidi otvorene i riješene prijave te može ručno zatvoriti otvorene stavke.
                    </Text>
                  </div>

                  <Button
                    variant="default"
                    onClick={() => void loadReportQueue(reportStatusTab, { force: true })}
                    loading={currentQueueState.loading}
                  >
                    Osvježi
                  </Button>
                </Group>

                <Tabs
                  value={reportStatusTab}
                  onChange={(value) =>
                    setReportStatusTab((value as IdentifierQueueStatusFilter | null) ?? 'open')
                  }
                >
                  <Tabs.List>
                    <Tabs.Tab value="open">Otvorene prijave</Tabs.Tab>
                    <Tabs.Tab value="resolved">Riješene prijave</Tabs.Tab>
                  </Tabs.List>

                  <Tabs.Panel value={reportStatusTab} pt="md">
                    {currentQueueState.error ? (
                      <Alert
                        color="red"
                        icon={<IconAlertCircle size={16} />}
                        title="Prijave nisu dostupne"
                      >
                        {currentQueueState.error}
                      </Alert>
                    ) : null}

                    {currentQueueState.loading && !currentQueueState.loaded ? (
                      <Paper withBorder radius="xl" p="xl">
                        <Group justify="center" py="xl">
                          <Loader />
                        </Group>
                      </Paper>
                    ) : null}

                    {!currentQueueState.loading &&
                    currentQueueState.loaded &&
                    currentQueueState.items.length === 0 ? (
                      <Paper withBorder radius="xl" p="xl">
                        <Text ta="center" c="dimmed">
                          {reportStatusTab === 'open'
                            ? 'Nema otvorenih prijava.'
                            : 'Nema riješenih prijava.'}
                        </Text>
                      </Paper>
                    ) : null}

                    {currentQueueState.items.length > 0 ? (
                      <Paper withBorder radius="xl" p="lg">
                        <Stack gap="md">
                          <Group justify="space-between" align="center">
                            <Text size="sm" c="dimmed">
                              Ukupno prijava: {currentQueueState.total}
                            </Text>
                            {currentQueueState.loading ? (
                              <Group gap="xs">
                                <Loader size="xs" />
                                <Text size="sm" c="dimmed">
                                  Osvježavanje…
                                </Text>
                              </Group>
                            ) : null}
                          </Group>

                          <ScrollArea>
                            <Table highlightOnHover withTableBorder verticalSpacing="sm">
                              <Table.Thead>
                                <Table.Tr>
                                  <Table.Th>Pojam</Table.Th>
                                  <Table.Th>Broj prijava</Table.Th>
                                  <Table.Th>Prva prijava</Table.Th>
                                  <Table.Th>Status</Table.Th>
                                  <Table.Th>Napomena</Table.Th>
                                  <Table.Th>Akcija</Table.Th>
                                </Table.Tr>
                              </Table.Thead>
                              <Table.Tbody>
                                {currentQueueState.items.map((report) => (
                                  <Table.Tr key={report.id}>
                                    <Table.Td>
                                      <Text fw={500}>{report.search_term}</Text>
                                    </Table.Td>
                                    <Table.Td>{report.report_count}</Table.Td>
                                    <Table.Td>{formatIdentifierDateTime(report.created_at)}</Table.Td>
                                    <Table.Td>
                                      <Badge
                                        color={getIdentifierReportStatusColor(report.status)}
                                        variant="light"
                                      >
                                        {getIdentifierReportStatusLabel(report.status)}
                                      </Badge>
                                    </Table.Td>
                                    <Table.Td>{report.resolution_note ?? '—'}</Table.Td>
                                    <Table.Td>
                                      {report.status === 'OPEN' ? (
                                        <Button
                                          size="xs"
                                          onClick={() => openResolveModal(report)}
                                        >
                                          Riješi
                                        </Button>
                                      ) : (
                                        '—'
                                      )}
                                    </Table.Td>
                                  </Table.Tr>
                                ))}
                              </Table.Tbody>
                            </Table>
                          </ScrollArea>
                        </Stack>
                      </Paper>
                    ) : null}
                  </Tabs.Panel>
                </Tabs>
              </Stack>
            </Tabs.Panel>
          ) : null}
        </Tabs>
      </Stack>
    </>
  )
}
