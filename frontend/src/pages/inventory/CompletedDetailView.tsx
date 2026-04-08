import { useMemo, useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Group,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core'
import { IconArrowLeft, IconChevronDown, IconChevronRight } from '@tabler/icons-react'

import type { CountDetail } from '../../api/inventory'
import { formatDate, formatDateTime } from '../../utils/locale'
import { buildActiveDisplayItems } from './activeCountDisplay'
import { fmtQty, fmtDiff } from './inventoryFormatters'
import { ResolutionBadge } from './ResolutionBadge'

const RESOLUTION_OPTIONS = [
  { value: 'ALL', label: 'Sve stavke' },
  { value: 'NO_CHANGE', label: 'Bez promjena' },
  { value: 'SURPLUS_ADDED', label: 'Višak dodan' },
  { value: 'SHORTAGE_DRAFT_CREATED', label: 'Manjkovi' },
  { value: 'OPENING_STOCK_SET', label: 'Početno stanje' },
]

export interface CompletedDetailViewProps {
  count: CountDetail
  onBack: () => void
}

export function CompletedDetailView({ count, onBack }: CompletedDetailViewProps) {
  const [resolutionFilter, setResolutionFilter] = useState('ALL')
  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set())

  const displayLines = count.lines.filter((line) => {
    if (resolutionFilter === 'ALL') return true
    return line.resolution === resolutionFilter
  })
  const displayItems = useMemo(() => buildActiveDisplayItems(displayLines), [displayLines])

  const s = count.summary
  const isOpeningCount = count.type === 'OPENING'
  const primaryAdjustmentLabel = isOpeningCount ? 'Početno stanje postavljeno' : 'Višak dodan'
  const primaryAdjustmentValue = isOpeningCount
    ? s.opening_stock_set ?? s.surplus_added ?? 0
    : s.surplus_added

  function toggleArticle(articleId: number) {
    setExpandedArticles((prev) => {
      const next = new Set(prev)
      if (next.has(articleId)) next.delete(articleId)
      else next.add(articleId)
      return next
    })
  }

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
          <Badge color="violet" size="lg">Inicijalna inventura</Badge>
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
            {primaryAdjustmentLabel}
          </Text>
          <Text size="xl" fw={700} c={isOpeningCount ? 'violet' : 'blue'}>
            {primaryAdjustmentValue}
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
                <Table.Th>Šarža</Table.Th>
                <Table.Th>Rok valjanosti</Table.Th>
                <Table.Th>Stanje sustava</Table.Th>
                <Table.Th>JMJ</Table.Th>
                <Table.Th>Prebrojano</Table.Th>
                <Table.Th>Razlika</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {displayItems.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={9}>
                    <Text c="dimmed" ta="center" py="md">
                      Nema stavki za odabrani filter.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                displayItems.flatMap((item) => {
                  if (item.kind === 'non-batch') {
                    const line = item.line
                    return [
                      <Table.Tr key={line.line_id}>
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
                      </Table.Tr>,
                    ]
                  }

                  const { group } = item
                  const isExpanded = expandedArticles.has(group.article_id)
                  const totalSystemQty = group.lines.reduce((sum, line) => sum + line.system_quantity, 0)
                  const totalCountedQty = group.lines.every((line) => line.counted_quantity !== null)
                    ? group.lines.reduce((sum, line) => sum + (line.counted_quantity ?? 0), 0)
                    : null
                  const totalDiff =
                    totalCountedQty !== null ? totalCountedQty - totalSystemQty : null
                  const summaryText = `${group.lines.length} šarža / ${fmtQty(totalSystemQty, group.decimal_display)} ${group.uom} ukupno`
                  const resolutionValues = Array.from(
                    new Set(group.lines.map((line) => line.resolution).filter(Boolean))
                  )
                  const groupResolution =
                    resolutionValues.length === 1 ? (resolutionValues[0] ?? null) : null
                  const rows = [
                    <Table.Tr
                      key={`group-${group.article_id}`}
                      style={{ cursor: 'pointer' }}
                      onClick={() => toggleArticle(group.article_id)}
                    >
                      <Table.Td>
                        <Group gap="xs" wrap="nowrap">
                          {isExpanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
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
                      <Table.Td>
                        {totalDiff !== null ? (
                          <Text
                            size="sm"
                            fw={500}
                            c={
                              totalDiff > 0
                                ? 'blue'
                                : totalDiff < 0
                                  ? 'yellow.7'
                                  : 'green'
                            }
                          >
                            {fmtDiff(totalDiff, group.decimal_display)}
                          </Text>
                        ) : (
                          '—'
                        )}
                      </Table.Td>
                      <Table.Td>
                        {groupResolution ? (
                          <ResolutionBadge resolution={groupResolution} />
                        ) : (
                          <Text size="sm" c="dimmed">
                            Više statusa
                          </Text>
                        )}
                      </Table.Td>
                    </Table.Tr>,
                  ]

                  if (isExpanded) {
                    for (const line of group.lines) {
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
                      )
                    }
                  }

                  return rows
                })
              )}
            </Table.Tbody>
          </Table>
        </ScrollArea>
      </Paper>
    </Stack>
  )
}
