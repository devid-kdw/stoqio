import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Checkbox,
  Divider,
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
  Textarea,
  TextInput,
  Title,
} from '@mantine/core'
import { IconArrowLeft } from '@tabler/icons-react'
import axios from 'axios'

import {
  employeesApi,
  type Employee,
  type IssuanceArticleLookupItem,
  type IssuanceCheckResult,
  type IssuanceHistoryItem,
  type QuotaRow,
} from '../../api/employees'
import FullPageState from '../../components/shared/FullPageState'
import { getActiveLocale } from '../../utils/locale'
import { useAuthStore } from '../../store/authStore'
import { getApiErrorBody, runWithRetry } from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'
import { INTEGER_UOMS } from '../../utils/uom'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ISSUANCES_PER_PAGE = 10
const EMPLOYEES_CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatQty(qty: number, uom: string): string {
  if (INTEGER_UOMS.includes(uom)) return Math.round(qty).toString()
  return qty.toFixed(2)
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString(getActiveLocale(), {
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
    return new Date(iso).toLocaleString(getActiveLocale(), {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return '—'
  }
}

function quotaStatusColor(status: QuotaRow['status']): string {
  if (status === 'OK') return 'green'
  if (status === 'WARNING') return 'yellow'
  return 'red'
}

function quotaStatusLabel(status: QuotaRow['status']): string {
  if (status === 'OK') return 'U redu'
  if (status === 'WARNING') return 'Upozorenje'
  return 'Prekoračeno'
}

function enforcementLabel(enforcement: string): string {
  if (enforcement === 'BLOCK') return 'Blokira'
  if (enforcement === 'WARN') return 'Upozorenje'
  return enforcement
}

// ---------------------------------------------------------------------------
// Sub-types
// ---------------------------------------------------------------------------

interface EditFormState {
  employee_id: string
  first_name: string
  last_name: string
  department: string
  job_title: string
  is_active: boolean
}

interface EditFormErrors {
  employee_id?: string
  first_name?: string
  last_name?: string
}

interface IssuanceFormState {
  articleQuery: string
  selectedArticle: IssuanceArticleLookupItem | null
  quantity: number | string
  batchId: number | null
  note: string
}

interface IssuanceFormErrors {
  article?: string
  quantity?: string
  batch?: string
}

type IssuanceCheckState =
  | { type: 'idle' }
  | { type: 'checking' }
  | { type: 'blocked'; message: string }
  | { type: 'warned'; message: string; checkResult: IssuanceCheckResult }
  | { type: 'creating' }

function emptyEditForm(emp: Employee): EditFormState {
  return {
    employee_id: emp.employee_id,
    first_name: emp.first_name,
    last_name: emp.last_name,
    department: emp.department ?? '',
    job_title: emp.job_title ?? '',
    is_active: emp.is_active,
  }
}

function emptyIssuanceForm(): IssuanceFormState {
  return {
    articleQuery: '',
    selectedArticle: null,
    quantity: '',
    batchId: null,
    note: '',
  }
}

// ---------------------------------------------------------------------------
// Detail field helper
// ---------------------------------------------------------------------------

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={4}>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Text fw={500}>{value}</Text>
    </Stack>
  )
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function EmployeeDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN'

  const employeeId = Number(id)

  // ── Core load state ──────────────────────────────────────────────────────
  const [employee, setEmployee] = useState<Employee | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)

  // ── Quotas ───────────────────────────────────────────────────────────────
  const [quotaYear, setQuotaYear] = useState<number | null>(null)
  const [quotas, setQuotas] = useState<QuotaRow[]>([])
  const [quotasLoading, setQuotasLoading] = useState(false)

  // ── Issuances ────────────────────────────────────────────────────────────
  const [issuances, setIssuances] = useState<IssuanceHistoryItem[]>([])
  const [issuancesTotal, setIssuancesTotal] = useState(0)
  const [issuancesPage, setIssuancesPage] = useState(1)
  const [issuancesLoading, setIssuancesLoading] = useState(false)

  // ── Edit ─────────────────────────────────────────────────────────────────
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<EditFormState>({
    employee_id: '',
    first_name: '',
    last_name: '',
    department: '',
    job_title: '',
    is_active: true,
  })
  const [editErrors, setEditErrors] = useState<EditFormErrors>({})
  const [editSaving, setEditSaving] = useState(false)

  // ── Deactivate ───────────────────────────────────────────────────────────
  const [isConfirmDeactivate, setIsConfirmDeactivate] = useState(false)
  const [deactivating, setDeactivating] = useState(false)

  // ── Issuance modal ───────────────────────────────────────────────────────
  const [issuanceOpen, setIssuanceOpen] = useState(false)
  const [issuanceForm, setIssuanceForm] = useState<IssuanceFormState>(emptyIssuanceForm())
  const [articleResults, setArticleResults] = useState<IssuanceArticleLookupItem[]>([])
  const [articleSearching, setArticleSearching] = useState(false)
  const [showArticleDropdown, setShowArticleDropdown] = useState(false)
  const [issuanceFormErrors, setIssuanceFormErrors] = useState<IssuanceFormErrors>({})
  const [issuanceCheckState, setIssuanceCheckState] = useState<IssuanceCheckState>({ type: 'idle' })

  const articleSearchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const articleBlurTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── Load functions ────────────────────────────────────────────────────────

  const loadQuotas = useCallback(async (empId: number) => {
    setQuotasLoading(true)
    try {
      const data = await runWithRetry(() => employeesApi.getQuotas(empId))
      setQuotas(data.quotas)
      setQuotaYear(data.year)
    } catch {
      // Non-fatal: show empty state
      setQuotas([])
    } finally {
      setQuotasLoading(false)
    }
  }, [])

  const loadIssuances = useCallback(async (empId: number, page: number) => {
    setIssuancesLoading(true)
    try {
      const data = await runWithRetry(() =>
        employeesApi.listIssuances(empId, page, ISSUANCES_PER_PAGE)
      )
      setIssuances(data.items)
      setIssuancesTotal(data.total)
    } catch {
      setIssuances([])
      setIssuancesTotal(0)
    } finally {
      setIssuancesLoading(false)
    }
  }, [])

  const loadAll = useCallback(async () => {
    setLoading(true)
    setLoadError(false)
    try {
      const [empData, quotaData, issuanceData] = await Promise.all([
        runWithRetry(() => employeesApi.get(employeeId)),
        runWithRetry(() => employeesApi.getQuotas(employeeId)),
        runWithRetry(() => employeesApi.listIssuances(employeeId, 1, ISSUANCES_PER_PAGE)),
      ])
      setEmployee(empData)
      setQuotas(quotaData.quotas)
      setQuotaYear(quotaData.year)
      setIssuances(issuanceData.items)
      setIssuancesTotal(issuanceData.total)
      setIssuancesPage(1)
    } catch {
      setLoadError(true)
    } finally {
      setLoading(false)
    }
  }, [employeeId])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  // ── Edit handlers ─────────────────────────────────────────────────────────

  function openEdit() {
    if (employee) {
      setEditForm(emptyEditForm(employee))
      setEditErrors({})
      setIsEditing(true)
      setIsConfirmDeactivate(false)
    }
  }

  function validateEdit(): EditFormErrors {
    const errors: EditFormErrors = {}
    if (!editForm.employee_id.trim()) errors.employee_id = 'Šifra zaposlenika je obavezna.'
    if (!editForm.first_name.trim()) errors.first_name = 'Ime je obavezno.'
    if (!editForm.last_name.trim()) errors.last_name = 'Prezime je obavezno.'
    return errors
  }

  async function handleEditSave(e: FormEvent) {
    e.preventDefault()
    const errors = validateEdit()
    if (Object.keys(errors).length > 0) {
      setEditErrors(errors)
      return
    }
    setEditSaving(true)
    try {
      const updated = await employeesApi.update(employeeId, {
        employee_id: editForm.employee_id.trim(),
        first_name: editForm.first_name.trim(),
        last_name: editForm.last_name.trim(),
        department: editForm.department.trim() || null,
        job_title: editForm.job_title.trim() || null,
        is_active: editForm.is_active,
      })
      setEmployee(updated)
      setIsEditing(false)
      showSuccessToast('Podaci zaposlenika uspješno ažurirani.')
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setEditErrors({ employee_id: 'Šifra zaposlenika već postoji.' })
      } else if (axios.isAxiosError(err) && err.response?.status === 400) {
        const body = getApiErrorBody(err)
        showErrorToast(body?.message || 'Greška pri ažuriranju.')
      } else {
        showErrorToast('Greška pri ažuriranju. Pokušajte ponovo.')
      }
    } finally {
      setEditSaving(false)
    }
  }

  // ── Deactivate handlers ───────────────────────────────────────────────────

  async function handleDeactivate() {
    setDeactivating(true)
    try {
      const updated = await employeesApi.deactivate(employeeId)
      setEmployee(updated)
      setIsConfirmDeactivate(false)
      showSuccessToast('Zaposlenik je deaktiviran.')
    } catch {
      showErrorToast('Greška pri deaktiviranju. Pokušajte ponovo.')
    } finally {
      setDeactivating(false)
    }
  }

  // ── Issuance form handlers ────────────────────────────────────────────────

  function openIssuanceModal() {
    setIssuanceForm(emptyIssuanceForm())
    setArticleResults([])
    setIssuanceFormErrors({})
    setIssuanceCheckState({ type: 'idle' })
    setIssuanceOpen(true)
  }

  function closeIssuanceModal() {
    setIssuanceOpen(false)
  }

  const handleArticleQueryChange = (value: string) => {
    setIssuanceForm((f) => ({ ...f, articleQuery: value, selectedArticle: null, batchId: null, quantity: '' }))
    setIssuanceCheckState({ type: 'idle' })
    setIssuanceFormErrors((e) => ({ ...e, article: undefined, batch: undefined }))

    if (articleSearchDebounceRef.current) clearTimeout(articleSearchDebounceRef.current)
    if (!value.trim()) {
      setArticleResults([])
      setShowArticleDropdown(false)
      return
    }
    articleSearchDebounceRef.current = setTimeout(async () => {
      setArticleSearching(true)
      try {
        const results = await employeesApi.lookupArticles(value.trim())
        setArticleResults(results)
        setShowArticleDropdown(results.length > 0)
      } catch {
        // ignore lookup errors silently
      } finally {
        setArticleSearching(false)
      }
    }, 400)
  }

  const handleArticleSelect = (article: IssuanceArticleLookupItem) => {
    setIssuanceForm((f) => ({
      ...f,
      articleQuery: `${article.article_no} — ${article.description}`,
      selectedArticle: article,
      batchId: null,
      quantity: '',
    }))
    setArticleResults([])
    setShowArticleDropdown(false)
    setIssuanceCheckState({ type: 'idle' })
    setIssuanceFormErrors({})
  }

  const handleArticleInputBlur = () => {
    articleBlurTimerRef.current = setTimeout(() => {
      setShowArticleDropdown(false)
    }, 150)
  }

  const handleArticleResultMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    if (articleBlurTimerRef.current) clearTimeout(articleBlurTimerRef.current)
  }

  function validateIssuanceForm(): IssuanceFormErrors {
    const errors: IssuanceFormErrors = {}
    const { selectedArticle, quantity, batchId } = issuanceForm
    if (!selectedArticle) {
      errors.article = 'Odaberite artikl.'
    }
    if (!quantity || Number(quantity) <= 0) {
      errors.quantity = 'Unesite valjanu količinu (> 0).'
    }
    if (selectedArticle?.has_batch) {
      if (!selectedArticle.batches || selectedArticle.batches.length === 0) {
        errors.batch = 'Nema dostupnih serija za ovaj artikl.'
      } else if (!batchId) {
        errors.batch = 'Odaberite seriju.'
      }
    }
    return errors
  }

  async function doCreateIssuance() {
    setIssuanceCheckState({ type: 'creating' })
    try {
      const result = await employeesApi.createIssuance(employeeId, {
        article_id: issuanceForm.selectedArticle!.id,
        quantity: Number(issuanceForm.quantity),
        batch_id: issuanceForm.batchId || null,
        note: issuanceForm.note.trim() || null,
      })
      if (result.warning) {
        showSuccessToast(`Artikl uspješno izdan. Upozorenje: ${result.warning.message}`)
      } else {
        showSuccessToast('Artikl uspješno izdan.')
      }
      closeIssuanceModal()
      loadQuotas(employeeId)
      loadIssuances(employeeId, 1)
      setIssuancesPage(1)
    } catch (err) {
      setIssuanceCheckState({ type: 'idle' })
      if (axios.isAxiosError(err) && err.response?.status === 400) {
        const body = getApiErrorBody(err)
        showErrorToast(body?.message || 'Greška pri izdavanju artikla.')
      } else {
        showErrorToast('Greška pri izdavanju artikla. Pokušajte ponovo.')
      }
    }
  }

  async function handleIssuanceSubmit(e: FormEvent) {
    e.preventDefault()

    // If already warned and user confirmed, proceed to create
    if (issuanceCheckState.type === 'warned') {
      await doCreateIssuance()
      return
    }

    const errors = validateIssuanceForm()
    if (Object.keys(errors).length > 0) {
      setIssuanceFormErrors(errors)
      return
    }

    // Run quota check
    setIssuanceCheckState({ type: 'checking' })
    try {
      const checkResult = await employeesApi.checkIssuance(employeeId, {
        article_id: issuanceForm.selectedArticle!.id,
        quantity: Number(issuanceForm.quantity),
        batch_id: issuanceForm.batchId || null,
      })
      if (checkResult.status === 'WARNING') {
        setIssuanceCheckState({ type: 'warned', message: checkResult.message, checkResult })
      } else {
        // OK or NO_QUOTA — proceed immediately
        await doCreateIssuance()
      }
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 400) {
        const body = err.response.data as { error?: string; message?: string; details?: { check?: IssuanceCheckResult } }
        const msg = body.details?.check?.message || body.message || 'Kvota prekoračena.'
        setIssuanceCheckState({ type: 'blocked', message: msg })
      } else {
        setIssuanceCheckState({ type: 'idle' })
        showErrorToast('Greška pri provjeri kvote. Pokušajte ponovo.')
      }
    }
  }

  const issuanceSubmitBusy =
    issuanceCheckState.type === 'checking' || issuanceCheckState.type === 'creating'

  const issuanceBlocked = issuanceCheckState.type === 'blocked'

  // ── Issuance page change ──────────────────────────────────────────────────

  const handleIssuancesPageChange = (newPage: number) => {
    setIssuancesPage(newPage)
    loadIssuances(employeeId, newPage)
  }

  // ── Batch select data ─────────────────────────────────────────────────────

  const batchSelectData =
    issuanceForm.selectedArticle?.has_batch && issuanceForm.selectedArticle.batches
      ? issuanceForm.selectedArticle.batches.map((b) => ({
          value: String(b.id),
          label: `${b.batch_code} (ist. ${b.expiry_date}, dos. ${formatQty(b.available, issuanceForm.selectedArticle!.base_uom)} ${issuanceForm.selectedArticle!.base_uom})`,
        }))
      : []

  // ── Full-page states ──────────────────────────────────────────────────────

  if (loading) {
    return <FullPageState title="Učitavanje..." loading />
  }

  if (loadError || !employee) {
    return (
      <FullPageState
        title="Greška pri učitavanju"
        message={EMPLOYEES_CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovo"
        onAction={() => loadAll()}
      />
    )
  }

  const issuancesTotalPages = Math.ceil(issuancesTotal / ISSUANCES_PER_PAGE)

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Stack gap="lg" p="md">
      {/* Header */}
      <Group align="center" gap="sm">
        <ActionIcon
          variant="subtle"
          onClick={() => navigate('/employees')}
          aria-label="Natrag na listu"
        >
          <IconArrowLeft size={20} />
        </ActionIcon>
        <Title order={2} style={{ flex: 1 }}>
          {employee.first_name} {employee.last_name}
        </Title>
        <Badge color={employee.is_active ? 'green' : 'gray'} size="lg">
          {employee.is_active ? 'Aktivan' : 'Neaktivan'}
        </Badge>
        {isAdmin && !isEditing && (
          <Group gap="xs">
            <Button variant="outline" size="sm" onClick={openEdit}>
              Uredi
            </Button>
            {employee.is_active && (
              <Button
                variant="outline"
                color="red"
                size="sm"
                onClick={() => {
                  setIsConfirmDeactivate(true)
                  setIsEditing(false)
                }}
              >
                Deaktiviraj
              </Button>
            )}
          </Group>
        )}
      </Group>

      {/* Deactivate confirmation */}
      {isAdmin && isConfirmDeactivate && (
        <Alert color="red" title="Potvrda deaktivacije">
          <Stack gap="sm">
            <Text size="sm">
              Jeste li sigurni da želite deaktivirati zaposlenika{' '}
              <strong>
                {employee.first_name} {employee.last_name}
              </strong>
              ?
            </Text>
            <Group gap="xs">
              <Button color="red" size="xs" loading={deactivating} onClick={handleDeactivate}>
                Deaktiviraj
              </Button>
              <Button
                variant="subtle"
                size="xs"
                disabled={deactivating}
                onClick={() => setIsConfirmDeactivate(false)}
              >
                Odustani
              </Button>
            </Group>
          </Stack>
        </Alert>
      )}

      {/* Edit form */}
      {isAdmin && isEditing && (
        <Paper withBorder p="md">
          <form onSubmit={handleEditSave}>
            <Stack gap="sm">
              <Title order={4}>Uredi zaposlenika</Title>
              <SimpleGrid cols={2} spacing="sm">
                <TextInput
                  label="Šifra zaposlenika"
                  required
                  value={editForm.employee_id}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, employee_id: e.currentTarget.value }))
                  }
                  error={editErrors.employee_id}
                  disabled={editSaving}
                />
                <TextInput
                  label="Ime"
                  required
                  value={editForm.first_name}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, first_name: e.currentTarget.value }))
                  }
                  error={editErrors.first_name}
                  disabled={editSaving}
                />
                <TextInput
                  label="Prezime"
                  required
                  value={editForm.last_name}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, last_name: e.currentTarget.value }))
                  }
                  error={editErrors.last_name}
                  disabled={editSaving}
                />
                <TextInput
                  label="Odjel"
                  value={editForm.department}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, department: e.currentTarget.value }))
                  }
                  disabled={editSaving}
                />
                <TextInput
                  label="Radno mjesto"
                  value={editForm.job_title}
                  onChange={(e) =>
                    setEditForm((f) => ({ ...f, job_title: e.currentTarget.value }))
                  }
                  disabled={editSaving}
                />
                <Box pt="xl">
                  <Checkbox
                    label="Aktivan"
                    checked={editForm.is_active}
                    onChange={(e) =>
                      setEditForm((f) => ({ ...f, is_active: e.currentTarget.checked }))
                    }
                    disabled={editSaving}
                  />
                </Box>
              </SimpleGrid>
              <Group justify="flex-end" mt="sm">
                <Button
                  variant="subtle"
                  disabled={editSaving}
                  onClick={() => {
                    setIsEditing(false)
                    setEditErrors({})
                  }}
                >
                  Odustani
                </Button>
                <Button type="submit" loading={editSaving}>
                  Spremi
                </Button>
              </Group>
            </Stack>
          </form>
        </Paper>
      )}

      {/* Employee info */}
      {!isEditing && (
        <Paper withBorder p="md">
          <SimpleGrid cols={4} spacing="md">
            <DetailField label="Šifra zaposlenika" value={employee.employee_id} />
            <DetailField label="Odjel" value={employee.department || '—'} />
            <DetailField label="Radno mjesto" value={employee.job_title || '—'} />
            <DetailField label="Dodano" value={formatDate(employee.created_at)} />
          </SimpleGrid>
        </Paper>
      )}

      {/* Quota overview */}
      <Paper withBorder p="md">
        <Stack gap="sm">
          <Title order={3}>
            Kvote {quotaYear ? `(${quotaYear})` : ''}
          </Title>
          {quotasLoading ? (
            <Group justify="center" py="md">
              <Loader size="sm" />
            </Group>
          ) : quotas.length === 0 ? (
            <Stack gap="xs">
              <Text c="dimmed">Nema konfiguriranih kvota za ovog zaposlenika.</Text>
              {isAdmin && (
                <Button
                  variant="subtle"
                  size="xs"
                  onClick={() => navigate('/settings')}
                >
                  Upravljanje kvotama u Postavkama
                </Button>
              )}
            </Stack>
          ) : (
            <ScrollArea>
              <Table striped>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Artikl / Kategorija</Table.Th>
                    <Table.Th>Kvota</Table.Th>
                    <Table.Th>Primljeno</Table.Th>
                    <Table.Th>Preostalo</Table.Th>
                    <Table.Th>Pravilo</Table.Th>
                    <Table.Th>Status</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {quotas.map((row, idx) => (
                    <Table.Tr key={idx}>
                      <Table.Td>
                        {row.article_id != null ? (
                          <Stack gap={2}>
                            <Text size="sm" fw={500}>
                              {row.article_no}
                            </Text>
                            <Text size="xs" c="dimmed">
                              {row.description}
                            </Text>
                          </Stack>
                        ) : (
                          <Stack gap={2}>
                            <Text size="sm" fw={500}>
                              {row.category_label_hr ?? '—'}
                            </Text>
                            <Text size="xs" c="dimmed">
                              (kategorija)
                            </Text>
                          </Stack>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {formatQty(row.quota, row.uom)} {row.uom}
                      </Table.Td>
                      <Table.Td>
                        {formatQty(row.received, row.uom)} {row.uom}
                      </Table.Td>
                      <Table.Td>
                        {formatQty(row.remaining, row.uom)} {row.uom}
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          color={row.enforcement === 'BLOCK' ? 'red' : 'yellow'}
                          variant="light"
                          size="sm"
                        >
                          {enforcementLabel(row.enforcement)}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          color={quotaStatusColor(row.status)}
                          variant="filled"
                          size="sm"
                        >
                          {quotaStatusLabel(row.status)}
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea>
          )}
        </Stack>
      </Paper>

      {/* Issuance history */}
      <Paper withBorder p="md">
        <Stack gap="sm">
          <Group justify="space-between" align="center">
            <Title order={3}>Povijest izdavanja</Title>
            {isAdmin && (
              <Button size="sm" onClick={openIssuanceModal}>
                Izdaj artikl
              </Button>
            )}
          </Group>

          {issuancesLoading ? (
            <Group justify="center" py="md">
              <Loader size="sm" />
            </Group>
          ) : issuances.length === 0 ? (
            <Text c="dimmed">Nema evidencija izdavanja.</Text>
          ) : (
            <>
              <ScrollArea>
                <Table striped>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Datum</Table.Th>
                      <Table.Th>Artikl br.</Table.Th>
                      <Table.Th>Opis</Table.Th>
                      <Table.Th>Količina</Table.Th>
                      <Table.Th>Serija</Table.Th>
                      <Table.Th>Izdao/la</Table.Th>
                      <Table.Th>Napomena</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {issuances.map((iso) => (
                      <Table.Tr key={iso.id}>
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>
                          {formatDateTime(iso.issued_at)}
                        </Table.Td>
                        <Table.Td>{iso.article_no ?? '—'}</Table.Td>
                        <Table.Td>{iso.description ?? '—'}</Table.Td>
                        <Table.Td style={{ whiteSpace: 'nowrap' }}>
                          {formatQty(iso.quantity, iso.uom)} {iso.uom}
                        </Table.Td>
                        <Table.Td>{iso.batch_code ?? '—'}</Table.Td>
                        <Table.Td>{iso.issued_by ?? '—'}</Table.Td>
                        <Table.Td>
                          <Text size="sm" style={{ maxWidth: 200 }} lineClamp={2}>
                            {iso.note ?? '—'}
                          </Text>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </ScrollArea>

              {issuancesTotalPages > 1 && (
                <Group justify="center">
                  <Pagination
                    total={issuancesTotalPages}
                    value={issuancesPage}
                    onChange={handleIssuancesPageChange}
                    size="sm"
                  />
                </Group>
              )}
            </>
          )}
        </Stack>
      </Paper>

      {/* Issuance form modal (ADMIN only) */}
      {isAdmin && (
        <Modal
          opened={issuanceOpen}
          onClose={() => {
            if (!issuanceSubmitBusy) closeIssuanceModal()
          }}
          title="Izdaj artikl"
          size="md"
        >
          <form onSubmit={handleIssuanceSubmit}>
            <Stack gap="sm">
              {/* Article search */}
              <Box style={{ position: 'relative' }}>
                <TextInput
                  label="Artikl"
                  placeholder="Unesite broj artikla ili opis..."
                  value={issuanceForm.articleQuery}
                  onChange={(e) => handleArticleQueryChange(e.currentTarget.value)}
                  onBlur={handleArticleInputBlur}
                  onFocus={() => {
                    if (articleResults.length > 0) setShowArticleDropdown(true)
                  }}
                  error={issuanceFormErrors.article}
                  disabled={issuanceSubmitBusy}
                  rightSection={articleSearching ? <Loader size="xs" /> : null}
                />
                {showArticleDropdown && articleResults.length > 0 && (
                  <Paper
                    withBorder
                    shadow="sm"
                    style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      zIndex: 200,
                      maxHeight: 240,
                      overflowY: 'auto',
                    }}
                  >
                    {articleResults.map((a) => (
                      <Box
                        key={a.id}
                        px="sm"
                        py="xs"
                        style={{ cursor: 'pointer' }}
                        onMouseDown={handleArticleResultMouseDown}
                        onClick={() => handleArticleSelect(a)}
                        onMouseEnter={(e) => {
                          ;(e.currentTarget as HTMLDivElement).style.background = 'var(--mantine-color-gray-1)'
                        }}
                        onMouseLeave={(e) => {
                          ;(e.currentTarget as HTMLDivElement).style.background = ''
                        }}
                      >
                        <Text size="sm" fw={500}>
                          {a.article_no}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {a.description} · {a.base_uom}
                        </Text>
                      </Box>
                    ))}
                  </Paper>
                )}
              </Box>

              {/* Quantity */}
              <NumberInput
                label="Količina"
                placeholder="0"
                value={issuanceForm.quantity}
                onChange={(val) => {
                  setIssuanceForm((f) => ({ ...f, quantity: val }))
                  setIssuanceCheckState({ type: 'idle' })
                  setIssuanceFormErrors((e) => ({ ...e, quantity: undefined }))
                }}
                min={0}
                step={issuanceForm.selectedArticle?.decimal_display ? 0.01 : 1}
                decimalScale={issuanceForm.selectedArticle?.decimal_display ? 3 : 0}
                rightSection={
                  issuanceForm.selectedArticle ? (
                    <Text size="xs" c="dimmed" pr="xs">
                      {issuanceForm.selectedArticle.base_uom}
                    </Text>
                  ) : null
                }
                error={issuanceFormErrors.quantity}
                disabled={!issuanceForm.selectedArticle || issuanceSubmitBusy}
              />

              {/* Batch select (conditional) */}
              {issuanceForm.selectedArticle?.has_batch && (
                <Select
                  label="Serija"
                  placeholder="Odaberite seriju..."
                  data={batchSelectData}
                  value={issuanceForm.batchId !== null ? String(issuanceForm.batchId) : null}
                  onChange={(val) => {
                    setIssuanceForm((f) => ({ ...f, batchId: val ? Number(val) : null }))
                    setIssuanceCheckState({ type: 'idle' })
                    setIssuanceFormErrors((e) => ({ ...e, batch: undefined }))
                  }}
                  error={issuanceFormErrors.batch}
                  disabled={batchSelectData.length === 0 || issuanceSubmitBusy}
                />
              )}

              {/* No batches inline error */}
              {issuanceForm.selectedArticle?.has_batch &&
                (!issuanceForm.selectedArticle.batches ||
                  issuanceForm.selectedArticle.batches.length === 0) && (
                  <Text size="sm" c="red">
                    Nema dostupnih serija za ovaj artikl.
                  </Text>
                )}

              {/* Note */}
              <Textarea
                label="Napomena"
                placeholder="Opcionalna napomena (maks. 1000 znakova)"
                value={issuanceForm.note}
                onChange={(e) =>
                  setIssuanceForm((f) => ({ ...f, note: e.currentTarget.value }))
                }
                maxLength={1000}
                minRows={2}
                disabled={issuanceSubmitBusy}
              />

              {/* Check result messages */}
              {issuanceCheckState.type === 'blocked' && (
                <Alert color="red" title="Kvota prekoračena">
                  {issuanceCheckState.message}
                </Alert>
              )}
              {issuanceCheckState.type === 'warned' && (
                <Alert color="yellow" title="Upozorenje o kvoti">
                  {issuanceCheckState.message}
                </Alert>
              )}

              <Divider />

              <Group justify="flex-end">
                <Button
                  variant="subtle"
                  onClick={closeIssuanceModal}
                  disabled={issuanceSubmitBusy}
                >
                  Odustani
                </Button>
                <Button
                  type="submit"
                  loading={issuanceSubmitBusy}
                  disabled={issuanceBlocked}
                  color={issuanceCheckState.type === 'warned' ? 'orange' : undefined}
                >
                  {issuanceCheckState.type === 'warned' ? 'Potvrdi i izdaj' : 'Izdaj'}
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>
      )}
    </Stack>
  )
}
