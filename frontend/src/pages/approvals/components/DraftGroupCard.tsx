import { useState, useCallback, Fragment } from 'react'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Collapse,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  Stack,
  Table,
  Text,
  Textarea,
  UnstyledButton,
} from '@mantine/core'
import { 
  IconCheck, 
  IconChevronDown, 
  IconChevronRight, 
  IconPencil, 
  IconX 
} from '@tabler/icons-react'
import { approvalsApi } from '../../../api/approvals'
import type {
  ApprovalsDraftGroup,
  ApprovalsAggregatedRow,
  ApprovalsOperatorEntry
} from '../../../api/approvals'
import { showErrorToast, showSuccessToast, showWarningToast } from '../../../utils/toasts'
import axios from 'axios'
import { isNetworkOrServerError, runWithRetry } from '../../../utils/http'
import { INTEGER_UOMS } from '../../../utils/uom'
import { getActiveLocale } from '../../../utils/locale'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatQuantity(qty: number, uom: string): string {
  if (INTEGER_UOMS.includes(uom)) {
    return Math.round(qty).toString()
  }
  return qty.toFixed(2)
}

function formatTime(isoString: string | null): string {
  if (!isoString) return '—'
  try {
    return new Date(isoString).toLocaleTimeString(getActiveLocale(), {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return '—'
  }
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DraftGroupCardProps {
  summary: ApprovalsDraftGroup
  isHistory: boolean
  onGroupResolved?: () => void
  onFatalError?: () => void
}

export default function DraftGroupCard({
  summary,
  isHistory,
  onGroupResolved,
  onFatalError,
}: DraftGroupCardProps) {
  const [detail, setDetail] = useState<ApprovalsDraftGroup | null>(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)

  // Modals & Inline Edits
  const [editingRow, setEditingRow] = useState<{ id: number; qty: number | string } | null>(null)
  const [isSavingEdit, setIsSavingEdit] = useState(false)

  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectTarget, setRejectTarget] = useState<'line' | 'group' | null>(null)
  const [rejectLineId, setRejectLineId] = useState<number | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [isRejecting, setIsRejecting] = useState(false)

  const [isApprovingLine, setIsApprovingLine] = useState<number | null>(null)
  const [isApprovingAll, setIsApprovingAll] = useState(false)

  // Expandable row state
  const [expandedRows, setExpandedRows] = useState<Record<number, boolean>>({})

  // Inline Row Errors (e.g., Insufficient stock)
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({})

  // -------------------------------------------------------------------------
  // Fetch Details
  // -------------------------------------------------------------------------
  const fetchDetail = useCallback(async () => {
    try {
      const data = await runWithRetry(() => approvalsApi.getDetail(summary.draft_group_id))
      setDetail(data)
      return data
    } catch (err: unknown) {
      if (isNetworkOrServerError(err)) {
        onFatalError?.()
      } else {
        const message = axios.isAxiosError(err)
          ? err.response?.data?.message || 'Učitavanje detalja drafta nije uspjelo.'
          : 'Učitavanje detalja drafta nije uspjelo.'
        showErrorToast(message)
      }
      return null
    }
  }, [onFatalError, summary.draft_group_id])

  const toggleExpand = () => {
    const next = !expanded
    setExpanded(next)
    if (next && !detail) {
      setLoading(true)
      fetchDetail().finally(() => setLoading(false))
    }
  }

  const toggleRow = (lineId: number) => {
    setExpandedRows((prev) => ({ ...prev, [lineId]: !prev[lineId] }))
  }

  // -------------------------------------------------------------------------
  // Inline Actions
  // -------------------------------------------------------------------------
  const handleGroupResolution = (nextDetail: ApprovalsDraftGroup | null) => {
    if (!onGroupResolved || !nextDetail) {
      return
    }

    const anyPending = nextDetail.rows?.some((row) => row.status === 'PENDING')
    if (!anyPending) {
      onGroupResolved()
    }
  }

  const handleSaveEdit = async () => {
    if (!editingRow) return
    const qty = typeof editingRow.qty === 'string' ? parseFloat(editingRow.qty) : editingRow.qty
    if (isNaN(qty) || qty <= 0) {
      showErrorToast('Količina mora biti veća od nule.')
      return
    }

    setIsSavingEdit(true)
    try {
      const updated = await approvalsApi.updateLine(summary.draft_group_id, editingRow.id, {
        quantity: qty,
      })
      setDetail(updated)
      setEditingRow(null)
      showSuccessToast('Količina ažurirana.')
    } catch (err: unknown) {
      if (isNetworkOrServerError(err)) {
        onFatalError?.()
        return
      }
      const msg = axios.isAxiosError(err)
        ? err.response?.data?.message || 'Ažuriranje količine nije uspjelo.'
        : 'Ažuriranje količine nije uspjelo.'
      showErrorToast(msg)
    } finally {
      setIsSavingEdit(false)
    }
  }

  const handleApproveLine = async (lineId: number) => {
    setIsApprovingLine(lineId)
    setRowErrors(prev => ({ ...prev, [lineId]: '' }))
    try {
      const res = await approvalsApi.approveLine(summary.draft_group_id, lineId)
      if (res.reorder_warning) {
        showWarningToast(`Zaliha za ${res.article_no ?? 'ovaj artikl'} past ce ispod minimalne razine nakon ovog odobrenja.`)
      }
      
      const nextDetail = await fetchDetail()
      handleGroupResolution(nextDetail)
    } catch (err: unknown) {
      if (isNetworkOrServerError(err)) {
        onFatalError?.()
        return
      }
      const msg = axios.isAxiosError(err) ? err.response?.data?.message || 'Odobravanje nije uspjelo.' : 'Odobravanje nije uspjelo.'
      if (msg.includes('Insufficient stock')) {
        setRowErrors(prev => ({ ...prev, [lineId]: 'Nedovoljna zaliha.' }))
      } else {
        showErrorToast(msg)
      }
    } finally {
      setIsApprovingLine(null)
    }
  }

  const handleApproveAll = async () => {
    setIsApprovingAll(true)
    setRowErrors({})
    try {
      const res = await approvalsApi.approveAll(summary.draft_group_id)
      const warnings = res.approved.filter(r => r.reorder_warning).length
      if (warnings > 0) {
        showWarningToast(`Zaliha za ${warnings} artikala past ce ispod minimalne razine nakon ovog odobrenja.`)
      }
      
      if (res.skipped.length > 0) {
        const newErrors = { ...rowErrors }
        res.skipped.forEach(skippedId => {
          newErrors[skippedId] = 'Nedovoljna zaliha.'
        })
        setRowErrors(prev => ({ ...prev, ...newErrors }))
      } else {
        showSuccessToast('Svi redovi uspješno odobreni.')
      }

      const nextDetail = await fetchDetail()
      handleGroupResolution(nextDetail)
    } catch (err: unknown) {
      if (isNetworkOrServerError(err)) {
        onFatalError?.()
        return
      }
      const msg = axios.isAxiosError(err) ? err.response?.data?.message || 'Odobravanje svih nije uspjelo.' : 'Odobravanje svih nije uspjelo.'
      showErrorToast(msg)
    } finally {
      setIsApprovingAll(false)
    }
  }

  const handleOpenRejectLine = (lineId: number) => {
    setRejectTarget('line')
    setRejectLineId(lineId)
    setRejectReason('')
    setRejectModalOpen(true)
  }

  const handleOpenRejectGroup = () => {
    setRejectTarget('group')
    setRejectLineId(null)
    setRejectReason('')
    setRejectModalOpen(true)
  }

  const submitReject = async () => {
    setIsRejecting(true)
    try {
      if (rejectTarget === 'line' && rejectLineId !== null) {
        await approvalsApi.rejectLine(summary.draft_group_id, rejectLineId, { reason: rejectReason })
      } else {
        await approvalsApi.rejectDraft(summary.draft_group_id, { reason: rejectReason })
      }
      setRejectModalOpen(false)
      showSuccessToast('Uspješno odbijeno.')
      const nextDetail = await fetchDetail()
      handleGroupResolution(nextDetail)
    } catch (err: unknown) {
      if (isNetworkOrServerError(err)) {
        onFatalError?.()
        return
      }
      const msg = axios.isAxiosError(err) ? err.response?.data?.message || 'Odbijanje nije uspjelo.' : 'Odbijanje nije uspjelo.'
      showErrorToast(msg)
    } finally {
      setIsRejecting(false)
    }
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  const isBusy = isApprovingAll || isSavingEdit

  return (
    <Paper withBorder radius="md" mb="md" shadow="sm">
      {/* Target Modal */}
      <Modal
        opened={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title={rejectTarget === 'line' ? 'Odbaci redak' : 'Odbaci cijeli draft'}
      >
        <Stack>
          <Textarea
            label="Razlog odbijanja"
            placeholder="Unesite razlog (neobavezno)"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.currentTarget.value)}
            maxLength={500}
            data-autofocus
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRejectModalOpen(false)}>Odustani</Button>
            <Button color="red" onClick={submitReject} loading={isRejecting}>Odbaci</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Header bar */}
      <UnstyledButton onClick={toggleExpand} w="100%" p="md">
        <Group justify="space-between" align="center" wrap="nowrap">
          <Group>
            {expanded ? <IconChevronDown size={20} /> : <IconChevronRight size={20} />}
            <Text fw={600}>{new Date(summary.operational_date).toLocaleDateString(getActiveLocale())}</Text>
            {summary.status === 'PENDING' && <Badge color="yellow">PENDING</Badge>}
            {summary.status === 'APPROVED' && <Badge color="green">APPROVED</Badge>}
            {summary.status === 'REJECTED' && <Badge color="red">REJECTED</Badge>}
            {summary.status === 'PARTIAL' && <Badge color="orange">PARTIAL</Badge>}
          </Group>
          <Text size="sm" c="dimmed">{summary.total_entries} linija</Text>
        </Group>
        {summary.draft_note && (
          <Text size="sm" c="dimmed" mt={4} ml={28}>
            Napomena: {summary.draft_note}
          </Text>
        )}
      </UnstyledButton>

      {/* Expanded Content */}
      <Collapse in={expanded}>
        <Box p="md" pt={0}>
          {loading ? (
            <Group justify="center" py="xl"><Loader size="sm" /></Group>
          ) : detail && detail.rows ? (
            <Stack>
              {!isHistory && (
                <Group justify="space-between" align="center">
                  <Text size="sm" fw={500}>Stavke ({detail.rows.length})</Text>
                  <Group>
                    <Button 
                      variant="outline" 
                      color="red" 
                      size="xs" 
                      onClick={handleOpenRejectGroup}
                      disabled={isBusy}
                    >
                      Odbaci sve
                    </Button>
                    <Button 
                      color="green" 
                      size="xs" 
                      onClick={handleApproveAll}
                      loading={isApprovingAll}
                      disabled={isBusy}
                    >
                      Odobri sve
                    </Button>
                  </Group>
                </Group>
              )}

              <Box style={{ overflowX: 'auto' }}>
                <Table striped highlightOnHover withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th w={40}></Table.Th>
                      <Table.Th>Br. artikla</Table.Th>
                      <Table.Th>Opis</Table.Th>
                      <Table.Th w={100}>Šarža</Table.Th>
                      <Table.Th w={100}>Ukupno</Table.Th>
                      <Table.Th w={60}>JMJ</Table.Th>
                      <Table.Th w={100}>Status</Table.Th>
                      {!isHistory && <Table.Th w={120}>Akcije</Table.Th>}
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {detail.rows.map((row: ApprovalsAggregatedRow) => (
                      <Fragment key={row.line_id}>
                        {/* Parent Row */}
                        <Table.Tr bg={row.status !== 'PENDING' && !isHistory ? 'gray.0' : undefined}>
                          <Table.Td>
                            <ActionIcon variant="subtle" onClick={() => toggleRow(row.line_id)}>
                              {expandedRows[row.line_id] ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
                            </ActionIcon>
                          </Table.Td>
                          <Table.Td>{row.article_no}</Table.Td>
                          <Table.Td>
                            <Stack gap={2}>
                              <Text size="sm">{row.description}</Text>
                              {row.status === 'REJECTED' && row.rejection_reason && (
                                <Text size="xs" c="dimmed" fs="italic">
                                  Razlog: {row.rejection_reason}
                                </Text>
                              )}
                            </Stack>
                          </Table.Td>
                          <Table.Td>{row.batch_code}</Table.Td>
                          <Table.Td>
                            {editingRow?.id === row.line_id ? (
                              <Group wrap="nowrap" gap={4}>
                                <NumberInput
                                  size="xs"
                                  w={80}
                                  value={editingRow.qty}
                                  onChange={(val) => setEditingRow(prev => prev ? { ...prev, qty: val } : null)}
                                  min={0}
                                />
                                <ActionIcon 
                                  color="green" 
                                  onClick={handleSaveEdit} 
                                  loading={isSavingEdit}
                                >
                                  <IconCheck size={16} />
                                </ActionIcon>
                                <ActionIcon 
                                  color="red" 
                                  onClick={() => setEditingRow(null)}
                                  disabled={isSavingEdit}
                                >
                                  <IconX size={16} />
                                </ActionIcon>
                              </Group>
                            ) : (
                              formatQuantity(row.total_quantity, row.uom)
                            )}
                          </Table.Td>
                          <Table.Td>{row.uom}</Table.Td>
                          <Table.Td>
                            <Badge 
                              color={
                                row.status === 'PENDING' ? 'yellow' : 
                                row.status === 'APPROVED' ? 'green' : 
                                row.status === 'REJECTED' ? 'red' : 'orange'
                              }
                              variant={row.status === 'PENDING' ? 'light' : 'filled'}
                            >
                              {row.status}
                            </Badge>
                          </Table.Td>
                          {!isHistory && (
                            <Table.Td>
                              {row.status === 'PENDING' && !editingRow ? (
                                <Stack gap={4} align="flex-start">
                                  <Group gap={4} wrap="nowrap">
                                    <ActionIcon 
                                      color="blue" 
                                      onClick={() => setEditingRow({ id: row.line_id, qty: row.total_quantity })}
                                      disabled={isBusy}
                                    >
                                      <IconPencil size={16} />
                                    </ActionIcon>
                                    <ActionIcon 
                                      color="green" 
                                      onClick={() => handleApproveLine(row.line_id)}
                                      loading={isApprovingLine === row.line_id}
                                      disabled={isBusy || isApprovingLine !== null}
                                    >
                                      <IconCheck size={16} />
                                    </ActionIcon>
                                    <ActionIcon 
                                      color="red" 
                                      onClick={() => handleOpenRejectLine(row.line_id)}
                                      disabled={isBusy}
                                    >
                                      <IconX size={16} />
                                    </ActionIcon>
                                  </Group>
                                  {rowErrors[row.line_id] && (
                                    <Text color="red" size="xs">{rowErrors[row.line_id]}</Text>
                                  )}
                                </Stack>
                              ) : null}
                            </Table.Td>
                          )}
                        </Table.Tr>
                        
                        {/* Nested Entries */}
                        {expandedRows[row.line_id] && (
                          <Table.Tr>
                            <Table.Td colSpan={!isHistory ? 8 : 7} p={0}>
                              <Box bg="gray.0" p="sm" pl={48}>
                                <Table withTableBorder={false}>
                                  <Table.Thead>
                                    <Table.Tr>
                                      <Table.Th w={100}>Vrijeme</Table.Th>
                                      <Table.Th w={150}>Operater</Table.Th>
                                      <Table.Th w={100}>Šifra</Table.Th>
                                      <Table.Th w={100}>Količina</Table.Th>
                                      <Table.Th>Status</Table.Th>
                                    </Table.Tr>
                                  </Table.Thead>
                                  <Table.Tbody>
                                    {row.entries.map((e: ApprovalsOperatorEntry) => (
                                      <Table.Tr key={e.id}>
                                        <Table.Td>{formatTime(e.created_at)}</Table.Td>
                                        <Table.Td>{e.operator}</Table.Td>
                                        <Table.Td>{e.employee_id_ref || '—'}</Table.Td>
                                        <Table.Td>{formatQuantity(e.quantity, row.uom)}</Table.Td>
                                        <Table.Td>
                                          <Stack gap={2}>
                                            <Text size="sm">{e.status}</Text>
                                            {e.status === 'REJECTED' && e.rejection_reason && (
                                              <Text size="xs" c="dimmed" fs="italic">
                                                Razlog: {e.rejection_reason}
                                              </Text>
                                            )}
                                          </Stack>
                                        </Table.Td>
                                      </Table.Tr>
                                    ))}
                                  </Table.Tbody>
                                </Table>
                              </Box>
                            </Table.Td>
                          </Table.Tr>
                        )}
                      </Fragment>
                    ))}
                  </Table.Tbody>
                </Table>
              </Box>
            </Stack>
          ) : (
            <Text ta="center" c="dimmed">Nema dostupnog sadržaja.</Text>
          )}
        </Box>
      </Collapse>
    </Paper>
  )
}
