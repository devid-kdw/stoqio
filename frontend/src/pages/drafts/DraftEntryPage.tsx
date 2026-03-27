import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Group,
  Loader,
  NumberInput,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { IconCheck, IconPencil, IconTrash, IconX } from '@tabler/icons-react'
import { v4 as uuidv4 } from 'uuid'
import axios from 'axios'

import { articlesApi, type ArticleBatch, type ArticleLookupResult } from '../../api/articles'
import { draftsApi, type DraftGroup, type DraftLine, type MyDraftLine } from '../../api/drafts'
import FullPageState from '../../components/shared/FullPageState'
import { CONNECTION_ERROR_MESSAGE, isNetworkOrServerError } from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import { INTEGER_UOMS } from '../../utils/uom'

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
    return new Date(isoString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return '—'
  }
}

// ---------------------------------------------------------------------------
// Sub-types
// ---------------------------------------------------------------------------

interface ResolvedArticle {
  id: number
  article_no: string
  description: string
  base_uom: string
  has_batch: boolean
  batches: ArticleBatch[]
}

interface FormErrors {
  articleNo?: string
  quantity?: string
  batch?: string
}

// ---------------------------------------------------------------------------
// Inline row state types
// ---------------------------------------------------------------------------

type RowAction =
  | { type: 'idle' }
  | { type: 'editing'; editQty: number | string; saving: boolean }
  | { type: 'confirming-delete'; deleting: boolean }

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DraftEntryPage() {

  // --- page-level data loading state ---
  const [lines, setLines] = useState<DraftLine[]>([])
  const [draftGroup, setDraftGroup] = useState<DraftGroup | null>(null)
  const [myLines, setMyLines] = useState<MyDraftLine[]>([])
  const [pageLoading, setPageLoading] = useState(true)
  const [pageError, setPageError] = useState(false)

  // --- form state ---
  const [articleNo, setArticleNo] = useState('')
  const [resolvedArticle, setResolvedArticle] = useState<ResolvedArticle | null>(null)
  const [articleLookupState, setArticleLookupState] = useState<
    'idle' | 'loading' | 'found' | 'not-found'
  >('idle')
  const [quantity, setQuantity] = useState<number | string>('')
  const [batchId, setBatchId] = useState<string | null>(null)
  const [employeeId, setEmployeeId] = useState('')
  const [draftNote, setDraftNote] = useState('')
  const [formErrors, setFormErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitRetried, setSubmitRetried] = useState(false)
  const [submitConnectionError, setSubmitConnectionError] = useState(false)
  const [savingDraftNote, setSavingDraftNote] = useState(false)

  // --- inline row actions ---
  const [rowActions, setRowActions] = useState<Record<number, RowAction>>({})

  // --- refs ---
  const articleInputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const refreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ---------------------------------------------------------------------------
  // Load today's lines on mount
  // ---------------------------------------------------------------------------

  // ---------------------------------------------------------------------------
  // Load my lines (dedicated /drafts/my endpoint)
  // ---------------------------------------------------------------------------

  const loadMyLines = useCallback(async () => {
    const attemptLoad = async (isRetry: boolean): Promise<void> => {
      try {
        const data = await draftsApi.getMyLines()
        setMyLines(data.lines)
      } catch (err) {
        if (!isRetry && isNetworkOrServerError(err)) {
          await attemptLoad(true)
          return
        }
        setPageError(true)
      }
    }
    await attemptLoad(false)
  }, [])

  const loadLines = useCallback(async () => {
    setPageLoading(true)
    setPageError(false)

    const attemptLoad = async (isRetry: boolean): Promise<void> => {
      try {
        const data = await draftsApi.getTodayLines()
        setLines(data.items)
        setDraftGroup(data.draft_group)
        setDraftNote(data.draft_group?.draft_note ?? '')
      } catch (err) {
        if (!isRetry && isNetworkOrServerError(err)) {
          await attemptLoad(true)
          return
        }
        setPageError(true)
      }
    }

    try {
      await attemptLoad(false)
    } finally {
      setPageLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadLines()
    void loadMyLines()
  }, [loadLines, loadMyLines])

  // 60-second auto-refresh for personal-status section
  useEffect(() => {
    refreshIntervalRef.current = setInterval(() => {
      void loadMyLines()
    }, 60_000)
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
        refreshIntervalRef.current = null
      }
    }
  }, [loadMyLines])

  // ---------------------------------------------------------------------------
  // Article lookup
  // ---------------------------------------------------------------------------

  const lookupArticle = useCallback(async (query: string) => {
    const trimmed = query.trim()
    if (!trimmed) {
      setResolvedArticle(null)
      setArticleLookupState('idle')
      setBatchId(null)
      setFormErrors((prev) => ({ ...prev, articleNo: undefined, batch: undefined }))
      return
    }

    setArticleLookupState('loading')
    setFormErrors((prev) => ({ ...prev, articleNo: undefined, batch: undefined }))

    const attemptLookup = async (isRetry: boolean): Promise<void> => {
      try {
        const result: ArticleLookupResult = await articlesApi.lookup(trimmed)
        const resolved: ResolvedArticle = {
          id: result.id,
          article_no: result.article_no,
          description: result.description,
          base_uom: result.base_uom,
          has_batch: result.has_batch,
          batches: result.batches ?? [],
        }
        setResolvedArticle(resolved)
        setArticleLookupState('found')
        setBatchId(null)

        // If batch article but no batches available, show inline error
        if (result.has_batch && (!result.batches || result.batches.length === 0)) {
          setFormErrors((prev) => ({
            ...prev,
            batch: 'No batches available for this article.',
          }))
        }
      } catch (err) {
        if (isNetworkOrServerError(err)) {
          if (!isRetry) {
            await attemptLookup(true)
            return
          }

          setPageError(true)
          return
        }

        setResolvedArticle(null)
        setArticleLookupState('not-found')
        setBatchId(null)
        setFormErrors((prev) => ({
          ...prev,
          articleNo: 'Article not found.',
          batch: undefined,
        }))
      }
    }

    await attemptLookup(false)
  }, [])

  const handleArticleNoChange = (value: string) => {
    setArticleNo(value)
    // Clear resolved article immediately when text changes
    if (resolvedArticle && value.trim().toUpperCase() !== resolvedArticle.article_no) {
      setResolvedArticle(null)
      setArticleLookupState('idle')
      setBatchId(null)
    }
    setFormErrors((prev) => ({ ...prev, articleNo: undefined, batch: undefined }))

    // Debounced lookup
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      void lookupArticle(value)
    }, 400)
  }

  const handleArticleNoBlur = () => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (articleLookupState !== 'found') {
      void lookupArticle(articleNo)
    }
  }

  // ---------------------------------------------------------------------------
  // Form validation
  // ---------------------------------------------------------------------------

  const validate = (): FormErrors => {
    const errors: FormErrors = {}

    if (!articleNo.trim() || articleLookupState !== 'found' || !resolvedArticle) {
      if (!articleNo.trim()) {
        errors.articleNo = 'Article number is required.'
      } else if (articleLookupState === 'not-found') {
        errors.articleNo = 'Article not found.'
      } else if (articleLookupState !== 'found') {
        errors.articleNo = 'Article not resolved. Please wait for lookup.'
      }
    }

    const qty = typeof quantity === 'string' ? parseFloat(quantity) : quantity
    if (quantity === '' || quantity === null || quantity === undefined) {
      errors.quantity = 'Quantity is required.'
    } else if (isNaN(qty) || qty <= 0) {
      errors.quantity = 'Quantity must be greater than 0.'
    }

    if (resolvedArticle?.has_batch) {
      if (!resolvedArticle.batches || resolvedArticle.batches.length === 0) {
        errors.batch = 'No batches available for this article.'
      } else if (!batchId) {
        errors.batch = 'Batch is required.'
      }
    }

    return errors
  }

  // ---------------------------------------------------------------------------
  // Form submit
  // ---------------------------------------------------------------------------

  const clearForm = () => {
    setArticleNo('')
    setResolvedArticle(null)
    setArticleLookupState('idle')
    setQuantity('')
    setBatchId(null)
    setEmployeeId('')
    setFormErrors({})
    setSubmitRetried(false)
    // Focus the article input for fast repeated entry
    setTimeout(() => articleInputRef.current?.focus(), 50)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const errors = validate()
    setFormErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSubmitting(true)
    setSubmitConnectionError(false)

    const qty = typeof quantity === 'string' ? parseFloat(quantity) : quantity
    // Generate once — reused on retry so the backend can deduplicate via client_event_id
    const eventId = uuidv4()

    const attemptSubmit = async (currentEventId: string): Promise<DraftLine> => {
      return draftsApi.addLine({
        article_id: resolvedArticle!.id,
        batch_id: batchId ? parseInt(batchId, 10) : null,
        quantity: qty,
        uom: resolvedArticle!.base_uom,
        employee_id_ref: employeeId.trim() || undefined,
        draft_note: draftNote,
        source: 'manual' as const,
        client_event_id: currentEventId,
      })
    }

    try {
      let newLine: DraftLine
      try {
        newLine = await attemptSubmit(eventId)
      } catch (err) {
        if (!submitRetried && isNetworkOrServerError(err)) {
          setSubmitRetried(true)
          // Retry with same event ID for idempotency
          newLine = await attemptSubmit(eventId)
        } else {
          throw err
        }
      }

      if (draftGroup) {
        setDraftGroup({
          ...draftGroup,
          draft_note: draftNote.trim() || null,
        })
        setLines((prev) => [newLine, ...prev])
      } else {
        await loadLines()
      }
      void loadMyLines()
      clearForm()
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setSubmitConnectionError(true)
        return
      }
      const message = axios.isAxiosError(err)
        ? err.response?.data?.message || 'Failed to add entry. Please try again.'
        : 'Failed to add entry. Please try again.'
      showErrorToast(message)
    } finally {
      setSubmitting(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Shared daily draft note
  // ---------------------------------------------------------------------------

  const saveDraftNote = async () => {
    if (!draftGroup) {
      return
    }

    setSavingDraftNote(true)

    let retried = false
    const attempt = () => draftsApi.updateGroup({ draft_note: draftNote })

    try {
      let updatedGroup: DraftGroup
      try {
        updatedGroup = await attempt()
      } catch (err) {
        if (!retried && isNetworkOrServerError(err)) {
          retried = true
          updatedGroup = await attempt()
        } else {
          throw err
        }
      }

      setDraftGroup(updatedGroup)
      setDraftNote(updatedGroup.draft_note ?? '')
      showSuccessToast('Napomena ažurirana.')
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setPageError(true)
        return
      }

      const message = axios.isAxiosError(err)
        ? err.response?.data?.message || 'Failed to update draft note.'
        : 'Failed to update draft note.'
      showErrorToast(message)
    } finally {
      setSavingDraftNote(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Inline edit
  // ---------------------------------------------------------------------------

  const startEdit = (line: DraftLine) => {
    setRowActions((prev) => ({
      ...prev,
      [line.id]: { type: 'editing', editQty: line.quantity, saving: false },
    }))
  }

  const cancelEdit = (lineId: number) => {
    setRowActions((prev) => ({ ...prev, [lineId]: { type: 'idle' } }))
  }

  const saveEdit = async (lineId: number) => {
    const action = rowActions[lineId]
    if (!action || action.type !== 'editing') return

    const qty =
      typeof action.editQty === 'string' ? parseFloat(action.editQty) : action.editQty
    if (isNaN(qty) || qty <= 0) {
      showErrorToast('Quantity must be greater than 0.')
      return
    }

    setRowActions((prev) => ({
      ...prev,
      [lineId]: { ...action, saving: true },
    }))

    let retried = false
    const attempt = () => draftsApi.updateLine(lineId, { quantity: qty })

    try {
      let updated: DraftLine
      try {
        updated = await attempt()
      } catch (err) {
        if (!retried && isNetworkOrServerError(err)) {
          retried = true
          updated = await attempt()
        } else {
          throw err
        }
      }

      setLines((prev) => prev.map((l) => (l.id === lineId ? updated : l)))
      void loadMyLines()
      setRowActions((prev) => ({ ...prev, [lineId]: { type: 'idle' } }))
      showSuccessToast('Unos ažuriran.')
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setPageError(true)
        return
      }
      const message = axios.isAxiosError(err)
        ? err.response?.data?.message || 'Failed to update entry.'
        : 'Failed to update entry.'
      showErrorToast(message)
      setRowActions((prev) => ({
        ...prev,
        [lineId]: { ...action, saving: false },
      }))
    }
  }

  // ---------------------------------------------------------------------------
  // Inline delete
  // ---------------------------------------------------------------------------

  const startDelete = (lineId: number) => {
    setRowActions((prev) => ({
      ...prev,
      [lineId]: { type: 'confirming-delete', deleting: false },
    }))
  }

  const cancelDelete = (lineId: number) => {
    setRowActions((prev) => ({ ...prev, [lineId]: { type: 'idle' } }))
  }

  const confirmDelete = async (lineId: number) => {
    const action = rowActions[lineId]
    if (!action || action.type !== 'confirming-delete') return

    setRowActions((prev) => ({
      ...prev,
      [lineId]: { ...action, deleting: true },
    }))

    let retried = false
    const attempt = () => draftsApi.deleteLine(lineId)

    try {
      try {
        await attempt()
      } catch (err) {
        if (!retried && isNetworkOrServerError(err)) {
          retried = true
          await attempt()
        } else {
          throw err
        }
      }

      setLines((prev) => prev.filter((l) => l.id !== lineId))
      void loadMyLines()
      setRowActions((prev) => {
        const next = { ...prev }
        delete next[lineId]
        return next
      })
      showSuccessToast('Unos obrisan.')
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setPageError(true)
        return
      }
      const message = axios.isAxiosError(err)
        ? err.response?.data?.message || 'Failed to delete entry.'
        : 'Failed to delete entry.'
      showErrorToast(message)
      setRowActions((prev) => ({
        ...prev,
        [lineId]: { ...action, deleting: false },
      }))
    }
  }

  // ---------------------------------------------------------------------------
  // Render: page-level states
  // ---------------------------------------------------------------------------

  if (pageLoading) {
    return (
      <FullPageState
        title="Učitavanje…"
        message="Dohvaćanje unosa za danas."
        loading
      />
    )
  }

  if (pageError) {
    return (
      <FullPageState
        title="Greška povezivanja"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => window.location.reload()}
      />
    )
  }

  if (submitConnectionError) {
    return (
      <FullPageState
        title="Greška povezivanja"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => window.location.reload()}
      />
    )
  }

  // ---------------------------------------------------------------------------
  // Render: batch options for the dropdown
  // ---------------------------------------------------------------------------

  const batchOptions =
    resolvedArticle?.has_batch && resolvedArticle.batches.length > 0
      ? resolvedArticle.batches.map((b) => ({
          value: String(b.id),
          label: `${b.batch_code} (exp: ${b.expiry_date.slice(0, 10)})`,
        }))
      : []

  // ---------------------------------------------------------------------------
  // Render: main page
  // ---------------------------------------------------------------------------

  return (
    <Box p="xl">
      {/* ------------------------------------------------------------------ */}
      {/* Page header + status badge                                          */}
      {/* ------------------------------------------------------------------ */}
      <Group mb="xl" align="center" justify="space-between">
        <Stack gap={4}>
          <Title order={2}>Unos izlaza</Title>
          <Text c="dimmed" size="sm">
            Upišite ili skenirajte artikl i unesite količinu
          </Text>
        </Stack>
        <Badge color="green" size="lg" variant="light">
          OTVORENO
        </Badge>
      </Group>

      {/* ------------------------------------------------------------------ */}
      {/* Entry form                                                          */}
      {/* ------------------------------------------------------------------ */}
      <Paper withBorder radius="md" p="xl" mb="xl">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Title order={4} mb={4}>
              Novi unos
            </Title>

            {/* Row 1: Article input + Quantity */}
            <Group align="flex-start" grow>
              {/* Article number */}
              <Box style={{ flex: 2 }}>
                <TextInput
                  ref={articleInputRef}
                  label="Broj artikla"
                  placeholder="Unesite ili skenirajte broj artikla"
                  value={articleNo}
                  onChange={(e) => handleArticleNoChange(e.currentTarget.value)}
                  onBlur={handleArticleNoBlur}
                  error={formErrors.articleNo}
                  rightSection={articleLookupState === 'loading' ? <Loader size="xs" /> : null}
                  autoComplete="off"
                  data-autofocus
                />
                {/* Article description — auto-populated, read-only */}
                {resolvedArticle && articleLookupState === 'found' && (
                  <Text size="sm" c="dimmed" mt={4} ml={2}>
                    {resolvedArticle.description}
                  </Text>
                )}
              </Box>

              {/* Quantity */}
              <Box style={{ flex: 1 }}>
                <NumberInput
                  label="Količina"
                  placeholder="0"
                  min={0.001}
                  step={
                    resolvedArticle && INTEGER_UOMS.includes(resolvedArticle.base_uom) ? 1 : 0.01
                  }
                  decimalScale={
                    resolvedArticle && INTEGER_UOMS.includes(resolvedArticle.base_uom) ? 0 : 3
                  }
                  value={quantity}
                  onChange={setQuantity}
                  error={formErrors.quantity}
                  rightSection={
                    resolvedArticle ? (
                      <Text size="xs" c="dimmed" pr={4}>
                        {resolvedArticle.base_uom}
                      </Text>
                    ) : null
                  }
                />
              </Box>
            </Group>

            {/* Row 2: Batch dropdown — shown only when article has batches */}
            {resolvedArticle?.has_batch && (
              <Select
                label="Šarža"
                placeholder="Odaberite šaržu (FEFO)"
                data={batchOptions}
                value={batchId}
                onChange={setBatchId}
                error={formErrors.batch}
                disabled={batchOptions.length === 0}
                nothingFoundMessage="Nema dostupnih šarži"
              />
            )}

            {/* Row 3: Optional employee reference + submit */}
            <Group align="flex-end" justify="space-between" style={{ gap: '0.75rem' }}>
              <Box style={{ width: 220 }}>
                <TextInput
                  size="sm"
                  label="Šifra zaposlenika"
                  labelProps={{
                    style: {
                      color: 'var(--mantine-color-gray-6)',
                      fontSize: '0.75rem',
                    },
                  }}
                  placeholder="npr. 0042"
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.currentTarget.value)}
                />
              </Box>
              <Button type="submit" loading={submitting} disabled={submitting} size="md">
                Dodaj
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>

      {/* ------------------------------------------------------------------ */}
      {/* Today's lines table                                                 */}
      {/* ------------------------------------------------------------------ */}
      <Paper withBorder radius="md" p="xl">
        <Title order={4} mb="md">
          Unosi za danas
        </Title>

        <Stack gap="xs" mb="lg">
            <Textarea
              label="Napomena za današnji draft"
            placeholder="Nije obavezno (maks 1000 znakova)"
            value={draftNote}
            onChange={(event) => {
              if (event.currentTarget.value.length <= 1000) {
                setDraftNote(event.currentTarget.value)
              }
            }}
            autosize
            minRows={2}
            maxLength={1000}
          />
          <Group justify="space-between" align="center">
            <Text c="dimmed" size="sm">
              {draftGroup
                ? 'Napomena vrijedi za cijeli današnji draft.'
                : 'Napomena će se spremiti s prvim uspješnim unosom.'}
            </Text>
            <Button
              variant="light"
              onClick={saveDraftNote}
              loading={savingDraftNote}
              disabled={!draftGroup || savingDraftNote}
            >
              Spremi napomenu
            </Button>
          </Group>
        </Stack>

        {lines.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            Nema unosa za danas.
          </Text>
        ) : (
          <Box style={{ overflowX: 'auto' }}>
            <Table striped highlightOnHover withColumnBorders withTableBorder={false}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th style={{ width: 64 }}>Vrijeme</Table.Th>
                  <Table.Th style={{ width: 96 }}>Br. artikla</Table.Th>
                  <Table.Th>Opis</Table.Th>
                  <Table.Th style={{ width: 84 }}>Količina</Table.Th>
                  <Table.Th style={{ width: 48 }}>JMJ</Table.Th>
                  <Table.Th style={{ width: 96 }}>Šarža</Table.Th>
                  <Table.Th style={{ width: 88 }}>Unio</Table.Th>
                  <Table.Th style={{ width: 68 }}>Akcije</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {lines.map((line) => {
                  const action = rowActions[line.id] ?? { type: 'idle' }
                  const isApproved = line.status === 'APPROVED'

                  if (action.type === 'editing') {
                    return (
                      <Table.Tr key={line.id} bg="blue.0">
                        <Table.Td>{formatTime(line.created_at)}</Table.Td>
                        <Table.Td>{line.article_no ?? '—'}</Table.Td>
                        <Table.Td>{line.description ?? '—'}</Table.Td>
                        <Table.Td>
                          <NumberInput
                            size="xs"
                            value={action.editQty}
                            onChange={(val) =>
                              setRowActions((prev) => ({
                                ...prev,
                                [line.id]: { ...action, editQty: val },
                              }))
                            }
                            min={0.001}
                            step={INTEGER_UOMS.includes(line.uom) ? 1 : 0.01}
                            decimalScale={INTEGER_UOMS.includes(line.uom) ? 0 : 3}
                            style={{ width: 90 }}
                            disabled={action.saving}
                          />
                        </Table.Td>
                        <Table.Td>{line.uom}</Table.Td>
                        <Table.Td>{line.batch_code ?? '—'}</Table.Td>
                        <Table.Td>{line.created_by ?? '—'}</Table.Td>
                        <Table.Td>
                          <Group gap="xs" wrap="nowrap">
                            <Tooltip label="Spremi">
                              <ActionIcon
                                color="green"
                                variant="light"
                                size="sm"
                                onClick={() => saveEdit(line.id)}
                                loading={action.saving}
                                disabled={action.saving}
                              >
                                <IconCheck size={14} />
                              </ActionIcon>
                            </Tooltip>
                            <Tooltip label="Odustani">
                              <ActionIcon
                                color="gray"
                                variant="light"
                                size="sm"
                                onClick={() => cancelEdit(line.id)}
                                disabled={action.saving}
                              >
                                <IconX size={14} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    )
                  }

                  if (action.type === 'confirming-delete') {
                    return (
                      <Table.Tr key={line.id} bg="red.0">
                        <Table.Td colSpan={7}>
                          <Text size="sm" c="red.7">
                            Obrisati ovaj unos? Ova radnja se ne može poništiti.
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Group gap="xs" wrap="nowrap">
                            <Button
                              color="red"
                              size="xs"
                              onClick={() => confirmDelete(line.id)}
                              loading={action.deleting}
                              disabled={action.deleting}
                            >
                              Potvrdi
                            </Button>
                            <Button
                              color="gray"
                              variant="light"
                              size="xs"
                              onClick={() => cancelDelete(line.id)}
                              disabled={action.deleting}
                            >
                              Odustani
                            </Button>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    )
                  }

                  // Idle row
                  return (
                    <Table.Tr key={line.id}>
                      <Table.Td>{formatTime(line.created_at)}</Table.Td>
                      <Table.Td>{line.article_no ?? '—'}</Table.Td>
                      <Table.Td>{line.description ?? '—'}</Table.Td>
                      <Table.Td>{formatQuantity(line.quantity, line.uom)}</Table.Td>
                      <Table.Td>{line.uom}</Table.Td>
                      <Table.Td>{line.batch_code ?? '—'}</Table.Td>
                      <Table.Td>{line.created_by ?? '—'}</Table.Td>
                      <Table.Td>
                        {isApproved ? (
                          <Text size="xs" c="dimmed">
                            Odobreno
                          </Text>
                        ) : (
                          <Group gap="xs" wrap="nowrap">
                            <Tooltip label="Uredi">
                              <ActionIcon
                                color="blue"
                                variant="light"
                                size="sm"
                                onClick={() => startEdit(line)}
                              >
                                <IconPencil size={14} />
                              </ActionIcon>
                            </Tooltip>
                            <Tooltip label="Obriši">
                              <ActionIcon
                                color="red"
                                variant="light"
                                size="sm"
                                onClick={() => startDelete(line.id)}
                              >
                                <IconTrash size={14} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  )
                })}
              </Table.Tbody>
            </Table>
          </Box>
        )}
      </Paper>

      {/* ------------------------------------------------------------------ */}
      {/* My entries today                                                    */}
      {/* ------------------------------------------------------------------ */}
      <Paper withBorder radius="md" p="xl" mt="xl">
        <Title order={4} mb="md">
          Moji unosi danas
        </Title>
        {myLines.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            Nema vaših unosa danas.
          </Text>
        ) : (
          <Stack gap="xs">
            {myLines.map((line) => (
              <Box key={line.id} style={{ borderBottom: '1px solid var(--mantine-color-gray-2)', paddingBottom: '0.5rem' }}>
                <Group justify="space-between" align="flex-start">
                  <Stack gap={2}>
                    <Text size="sm" fw={500}>
                      {line.article_no ?? '—'} — {line.description ?? '—'}
                    </Text>
                    <Text size="sm" c="dimmed">
                      {formatQuantity(line.quantity, line.uom)} {line.uom}
                      {line.batch_code ? ` · ${line.batch_code}` : ''}
                    </Text>
                  </Stack>
                  <Badge
                    color={
                      line.status === 'DRAFT'
                        ? 'yellow'
                        : line.status === 'APPROVED'
                        ? 'green'
                        : line.status === 'REJECTED'
                        ? 'red'
                        : 'gray'
                    }
                    variant={line.status === 'DRAFT' ? 'light' : 'filled'}
                  >
                    {line.status === 'DRAFT'
                      ? 'Na čekanju'
                      : line.status === 'APPROVED'
                      ? 'Odobreno'
                      : line.status === 'REJECTED'
                      ? 'Odbijeno'
                      : line.status}
                  </Badge>
                </Group>
                {line.status === 'REJECTED' && line.rejection_reason && (
                  <Text size="xs" c="dimmed" fs="italic" mt={4}>
                    Razlog: {line.rejection_reason}
                  </Text>
                )}
              </Box>
            ))}
          </Stack>
        )}
      </Paper>
    </Box>
  )
}
