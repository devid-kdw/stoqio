import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Badge,
  Button,
  Checkbox,
  Group,
  Loader,
  Modal,
  Pagination,
  Paper,
  ScrollArea,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import axios from 'axios'

import {
  employeesApi,
  type Employee,
  type EmployeeMutationPayload,
} from '../../api/employees'
import FullPageState from '../../components/shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import { getApiErrorBody, runWithRetry } from '../../utils/http'
import { showErrorToast, showSuccessToast } from '../../utils/toasts'

const PAGE_SIZE = 50
const EMPLOYEES_CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'

interface CreateFormState {
  employee_id: string
  first_name: string
  last_name: string
  department: string
  job_title: string
  is_active: boolean
}

interface CreateFormErrors {
  employee_id?: string
  first_name?: string
  last_name?: string
}

function createEmptyForm(): CreateFormState {
  return {
    employee_id: '',
    first_name: '',
    last_name: '',
    department: '',
    job_title: '',
    is_active: true,
  }
}

export default function EmployeesPage() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN'

  const [employees, setEmployees] = useState<Employee[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)

  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<CreateFormState>(createEmptyForm())
  const [createErrors, setCreateErrors] = useState<CreateFormErrors>({})
  const [createSaving, setCreateSaving] = useState(false)

  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadEmployees = useCallback(
    async (p: number, q: string, inactive: boolean) => {
      setLoading(true)
      setLoadError(false)
      try {
        const data = await runWithRetry(() =>
          employeesApi.list({ page: p, perPage: PAGE_SIZE, q: q || undefined, includeInactive: inactive })
        )
        setEmployees(data.items)
        setTotal(data.total)
      } catch {
        setLoadError(true)
      } finally {
        setLoading(false)
      }
    },
    []
  )

  useEffect(() => {
    loadEmployees(1, '', false)
  }, [loadEmployees])

  const handleSearchChange = (value: string) => {
    setSearch(value)
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current)
    searchDebounceRef.current = setTimeout(() => {
      setPage(1)
      loadEmployees(1, value, includeInactive)
    }, 400)
  }

  const handleToggleInactive = (checked: boolean) => {
    setIncludeInactive(checked)
    setPage(1)
    loadEmployees(1, search, checked)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    loadEmployees(newPage, search, includeInactive)
  }

  function validateCreate(): CreateFormErrors {
    const errors: CreateFormErrors = {}
    if (!createForm.employee_id.trim()) errors.employee_id = 'Šifra zaposlenika je obavezna.'
    if (!createForm.first_name.trim()) errors.first_name = 'Ime je obavezno.'
    if (!createForm.last_name.trim()) errors.last_name = 'Prezime je obavezno.'
    return errors
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    const errors = validateCreate()
    if (Object.keys(errors).length > 0) {
      setCreateErrors(errors)
      return
    }
    setCreateSaving(true)
    try {
      const payload: EmployeeMutationPayload = {
        employee_id: createForm.employee_id.trim(),
        first_name: createForm.first_name.trim(),
        last_name: createForm.last_name.trim(),
        department: createForm.department.trim() || null,
        job_title: createForm.job_title.trim() || null,
        is_active: createForm.is_active,
      }
      const created = await employeesApi.create(payload)
      showSuccessToast('Zaposlenik uspješno dodan.')
      setCreateOpen(false)
      setCreateForm(createEmptyForm())
      setCreateErrors({})
      navigate(`/employees/${created.id}`)
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setCreateErrors({ employee_id: 'Šifra zaposlenika već postoji.' })
      } else if (axios.isAxiosError(err) && err.response?.status === 400) {
        const body = getApiErrorBody(err)
        showErrorToast(body?.message || 'Greška pri dodavanju zaposlenika.')
      } else {
        showErrorToast('Greška pri dodavanju zaposlenika. Pokušajte ponovo.')
      }
    } finally {
      setCreateSaving(false)
    }
  }

  if (loadError) {
    return (
      <FullPageState
        title="Greška pri učitavanju"
        message={EMPLOYEES_CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovo"
        onAction={() => loadEmployees(page, search, includeInactive)}
      />
    )
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between" align="center">
        <Title order={2}>Zaposlenici</Title>
        {isAdmin && (
          <Button
            onClick={() => {
              setCreateForm(createEmptyForm())
              setCreateErrors({})
              setCreateOpen(true)
            }}
          >
            Novi zaposlenik
          </Button>
        )}
      </Group>

      <Group gap="md" align="flex-end">
        <TextInput
          placeholder="Pretraži zaposlenike..."
          value={search}
          onChange={(e) => handleSearchChange(e.currentTarget.value)}
          style={{ flex: 1 }}
        />
        <Checkbox
          label="Prikaži neaktivne"
          checked={includeInactive}
          onChange={(e) => handleToggleInactive(e.currentTarget.checked)}
        />
      </Group>

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
                  <Table.Th>Šifra</Table.Th>
                  <Table.Th>Ime i prezime</Table.Th>
                  <Table.Th>Radno mjesto</Table.Th>
                  <Table.Th>Odjel</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {employees.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={5}>
                      <Text c="dimmed" ta="center" py="md">
                        Nema zaposlenika.
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  employees.map((emp) => (
                    <Table.Tr
                      key={emp.id}
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/employees/${emp.id}`)}
                    >
                      <Table.Td>{emp.employee_id}</Table.Td>
                      <Table.Td>
                        {emp.first_name} {emp.last_name}
                      </Table.Td>
                      <Table.Td>{emp.job_title || '—'}</Table.Td>
                      <Table.Td>{emp.department || '—'}</Table.Td>
                      <Table.Td>
                        <Badge color={emp.is_active ? 'green' : 'gray'}>
                          {emp.is_active ? 'Aktivan' : 'Neaktivan'}
                        </Badge>
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
          <Pagination total={totalPages} value={page} onChange={handlePageChange} />
        </Group>
      )}

      {isAdmin && (
        <Modal
          opened={createOpen}
          onClose={() => {
            if (!createSaving) {
              setCreateOpen(false)
              setCreateErrors({})
            }
          }}
          title="Novi zaposlenik"
        >
          <form onSubmit={handleCreate}>
            <Stack gap="sm">
              <TextInput
                label="Šifra zaposlenika"
                required
                value={createForm.employee_id}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, employee_id: e.currentTarget.value }))
                }
                error={createErrors.employee_id}
                disabled={createSaving}
              />
              <TextInput
                label="Ime"
                required
                value={createForm.first_name}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, first_name: e.currentTarget.value }))
                }
                error={createErrors.first_name}
                disabled={createSaving}
              />
              <TextInput
                label="Prezime"
                required
                value={createForm.last_name}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, last_name: e.currentTarget.value }))
                }
                error={createErrors.last_name}
                disabled={createSaving}
              />
              <TextInput
                label="Odjel"
                value={createForm.department}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, department: e.currentTarget.value }))
                }
                disabled={createSaving}
              />
              <TextInput
                label="Radno mjesto"
                value={createForm.job_title}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, job_title: e.currentTarget.value }))
                }
                disabled={createSaving}
              />
              <Checkbox
                label="Aktivan"
                checked={createForm.is_active}
                onChange={(e) =>
                  setCreateForm((f) => ({ ...f, is_active: e.currentTarget.checked }))
                }
                disabled={createSaving}
              />
              <Group justify="flex-end" mt="md">
                <Button
                  variant="subtle"
                  onClick={() => {
                    setCreateOpen(false)
                    setCreateErrors({})
                  }}
                  disabled={createSaving}
                >
                  Odustani
                </Button>
                <Button type="submit" loading={createSaving}>
                  Spremi
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>
      )}
    </Stack>
  )
}
