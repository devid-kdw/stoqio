import { useCallback, useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Checkbox,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  ScrollArea,
  Stack,
  Table,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react'

import {
  inventoryApi,
  type ActiveCount,
  type InventoryCountLine,
} from '../../api/inventory'
import { formatDate, formatDateTime } from '../../utils/locale'
import { getApiErrorBody, isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast } from '../../utils/toasts'
import {
  buildActiveDisplayItems,
  filterActiveDisplayItems,
  resolveCountedQuantity,
  type ActiveDisplayItem,
  type FilteredDisplayItem,
} from './activeCountDisplay'
import { fmtQty, fmtDiff } from './inventoryFormatters'

// ---------------------------------------------------------------------------
// Local types
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

// ---------------------------------------------------------------------------
// ActiveCountView
// ---------------------------------------------------------------------------

export interface ActiveCountViewProps {
  count: ActiveCount
  onCompleted: (countId: number) => void
  onFatalError: () => void
}

export function ActiveCountView({ count, onCompleted, onFatalError }: ActiveCountViewProps) {
  const [lines, setLines] = useState<InventoryCountLine[]>(count.lines)
  const [lineEdits, setLineEdits] = useState<Record<number, LineEdit>>(() =>
    initEdits(count.lines)
  )
  const [filterDiscrepancies, setFilterDiscrepancies] = useState(false)
  const [filterUncounted, setFilterUncounted] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set())

  // Progress operates on leaf count-lines only (flat lines array, no parent rows)
  const countedCount = lines.filter((l) => typeof lineEdits[l.line_id]?.value === 'number').length
  const allCounted = countedCount === lines.length && lines.length > 0

  function toggleArticle(articleId: number) {
    setExpandedArticles((prev) => {
      const next = new Set(prev)
      if (next.has(articleId)) next.delete(articleId)
      else next.add(articleId)
      return next
    })
  }

  const getLocalCounted = useCallback(
    (line: InventoryCountLine): number | null =>
      resolveCountedQuantity(lineEdits[line.line_id]?.value, line.counted_quantity),
    [lineEdits]
  )

  // Build ordered display items, grouping batch lines under their article (memoised on lines)
  const allDisplayItems = useMemo((): ActiveDisplayItem[] => buildActiveDisplayItems(lines), [lines])

  // Apply filters to leaf rows; a batch group survives only if at least one child passes
  const filteredDisplayItems = useMemo(
    (): FilteredDisplayItem[] =>
      filterActiveDisplayItems(allDisplayItems, {
        filterDiscrepancies,
        filterUncounted,
        getLocalCounted,
      }),
    [allDisplayItems, filterDiscrepancies, filterUncounted, getLocalCounted]
  )

  async function handleBlur(line: InventoryCountLine) {
    const edit = lineEdits[line.line_id]
    if (!edit) return

    const raw = edit.value
    const val = typeof raw === 'number' ? raw : parseFloat(String(raw))

    if (isNaN(val)) {
      setLineEdits((prev) => ({
        ...prev,
        [line.line_id]: { ...prev[line.line_id], value: line.counted_quantity ?? '' },
      }))
      return
    }

    if (val < 0) {
      setLineEdits((prev) => ({
        ...prev,
        [line.line_id]: { ...prev[line.line_id], value: line.counted_quantity ?? '' },
      }))
      showErrorToast('Količina mora biti >= 0.')
      return
    }

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
      const result = await inventoryApi.complete(count.id)
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

  function renderCountedQtyInput(line: InventoryCountLine) {
    const edit = lineEdits[line.line_id]
    return (
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
    )
  }

  function renderDiff(displayDiff: number | null, decimalDisplay: boolean) {
    if (displayDiff === null) return '—'
    return (
      <Text
        size="sm"
        fw={500}
        c={displayDiff > 0 ? 'blue' : displayDiff < 0 ? 'yellow.7' : 'green'}
      >
        {fmtDiff(displayDiff, decimalDisplay)}
      </Text>
    )
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
                <Table.Th>Batch</Table.Th>
                <Table.Th>Rok valjanosti</Table.Th>
                <Table.Th>Stanje sustava</Table.Th>
                <Table.Th>JMJ</Table.Th>
                <Table.Th>Prebrojano</Table.Th>
                <Table.Th>Razlika</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {filteredDisplayItems.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={8}>
                    <Text c="dimmed" ta="center" py="md">
                      Nema stavki za prikaz.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                filteredDisplayItems.flatMap((item) => {
                  if (item.kind === 'non-batch') {
                    const line = item.line
                    const localCounted = getLocalCounted(line)
                    const displayDiff =
                      localCounted !== null ? localCounted - line.system_quantity : null
                    const bg =
                      localCounted === null
                        ? undefined
                        : localCounted === line.system_quantity
                          ? 'var(--mantine-color-green-0)'
                          : localCounted > line.system_quantity
                            ? 'var(--mantine-color-blue-0)'
                            : 'var(--mantine-color-yellow-0)'

                    return [
                      <Table.Tr key={line.line_id} style={{ backgroundColor: bg }}>
                        <Table.Td>{line.article_no || '—'}</Table.Td>
                        <Table.Td>{line.description || '—'}</Table.Td>
                        <Table.Td>{line.batch_code || '—'}</Table.Td>
                        <Table.Td>{formatDate(line.expiry_date)}</Table.Td>
                        <Table.Td>{fmtQty(line.system_quantity, line.decimal_display)}</Table.Td>
                        <Table.Td>{line.uom}</Table.Td>
                        <Table.Td>{renderCountedQtyInput(line)}</Table.Td>
                        <Table.Td>{renderDiff(displayDiff, line.decimal_display)}</Table.Td>
                      </Table.Tr>,
                    ]
                  } else {
                    // batch-group: parent row + optional child rows
                    const { group, visibleChildren } = item
                    const isExpanded = expandedArticles.has(group.article_id)
                    const totalQty = group.lines.reduce((sum, l) => sum + l.system_quantity, 0)
                    const summaryText = `${group.lines.length} batches / ${fmtQty(totalQty, group.decimal_display)} ${group.uom} total`

                    const rows = [
                      <Table.Tr
                        key={`group-${group.article_id}`}
                        style={{
                          cursor: 'pointer',
                          backgroundColor: 'var(--mantine-color-gray-1)',
                        }}
                        onClick={() => toggleArticle(group.article_id)}
                      >
                        <Table.Td>
                          <Group gap="xs" wrap="nowrap">
                            {isExpanded ? (
                              <IconChevronDown size={14} />
                            ) : (
                              <IconChevronRight size={14} />
                            )}
                            <Text size="sm" fw={600}>
                              {group.article_no || '—'}
                            </Text>
                          </Group>
                        </Table.Td>
                        <Table.Td>
                          <Text size="sm" fw={600}>
                            {group.description || '—'}
                          </Text>
                        </Table.Td>
                        <Table.Td>—</Table.Td>
                        <Table.Td>—</Table.Td>
                        <Table.Td>
                          <Text size="sm" c="dimmed">
                            {summaryText}
                          </Text>
                        </Table.Td>
                        <Table.Td>—</Table.Td>
                        <Table.Td>—</Table.Td>
                        <Table.Td>—</Table.Td>
                      </Table.Tr>,
                    ]

                    if (isExpanded) {
                      for (const line of visibleChildren) {
                        const localCounted = getLocalCounted(line)
                        const displayDiff =
                          localCounted !== null ? localCounted - line.system_quantity : null
                        const bg =
                          localCounted === null
                            ? undefined
                            : localCounted === line.system_quantity
                              ? 'var(--mantine-color-green-0)'
                              : localCounted > line.system_quantity
                                ? 'var(--mantine-color-blue-0)'
                                : 'var(--mantine-color-yellow-0)'

                        rows.push(
                          <Table.Tr key={line.line_id} style={{ backgroundColor: bg }}>
                            <Table.Td />
                            <Table.Td />
                            <Table.Td>
                              <Text size="sm" pl="sm">
                                {line.batch_code || '—'}
                              </Text>
                            </Table.Td>
                            <Table.Td>{formatDate(line.expiry_date)}</Table.Td>
                            <Table.Td>
                              {fmtQty(line.system_quantity, line.decimal_display)}
                            </Table.Td>
                            <Table.Td>{line.uom}</Table.Td>
                            <Table.Td>{renderCountedQtyInput(line)}</Table.Td>
                            <Table.Td>{renderDiff(displayDiff, line.decimal_display)}</Table.Td>
                          </Table.Tr>
                        )
                      }
                    }

                    return rows
                  }
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
