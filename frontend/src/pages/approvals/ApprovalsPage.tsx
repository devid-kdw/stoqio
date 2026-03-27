import { useCallback, useEffect, useState } from 'react'
import {
  Container,
  Group,
  Loader,
  Stack,
  Tabs,
  Text,
  Title,
} from '@mantine/core'
import { approvalsApi } from '../../api/approvals'
import type { ApprovalsDraftGroup } from '../../api/approvals'
import FullPageState from '../../components/shared/FullPageState'
import DraftGroupCard from './components/DraftGroupCard'
import { CONNECTION_ERROR_MESSAGE, isNetworkOrServerError } from '../../utils/http'

export default function ApprovalsPage() {
  const [activeTab, setActiveTab] = useState<string | null>('pending')

  const [pendingGroups, setPendingGroups] = useState<ApprovalsDraftGroup[]>([])
  const [historyGroups, setHistoryGroups] = useState<ApprovalsDraftGroup[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const handleFatalError = useCallback(() => {
    setError(true)
  }, [])

  const loadData = useCallback(async (tab: string, isRetry = false) => {
    setLoading(true)
    setError(false)

    try {
      if (tab === 'pending') {
        const data = await approvalsApi.getPending()
        setPendingGroups(data.items)
      } else {
        const data = await approvalsApi.getHistory()
        setHistoryGroups(data.items)
      }
    } catch (err) {
      if (!isRetry && isNetworkOrServerError(err)) {
        await loadData(tab, true)
        return
      }
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab) {
      void loadData(activeTab)
    }
  }, [activeTab, loadData])

  if (error) {
    return (
      <FullPageState
        title="Greška povezivanja"
        message={CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => window.location.reload()}
      />
    )
  }

  return (
    <Container fluid px="xl" py="lg">
      <Group justify="space-between" mb="xl">
        <Stack gap={4}>
          <Title order={2}>Odobravanja</Title>
          <Text c="dimmed" size="sm">
            Pregled i odobravanje unosa izlaznog materijala
          </Text>
        </Stack>
      </Group>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="pending">Za odobrenje</Tabs.Tab>
          <Tabs.Tab value="history">Povijest</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="pending">
          {loading ? (
            <Group justify="center" py="xl"><Loader /></Group>
          ) : pendingGroups.length === 0 ? (
            <Text c="dimmed" ta="center" py="xl">Nema draftova na čekanju.</Text>
          ) : (
            <Stack gap="xs">
              {pendingGroups.map(group => (
                <DraftGroupCard 
                  key={`pending-${group.draft_group_id}`} 
                  summary={group} 
                  isHistory={false} 
                  onGroupResolved={() => loadData('pending')}
                  onFatalError={handleFatalError}
                />
              ))}
            </Stack>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="history">
          {loading ? (
            <Group justify="center" py="xl"><Loader /></Group>
          ) : historyGroups.length === 0 ? (
            <Text c="dimmed" ta="center" py="xl">Nema povijesti odobrenja.</Text>
          ) : (
            <Stack gap="xs">
              {historyGroups.map(group => (
                <DraftGroupCard 
                  key={`history-${group.draft_group_id}`} 
                  summary={group} 
                  isHistory={true}
                  onFatalError={handleFatalError}
                />
              ))}
            </Stack>
          )}
        </Tabs.Panel>
      </Tabs>
    </Container>
  )
}
