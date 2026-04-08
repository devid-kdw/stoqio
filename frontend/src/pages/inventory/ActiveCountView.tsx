import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react'

import {
  articlesApi,
  type ArticleLookupResult,
  type WarehouseArticleListItem,
} from '../../api/articles'
import {
  inventoryApi,
  type ActiveCount,
  type InventoryCountLine,
} from '../../api/inventory'
import { formatDate, formatDateTime } from '../../utils/locale'
import { getApiErrorBody, isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import { INTEGER_UOMS } from '../../utils/uom'
import {
  buildActiveDisplayItems,
  filterActiveDisplayItems,
  resolveCountedQuantity,
  type ActiveDisplayItem,
  type FilteredDisplayItem,
} from './activeCountDisplay'
import { fmtQty, fmtDiff } from './inventoryFormatters'
import { translateArticleApiMessage } from '../warehouse/warehouseUtils'

// ---------------------------------------------------------------------------
// Local types
// ---------------------------------------------------------------------------

interface LineEdit {
  value: number | string
  saving: boolean
}

interface OpeningArticleOption {
  id: number
  article_no: string
  description: string
  label: string
}

function toOpeningArticleOption(article: {
  id: number
  article_no: string
  description: string
}): OpeningArticleOption {
  return {
    id: article.id,
    article_no: article.article_no,
    description: article.description,
    label: `${article.article_no} - ${article.description}`,
  }
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
  onCountRefreshed: (count: ActiveCount) => void
  onFatalError: () => void
}

export function ActiveCountView({
  count,
  onCompleted,
  onCountRefreshed,
  onFatalError,
}: ActiveCountViewProps) {
  const [lines, setLines] = useState<InventoryCountLine[]>(count.lines)
  const [lineEdits, setLineEdits] = useState<Record<number, LineEdit>>(() =>
    initEdits(count.lines)
  )
  const [filterDiscrepancies, setFilterDiscrepancies] = useState(false)
  const [filterUncounted, setFilterUncounted] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set())
  const [openingBatchModalOpen, setOpeningBatchModalOpen] = useState(false)
  const [openingBatchSubmitting, setOpeningBatchSubmitting] = useState(false)
  const [openingArticleQuery, setOpeningArticleQuery] = useState('')
  const [openingArticle, setOpeningArticle] = useState<ArticleLookupResult | null>(null)
  const [openingArticleOptions, setOpeningArticleOptions] = useState<OpeningArticleOption[]>([])
  const [openingArticleLoading, setOpeningArticleLoading] = useState(false)
  const [openingArticleError, setOpeningArticleError] = useState<string | null>(null)
  const [openingBatchCode, setOpeningBatchCode] = useState('')
  const [openingExpiryDate, setOpeningExpiryDate] = useState('')
  const [openingCountedQuantity, setOpeningCountedQuantity] = useState<number | string>('')
  const [openingBatchError, setOpeningBatchError] = useState<string | null>(null)

  const openingArticleSelectData = useMemo(() => {
    const seen = new Set<number>()

    const selectedOption = openingArticle ? toOpeningArticleOption(openingArticle) : null

    return [selectedOption, ...openingArticleOptions].reduce<Array<{ value: string; label: string }>>(
      (accumulator, option) => {
        if (!option || seen.has(option.id)) {
          return accumulator
        }

        seen.add(option.id)
        accumulator.push({
          value: String(option.id),
          label: option.label,
        })
        return accumulator
      },
      []
    )
  }, [openingArticle, openingArticleOptions])

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

  function resetOpeningBatchForm() {
    setOpeningArticleQuery('')
    setOpeningArticle(null)
    setOpeningArticleOptions([])
    setOpeningArticleLoading(false)
    setOpeningArticleError(null)
    setOpeningBatchCode('')
    setOpeningExpiryDate('')
    setOpeningCountedQuantity('')
    setOpeningBatchError(null)
  }

  const applyCountSnapshot = useCallback(
    (nextCount: ActiveCount) => {
      setLines(nextCount.lines)
      setLineEdits(initEdits(nextCount.lines))
      onCountRefreshed(nextCount)
    },
    [onCountRefreshed]
  )

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

  const loadOpeningArticle = useCallback(
    async (option: OpeningArticleOption) => {
      setOpeningArticleLoading(true)
      setOpeningArticleError(null)
      setOpeningBatchError(null)

      try {
        const detail = await runWithRetry(() => articlesApi.getDetail(option.id))
        if (!detail.has_batch) {
          setOpeningArticle(null)
          setOpeningArticleError('Ovaj artikl nema šarže.')
          return
        }

        const article: ArticleLookupResult = {
          id: detail.id,
          article_no: detail.article_no,
          description: detail.description,
          base_uom: detail.base_uom ?? 'kom',
          has_batch: detail.has_batch,
          batches: detail.batches?.map((batch) => ({
            id: batch.id,
            batch_code: batch.batch_code,
            expiry_date: batch.expiry_date ?? '',
          })),
        }

        setOpeningArticle(article)
        setOpeningArticleQuery(option.label)
        setOpeningBatchCode('')
        setOpeningExpiryDate('')
        setOpeningCountedQuantity('')
      } catch (err) {
        if (isNetworkOrServerError(err)) {
          onFatalError()
          return
        }

        setOpeningArticle(null)
        setOpeningArticleError(
          translateArticleApiMessage(getApiErrorBody(err), 'Artikl nije pronađen.')
        )
      } finally {
        setOpeningArticleLoading(false)
      }
    },
    [onFatalError]
  )

  useEffect(() => {
    if (!openingBatchModalOpen) {
      return
    }

    const searchQuery = openingArticleQuery.trim()
    const selectedLabel = openingArticle
      ? `${openingArticle.article_no} - ${openingArticle.description}`
      : null

    if (searchQuery.length < 2 || searchQuery === selectedLabel) {
      if (!openingArticle) {
        setOpeningArticleOptions([])
      }
      setOpeningArticleError(null)
      setOpeningArticleLoading(false)
      return
    }

    const timer = window.setTimeout(async () => {
      setOpeningArticleLoading(true)
      setOpeningArticleError(null)
      setOpeningBatchError(null)

      try {
        const response = await runWithRetry(() =>
          articlesApi.listWarehouse({
            page: 1,
            perPage: 10,
            q: searchQuery,
          })
        )

        setOpeningArticleOptions(
          response.items.map((item: WarehouseArticleListItem) => toOpeningArticleOption(item))
        )
      } catch (err) {
        if (isNetworkOrServerError(err)) {
          onFatalError()
          return
        }

        setOpeningArticleError(
          translateArticleApiMessage(getApiErrorBody(err), 'Pretraga artikala nije uspjela.')
        )
      } finally {
        setOpeningArticleLoading(false)
      }
    }, 250)

    return () => window.clearTimeout(timer)
  }, [onFatalError, openingArticle, openingArticleQuery, openingBatchModalOpen])

  const handleOpeningBatchSubmit = useCallback(async () => {
    if (!openingArticle) {
      setOpeningArticleError('Artikl sa šaržom je obavezan.')
      return
    }

    const trimmedBatchCode = openingBatchCode.trim()
    const qty =
      typeof openingCountedQuantity === 'number'
        ? openingCountedQuantity
        : Number.parseFloat(String(openingCountedQuantity))

    if (!trimmedBatchCode) {
      setOpeningBatchError('Šifra šarže je obavezna.')
      return
    }

    if (!openingExpiryDate) {
      setOpeningBatchError('Rok valjanosti je obavezan.')
      return
    }

    if (Number.isNaN(qty) || qty <= 0) {
      setOpeningBatchError('Količina mora biti veća od 0.')
      return
    }

    setOpeningBatchSubmitting(true)
    setOpeningBatchError(null)

    try {
      const updatedCount = await runWithRetry(() =>
        inventoryApi.addOpeningBatchLine(count.id, {
          article_id: openingArticle.id,
          batch_code: trimmedBatchCode,
          expiry_date: openingExpiryDate,
          counted_quantity: qty,
        })
      )
      applyCountSnapshot(updatedCount)
      showSuccessToast('Šarža je dodana.')
      setOpeningBatchError(null)
      setOpeningBatchCode('')
      setOpeningExpiryDate('')
      setOpeningCountedQuantity('')
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        onFatalError()
        return
      }

      const body = getApiErrorBody(err)
      setOpeningBatchError(
        translateArticleApiMessage(body, 'Dodavanje šarže nije uspjelo.')
      )
    } finally {
      setOpeningBatchSubmitting(false)
    }
  }, [
    applyCountSnapshot,
    count.id,
    onFatalError,
    openingArticle,
    openingBatchCode,
    openingCountedQuantity,
    openingExpiryDate,
  ])

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
              <Badge color="violet" size="lg">Inicijalna inventura</Badge>
            )}
          </Group>
          <Text c="dimmed" size="sm">
            Pokrenuo: {count.started_by || '—'} &nbsp;|&nbsp; {formatDateTime(count.started_at)}
          </Text>
          <Text size="sm" fw={600}>
            {countedCount} / {lines.length} prebrojano
          </Text>
        </Stack>

        <Stack gap="xs" align="flex-end">
          {count.type === 'OPENING' && (
            <Button
              variant="light"
              onClick={() => {
                resetOpeningBatchForm()
                setOpeningBatchModalOpen(true)
              }}
            >
              Dodaj šaržu
            </Button>
          )}

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
        </Stack>
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
                <Table.Th>Šarža</Table.Th>
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
                    return [
                      <Table.Tr key={line.line_id}>
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
                    const totalSystemQty = group.lines.reduce((sum, l) => sum + l.system_quantity, 0)
                    const countedChildren = group.lines.map((line) => getLocalCounted(line))
                    const allChildrenCounted = countedChildren.every((qty) => qty !== null)
                    const totalCountedQty = allChildrenCounted
                      ? countedChildren.reduce((sum, qty) => sum + (qty ?? 0), 0)
                      : null
                    const totalDiff =
                      totalCountedQty !== null ? totalCountedQty - totalSystemQty : null
                    const summaryText = `${group.lines.length} šarža / ${fmtQty(totalSystemQty, group.decimal_display)} ${group.uom} ukupno`

                    const rows = [
                      <Table.Tr
                        key={`group-${group.article_id}`}
                        style={{
                          cursor: 'pointer',
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
                        <Table.Td>{group.uom}</Table.Td>
                        <Table.Td>
                          {totalCountedQty !== null
                            ? fmtQty(totalCountedQty, group.decimal_display)
                            : '—'}
                        </Table.Td>
                        <Table.Td>{renderDiff(totalDiff, group.decimal_display)}</Table.Td>
                      </Table.Tr>,
                    ]

                    if (isExpanded) {
                      for (const line of visibleChildren) {
                        const localCounted = getLocalCounted(line)
                        const displayDiff =
                          localCounted !== null ? localCounted - line.system_quantity : null
                        rows.push(
                          <Table.Tr key={line.line_id}>
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
        opened={openingBatchModalOpen}
        onClose={() => {
          if (openingBatchSubmitting) {
            return
          }
          setOpeningBatchModalOpen(false)
          resetOpeningBatchForm()
        }}
        title="Unos šarže za početno stanje"
        size="lg"
      >
        <Stack gap="md">
          {openingBatchError ? (
            <Alert color="red" withCloseButton onClose={() => setOpeningBatchError(null)}>
              {openingBatchError}
            </Alert>
          ) : null}

          <Select
            label="Artikl"
            placeholder="Pretražite broj ili opis artikla"
            searchable
            clearable
            data={openingArticleSelectData}
            searchValue={openingArticleQuery}
            onSearchChange={(value) => {
              setOpeningArticleQuery(value)
              setOpeningArticleError(null)
              setOpeningBatchError(null)
              if (
                openingArticle &&
                value !== `${openingArticle.article_no} - ${openingArticle.description}`
              ) {
                setOpeningArticle(null)
                setOpeningBatchCode('')
                setOpeningExpiryDate('')
                setOpeningCountedQuantity('')
              }
            }}
            value={openingArticle ? String(openingArticle.id) : null}
            onChange={(value) => {
              if (!value) {
                setOpeningArticle(null)
                setOpeningArticleQuery('')
                setOpeningArticleOptions([])
                setOpeningBatchCode('')
                setOpeningExpiryDate('')
                setOpeningCountedQuantity('')
                return
              }

              const selectedOption = [openingArticle, ...openingArticleOptions]
                .map((option) => {
                  if (!option) {
                    return null
                  }

                  if ('label' in option) {
                    return option as OpeningArticleOption
                  }

                  return toOpeningArticleOption(option)
                })
                .find((option) => option?.id === Number(value))

              if (!selectedOption) {
                return
              }

              void loadOpeningArticle(selectedOption)
            }}
            nothingFoundMessage={
              openingArticleQuery.trim().length < 2
                ? 'Upišite najmanje 2 znaka.'
                : 'Nema rezultata.'
            }
            error={openingArticleError}
            rightSection={openingArticleLoading ? <Loader size="xs" /> : null}
          />

          {openingArticle ? (
            <Paper withBorder p="md">
              <Stack gap={4}>
                <Text fw={600}>{openingArticle.article_no}</Text>
                <Text size="sm" c="dimmed">
                  {openingArticle.description}
                </Text>
                <Text size="sm" c="dimmed">
                  Osnovna mjerna jedinica: {openingArticle.base_uom}
                </Text>
              </Stack>
            </Paper>
          ) : null}

          <Group grow align="flex-start">
            <TextInput
              label="Šifra šarže"
              placeholder="Unesite šifru šarže"
              value={openingBatchCode}
              onChange={(event) => setOpeningBatchCode(event.currentTarget.value)}
              disabled={!openingArticle}
            />
            <TextInput
              label="Rok valjanosti"
              type="date"
              value={openingExpiryDate}
              onChange={(event) => setOpeningExpiryDate(event.currentTarget.value)}
              disabled={!openingArticle}
            />
          </Group>

          <NumberInput
            label="Količina"
            placeholder="0"
            value={openingCountedQuantity}
            onChange={(value) => setOpeningCountedQuantity(value)}
            min={0}
            step={
              openingArticle && INTEGER_UOMS.includes(openingArticle.base_uom) ? 1 : 0.01
            }
            decimalScale={
              openingArticle && INTEGER_UOMS.includes(openingArticle.base_uom) ? 0 : 2
            }
            disabled={!openingArticle}
          />

          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setOpeningBatchModalOpen(false)
                resetOpeningBatchForm()
              }}
              disabled={openingBatchSubmitting}
            >
              Zatvori
            </Button>
            <Button
              color="blue"
              loading={openingBatchSubmitting}
              onClick={() => void handleOpeningBatchSubmit()}
              disabled={!openingArticle}
            >
              Dodaj šaržu
            </Button>
          </Group>
        </Stack>
      </Modal>

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
