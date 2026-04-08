import { useState } from 'react'
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
import { IconArrowLeft } from '@tabler/icons-react'

import type { CountDetail } from '../../api/inventory'
import { formatDate, formatDateTime } from '../../utils/locale'
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

  const displayLines = count.lines.filter((line) => {
    if (resolutionFilter === 'ALL') return true
    return line.resolution === resolutionFilter
  })

  const s = count.summary
  const isOpeningCount = count.type === 'OPENING'
  const primaryAdjustmentLabel = isOpeningCount ? 'Početno stanje postavljeno' : 'Višak dodan'
  const primaryAdjustmentValue = isOpeningCount
    ? s.opening_stock_set ?? s.surplus_added ?? 0
    : s.surplus_added

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
