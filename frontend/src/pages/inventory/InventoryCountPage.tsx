import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Box,
  Button,
  Checkbox,
  Group,
  Loader,
  Modal,
  NumberInput,
  Pagination,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { IconArrowLeft } from '@tabler/icons-react'
import axios from 'axios'

import {
  inventoryApi,
  type ActiveCount,
  type CountDetail,
  type HistoryItem,
  type InventoryCountLine,
  type InventoryCountType,
} from '../../api/inventory'
import FullPageState from '../../components/shared/FullPageState'
import { getApiErrorBody, isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const HISTORY_PAGE_SIZE = 50

const CONNECTION_ERROR =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovo.'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('hr-HR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return '—'
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('hr-HR', {
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

function fmtQty(n: number, decimalDisplay: boolean): string {
  if (!decimalDisplay) {
    return Number.isInteger(n) ? n.toString() : String(n)
  }

  return n.toFixed(2)
}

function fmtDiff(n: number, decimalDisplay: boolean): string {
  const sign = n > 0 ? '+' : ''
  return `${sign}${fmtQty(n, decimalDisplay)}`
}

// ---------------------------------------------------------------------------
// ResolutionBadge
// ---------------------------------------------------------------------------

function ResolutionBadge({ resolution }: { resolution: string | null }) {
  if (!resolution) return <span>—</span>
  const map: Record<string, { label: string; color: string }> = {
    NO_CHANGE: { label: 'Bez promjena', color: 'green' },
    SURPLUS_ADDED: { label: 'Višak dodan', color: 'blue' },
    SHORTAGE_DRAFT_CREATED: { label: 'Manjak (nacrt)', color: 'yellow' },
  }
  const entry = map[resolution]
  if (!entry) return <Badge>{resolution}</Badge>
  return <Badge color={entry.color}>{entry.label}</Badge>
}

// ---------------------------------------------------------------------------
// HistoryView
// ---------------------------------------------------------------------------

interface HistoryViewProps {
  items: HistoryItem[]
  total: number
  page: number
  loading: boolean
  openingCountExists: boolean
  onPageChange: (page: number) => void
  onRowClick: (id: number) => void
  onCountStarted: (count: ActiveCount) => void
  onFatalError: () => void
}

function HistoryView({
  items,
  total,
  page,
  loading,
  openingCountExists,
  onPageChange,
  onRowClick,
  onCountStarted,
  onFatalError,
}: HistoryViewProps) {
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const [typeModalOpen, setTypeModalOpen] = useState(false)
  const [typeModalError, setTypeModalError] = useState<string | null>(null)

  async function doStart(type: InventoryCountType) {
    setStarting(true)
    setStartError(null)
    setTypeModalError(null)
    try {
      await runWithRetry(() => inventoryApi.start(type))
      const active = await runWithRetry(() => inventoryApi.getActive())
      if (active) {
        setTypeModalOpen(false)
        showSuccessToast('Inventura pokrenuta.')
        onCountStarted(active)
      }
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setTypeModalOpen(false)
        onFatalError()
        return
      }
      if (axios.isAxiosError(err) && err.response?.status === 400) {
        const body = getApiErrorBody(err)
        const msg = body?.message || 'Greška pri pokretanju inventure.'
        if (type === 'OPENING') {
          setTypeModalError(msg)
        } else {
          setTypeModalOpen(false)
          setStartError(msg)
        }
      } else {
        showErrorToast('Greška pri pokretanju inventure. Pokušajte ponovo.')
      }
    } finally {
      setStarting(false)
    }
  }

  function handleStart() {
    if (!openingCountExists) {
      setTypeModalError(null)
      setTypeModalOpen(true)
    } else {
      doStart('REGULAR')
    }
  }

  const totalPages = Math.ceil(total / HISTORY_PAGE_SIZE)

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between" align="center">
        <Title order={2}>Inventura</Title>
        <Button onClick={handleStart} loading={starting}>
          Pokreni novu inventuru
        </Button>
      </Group>

      {startError && (
        <Alert color="red" onClose={() => setStartError(null)} withCloseButton>
          {startError}
        </Alert>
      )}

      <Paper withBorder>
        {loading ? (
          <Group justify="center" p="xl">
            <Loader size="sm" />
          </Group>
        ) : (
          <ScrollArea>
            <Table highlightOnHover striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Datum</Table.Th>
                  <Table.Th>Pokrenuo</Table.Th>
                  <Table.Th>Broj stavki</Table.Th>
                  <Table.Th>Broj odstupanja</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {items.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={5}>
                      <Text c="dimmed" ta="center" py="md">
                        Nema evidentiranih inventura.
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  items.map((item) => (
                    <Table.Tr
                      key={item.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => onRowClick(item.id)}
                    >
                      <Table.Td>{formatDate(item.started_at)}</Table.Td>
                      <Table.Td>{item.started_by || '—'}</Table.Td>
                      <Table.Td>{item.total_lines}</Table.Td>
                      <Table.Td>{item.discrepancies}</Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Badge color="teal">ZAVRŠENA</Badge>
                          {item.type === 'OPENING' && (
                            <Badge color="violet">Opening Stock</Badge>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        )}
      </Paper>

      {totalPages > 1 && (
        <Group justify="center">
          <Pagination total={totalPages} value={page} onChange={onPageChange} />
        </Group>
      )}

      <Modal
        opened={typeModalOpen}
        onClose={() => !starting && setTypeModalOpen(false)}
        title="Odaberi vrstu inventure"
      >
        <Stack>
          {typeModalError && (
            <Alert color="red" onClose={() => setTypeModalError(null)} withCloseButton>
              {typeModalError}
            </Alert>
          )}
          <Button
            variant="outline"
            color="violet"
            loading={starting}
            onClick={() => doStart('OPENING')}
          >
            Opening Stock Count
          </Button>
          <Button loading={starting} onClick={() => doStart('REGULAR')}>
            Regular Count
          </Button>
        </Stack>
      </Modal>
    </Stack>
  )
}

// ---------------------------------------------------------------------------
// ActiveCountView
// ---------------------------------------------------------------------------

interface LineEdit {
  value: number | string
  saving: boolean
}

function initEdits(lines: InventoryCountLine[]): Record<number, LineEdit> {
  const edits: Record<number, LineEdit> = {}
  for (const line of lines) {
    edits[line.line_id] = {
      value: line.counted_quantity ?? '',
      saving: false,
    }
  }
  return edits
}

interface ActiveCountViewProps {
  count: ActiveCount
  onCompleted: (countId: number) => void
  onFatalError: () => void
}

function ActiveCountView({ count, onCompleted, onFatalError }: ActiveCountViewProps) {
  const [lines, setLines] = useState<InventoryCountLine[]>(count.lines)
  const [lineEdits, setLineEdits] = useState<Record<number, LineEdit>>(() =>
    initEdits(count.lines)
  )
  const [filterDiscrepancies, setFilterDiscrepancies] = useState(false)
  const [filterUncounted, setFilterUncounted] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)

  // A line is "counted" when its edit value is a valid number (>= 0)
  const countedCount = lines.filter((l) => typeof lineEdits[l.line_id]?.value === 'number').length
  const allCounted = countedCount === lines.length && lines.length > 0

  function getLocalCounted(lineId: number, savedQty: number | null): number | null {
    const edit = lineEdits[lineId]
    if (!edit) return savedQty
    return typeof edit.value === 'number' ? edit.value : savedQty
  }

  function getActiveBg(lineId: number, systemQty: number, savedQty: number | null): string | undefined {
    const val = getLocalCounted(lineId, savedQty)
    if (val === null) return undefined
    if (val === systemQty) return 'var(--mantine-color-green-0)'
    if (val > systemQty) return 'var(--mantine-color-blue-0)'
    return 'var(--mantine-color-yellow-0)'
  }

  const displayLines = lines.filter((line) => {
    const localCounted = getLocalCounted(line.line_id, line.counted_quantity)
    if (filterUncounted && localCounted !== null) return false
    if (filterDiscrepancies) {
      if (localCounted === null) return false
      if (localCounted === line.system_quantity) return false
    }
    return true
  })

  async function handleBlur(line: InventoryCountLine) {
    const edit = lineEdits[line.line_id]
    if (!edit) return

    // Parse the current input value
    const raw = edit.value
    const val = typeof raw === 'number' ? raw : parseFloat(String(raw))

    // If empty/invalid, revert to last saved value
    if (isNaN(val)) {
      setLineEdits((prev) => ({
        ...prev,
        [line.line_id]: { ...prev[line.line_id], value: line.counted_quantity ?? '' },
      }))
      return
    }

    // Reject negative
    if (val < 0) {
      setLineEdits((prev) => ({
        ...prev,
        [line.line_id]: { ...prev[line.line_id], value: line.counted_quantity ?? '' },
      }))
      showErrorToast('Količina mora biti >= 0.')
      return
    }

    // No change from saved value — skip
    if (val === line.counted_quantity) return

    setLineEdits((prev) => ({
      ...prev,
      [line.line_id]: { ...prev[line.line_id], saving: true },
    }))

    try {
      const updated = await runWithRetry(() => inventoryApi.updateLine(count.id, line.line_id, val))
      setLines((prev) => prev.map((l) => (l.line_id === updated.line_id ? updated : l)))
      setLineEdits((prev) => ({
        ...prev,
        [updated.line_id]: {
          value: updated.counted_quantity ?? '',
          saving: false,
        },
      }))
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setLineEdits((prev) => ({
          ...prev,
          [line.line_id]: {
            value: line.counted_quantity ?? '',
            saving: false,
          },
        }))
        onFatalError()
        return
      }
      const body = getApiErrorBody(err)
      const msg = body?.message || 'Greška pri spremanju stavke.'
      showErrorToast(msg)
      setLineEdits((prev) => ({
        ...prev,
        [line.line_id]: {
          value: line.counted_quantity ?? '',
          saving: false,
        },
      }))
    }
  }

  async function handleComplete() {
    setCompleting(true)
    setConfirmOpen(false)
    try {
      const result = await runWithRetry(() => inventoryApi.complete(count.id))
      onCompleted(result.id)
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        onFatalError()
        return
      }
      const body = getApiErrorBody(err)
      showErrorToast(body?.message || 'Greška pri završavanju inventure.')
    } finally {
      setCompleting(false)
    }
  }

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between" align="flex-start">
        <Stack gap={2}>
          <Group gap="sm" align="center">
            <Title order={2}>Inventura u tijeku</Title>
            {count.type === 'OPENING' && (
              <Badge color="violet" size="lg">Opening Stock</Badge>
            )}
          </Group>
          <Text c="dimmed" size="sm">
            Pokrenuo: {count.started_by || '—'} &nbsp;|&nbsp; {formatDateTime(count.started_at)}
          </Text>
          <Text size="sm" fw={600}>
            {countedCount} / {lines.length} prebrojano
          </Text>
        </Stack>

        <Tooltip
          label="Sve stavke moraju biti prebrojane prije završetka."
          disabled={allCounted}
          withArrow
        >
          <span>
            <Button
              color="green"
              disabled={!allCounted}
              loading={completing}
              onClick={() => setConfirmOpen(true)}
              style={{ pointerEvents: !allCounted ? 'none' : undefined }}
            >
              Završi inventuru
            </Button>
          </span>
        </Tooltip>
      </Group>

      <Group gap="md">
        <Checkbox
          label="Samo odstupanja"
          checked={filterDiscrepancies}
          onChange={(e) => setFilterDiscrepancies(e.currentTarget.checked)}
        />
        <Checkbox
          label="Samo neprebrojano"
          checked={filterUncounted}
          onChange={(e) => setFilterUncounted(e.currentTarget.checked)}
        />
      </Group>

      <Paper withBorder>
        <ScrollArea>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Artikl br.</Table.Th>
                <Table.Th>Opis</Table.Th>
                <Table.Th>Serija</Table.Th>
                <Table.Th>Rok valjanosti</Table.Th>
                <Table.Th>Stanje sustava</Table.Th>
                <Table.Th>JMJ</Table.Th>
                <Table.Th>Prebrojano</Table.Th>
                <Table.Th>Razlika</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {displayLines.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={8}>
                    <Text c="dimmed" ta="center" py="md">
                      Nema stavki za prikaz.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                displayLines.map((line) => {
                  const edit = lineEdits[line.line_id]
                  const localCounted = getLocalCounted(line.line_id, line.counted_quantity)
                  const displayDiff =
                    localCounted !== null ? localCounted - line.system_quantity : null
                  const bg = getActiveBg(line.line_id, line.system_quantity, line.counted_quantity)

                  return (
                    <Table.Tr key={line.line_id} style={{ backgroundColor: bg }}>
                      <Table.Td>{line.article_no || '—'}</Table.Td>
                      <Table.Td>{line.description || '—'}</Table.Td>
                      <Table.Td>{line.batch_code || '—'}</Table.Td>
                      <Table.Td>{formatDate(line.expiry_date)}</Table.Td>
                      <Table.Td>{fmtQty(line.system_quantity, line.decimal_display)}</Table.Td>
                      <Table.Td>{line.uom}</Table.Td>
                      <Table.Td>
                        <NumberInput
                          value={edit?.value ?? ''}
                          onChange={(v) =>
                            setLineEdits((prev) => ({
                              ...prev,
                              [line.line_id]: { ...prev[line.line_id], value: v },
                            }))
                          }
                          onBlur={() => handleBlur(line)}
                          min={0}
                          size="xs"
                          w={110}
                          step={line.decimal_display ? 0.01 : 1}
                          disabled={edit?.saving}
                          rightSection={edit?.saving ? <Loader size={12} /> : null}
                          hideControls
                        />
                      </Table.Td>
                      <Table.Td>
                        {displayDiff !== null ? (
                          <Text
                            size="sm"
                            fw={500}
                            c={
                              displayDiff > 0
                                ? 'blue'
                                : displayDiff < 0
                                  ? 'yellow.7'
                                  : 'green'
                            }
                          >
                            {fmtDiff(displayDiff, line.decimal_display)}
                          </Text>
                        ) : (
                          '—'
                        )}
                      </Table.Td>
                    </Table.Tr>
                  )
                })
              )}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      </Paper>

      <Modal
        opened={confirmOpen}
        onClose={() => !completing && setConfirmOpen(false)}
        title="Završi inventuru"
      >
        <Stack>
          <Text>
            Završiti ovu inventuru? Odstupanja će biti automatski obrađena. Ova radnja se ne može
            poništiti.
          </Text>
          <Group justify="flex-end" mt="sm">
            <Button
              variant="subtle"
              onClick={() => setConfirmOpen(false)}
              disabled={completing}
            >
              Odustani
            </Button>
            <Button color="green" loading={completing} onClick={handleComplete}>
              Završi
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  )
}

// ---------------------------------------------------------------------------
// CompletedDetailView
// ---------------------------------------------------------------------------

const RESOLUTION_OPTIONS = [
  { value: 'ALL', label: 'Sve stavke' },
  { value: 'NO_CHANGE', label: 'Bez promjena' },
  { value: 'SURPLUS_ADDED', label: 'Višak dodan' },
  { value: 'SHORTAGE_DRAFT_CREATED', label: 'Manjkovi' },
]

interface CompletedDetailViewProps {
  count: CountDetail
  onBack: () => void
}

function CompletedDetailView({ count, onBack }: CompletedDetailViewProps) {
  const [resolutionFilter, setResolutionFilter] = useState('ALL')

  const displayLines = count.lines.filter((line) => {
    if (resolutionFilter === 'ALL') return true
    return line.resolution === resolutionFilter
  })

  function getCompletedBg(resolution: string | null): string | undefined {
    switch (resolution) {
      case 'NO_CHANGE':
        return 'var(--mantine-color-green-0)'
      case 'SURPLUS_ADDED':
        return 'var(--mantine-color-blue-0)'
      case 'SHORTAGE_DRAFT_CREATED':
        return 'var(--mantine-color-yellow-0)'
      default:
        return undefined
    }
  }

  const s = count.summary

  return (
    <Stack gap="lg" p="md">
      <Group align="center" gap="sm">
        <Button
          variant="subtle"
          leftSection={<IconArrowLeft size={16} />}
          onClick={onBack}
          px="xs"
        >
          Natrag
        </Button>
        <Title order={2}>Završena inventura #{count.id}</Title>
        {count.type === 'OPENING' && (
          <Badge color="violet" size="lg">Opening Stock</Badge>
        )}
      </Group>

      {/* Metadata header */}
      <Paper withBorder p="md">
        <Group gap="xl">
          <Box>
            <Text size="xs" c="dimmed">
              Pokrenuo
            </Text>
            <Text fw={500}>{count.started_by || '—'}</Text>
          </Box>
          <Box>
            <Text size="xs" c="dimmed">
              Datum pokretanja
            </Text>
            <Text fw={500}>{formatDateTime(count.started_at)}</Text>
          </Box>
          <Box>
            <Text size="xs" c="dimmed">
              Datum završetka
            </Text>
            <Text fw={500}>{formatDateTime(count.completed_at)}</Text>
          </Box>
        </Group>
      </Paper>

      {/* Summary widget */}
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <Paper withBorder p="md">
          <Text size="xs" c="dimmed">
            Ukupno stavki
          </Text>
          <Text size="xl" fw={700}>
            {s.total_lines}
          </Text>
        </Paper>
        <Paper withBorder p="md">
          <Text size="xs" c="dimmed">
            Bez promjena
          </Text>
          <Text size="xl" fw={700} c="green">
            {s.no_change}
          </Text>
        </Paper>
        <Paper withBorder p="md">
          <Text size="xs" c="dimmed">
            Višak dodan
          </Text>
          <Text size="xl" fw={700} c="blue">
            {s.surplus_added}
          </Text>
        </Paper>
        <Paper withBorder p="md">
          <Text size="xs" c="dimmed">
            Manjkovi (nacrti)
          </Text>
          <Text size="xl" fw={700} c="yellow.7">
            {s.shortage_drafts_created}
          </Text>
        </Paper>
      </SimpleGrid>

      {/* Resolution filter */}
      <Group>
        <Select
          value={resolutionFilter}
          onChange={(v) => setResolutionFilter(v ?? 'ALL')}
          data={RESOLUTION_OPTIONS}
          w={220}
        />
      </Group>

      {/* Lines table */}
      <Paper withBorder>
        <ScrollArea>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Artikl br.</Table.Th>
                <Table.Th>Opis</Table.Th>
                <Table.Th>Serija</Table.Th>
                <Table.Th>Rok valjanosti</Table.Th>
                <Table.Th>Stanje sustava</Table.Th>
                <Table.Th>JMJ</Table.Th>
                <Table.Th>Prebrojano</Table.Th>
                <Table.Th>Razlika</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {displayLines.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={9}>
                    <Text c="dimmed" ta="center" py="md">
                      Nema stavki za odabrani filter.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                displayLines.map((line) => (
                  <Table.Tr
                    key={line.line_id}
                    style={{ backgroundColor: getCompletedBg(line.resolution) }}
                  >
                    <Table.Td>{line.article_no || '—'}</Table.Td>
                    <Table.Td>{line.description || '—'}</Table.Td>
                    <Table.Td>{line.batch_code || '—'}</Table.Td>
                    <Table.Td>{formatDate(line.expiry_date)}</Table.Td>
                    <Table.Td>{fmtQty(line.system_quantity, line.decimal_display)}</Table.Td>
                    <Table.Td>{line.uom}</Table.Td>
                    <Table.Td>
                      {line.counted_quantity !== null
                        ? fmtQty(line.counted_quantity, line.decimal_display)
                        : '—'}
                    </Table.Td>
                    <Table.Td>
                      {line.difference !== null ? (
                        <Text
                          size="sm"
                          fw={500}
                          c={
                            line.difference > 0
                              ? 'blue'
                              : line.difference < 0
                                ? 'yellow.7'
                                : 'green'
                            }
                          >
                          {fmtDiff(line.difference, line.decimal_display)}
                        </Text>
                      ) : (
                        '—'
                      )}
                    </Table.Td>
                    <Table.Td>
                      <ResolutionBadge resolution={line.resolution} />
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      </Paper>
    </Stack>
  )
}

// ---------------------------------------------------------------------------
// InventoryCountPage — main entry point
// ---------------------------------------------------------------------------

type ViewKind = 'loading' | 'load-error' | 'history' | 'active' | 'detail'

export default function InventoryCountPage() {
  const [view, setView] = useState<ViewKind>('loading')
  const [activeCount, setActiveCount] = useState<ActiveCount | null>(null)
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [openingCountExists, setOpeningCountExists] = useState(true)
  const [detailCount, setDetailCount] = useState<CountDetail | null>(null)

  const loadHistory = useCallback(async (page: number) => {
    setHistoryLoading(true)
    try {
      const data = await runWithRetry(() => inventoryApi.history(page, HISTORY_PAGE_SIZE))
      setHistoryItems(data.items)
      setHistoryTotal(data.total)
      setHistoryPage(page)
      setOpeningCountExists(data.opening_count_exists)
      setView('history')
    } catch {
      setView('load-error')
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  const initPage = useCallback(async () => {
    setView('loading')
    try {
      const active = await runWithRetry(() => inventoryApi.getActive())
      if (active) {
        setActiveCount(active)
        setView('active')
      } else {
        await loadHistory(1)
      }
    } catch {
      setView('load-error')
    }
  }, [loadHistory])

  useEffect(() => {
    initPage()
  }, [initPage])

  async function handleHistoryRowClick(id: number) {
    try {
      const detail = await runWithRetry(() => inventoryApi.detail(id))
      setDetailCount(detail)
      setView('detail')
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setView('load-error')
        return
      }
      showErrorToast('Greška pri učitavanju inventure.')
    }
  }

  async function handleCountCompleted(countId: number) {
    try {
      const detail = await runWithRetry(() => inventoryApi.detail(countId))
      setDetailCount(detail)
      setView('detail')
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setView('load-error')
        return
      }
      showErrorToast('Greška pri učitavanju završene inventure.')
      initPage()
    }
  }

  if (view === 'loading') {
    return <FullPageState title="Učitavanje…" loading />
  }

  if (view === 'load-error') {
    return (
      <FullPageState
        title="Greška pri učitavanju"
        message={CONNECTION_ERROR}
        actionLabel="Pokušaj ponovo"
        onAction={initPage}
      />
    )
  }

  if (view === 'active' && activeCount) {
    return (
      <ActiveCountView
        count={activeCount}
        onCompleted={handleCountCompleted}
        onFatalError={() => setView('load-error')}
      />
    )
  }

  if (view === 'detail' && detailCount) {
    return <CompletedDetailView count={detailCount} onBack={initPage} />
  }

  // Default: history view
  return (
    <HistoryView
      items={historyItems}
      total={historyTotal}
      page={historyPage}
      loading={historyLoading}
      openingCountExists={openingCountExists}
      onPageChange={loadHistory}
      onRowClick={handleHistoryRowClick}
      onFatalError={() => setView('load-error')}
      onCountStarted={(active) => {
        setActiveCount(active)
        setView('active')
      }}
    />
  )
}
