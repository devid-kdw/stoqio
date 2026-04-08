import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  Pagination,
  Paper,
  ScrollArea,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core'
import axios from 'axios'

import {
  inventoryApi,
  type ActiveCount,
  type HistoryItem,
  type InventoryCountType,
} from '../../api/inventory'
import { formatDate } from '../../utils/locale'
import { getApiErrorBody, isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import { ShortageApprovalBadge } from './ShortageApprovalBadge'
import { HISTORY_PAGE_SIZE } from './inventoryFormatters'

export interface HistoryViewProps {
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

export function HistoryView({
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
      await inventoryApi.start(type)
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
                          <ShortageApprovalBadge summary={item.shortage_drafts_summary} />
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
