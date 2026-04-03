import { useCallback, useEffect, useState } from 'react'

import {
  inventoryApi,
  type ActiveCount,
  type CountDetail,
  type HistoryItem,
} from '../../api/inventory'
import FullPageState from '../../components/shared/FullPageState'
import { isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast } from '../../utils/toasts'
import { HISTORY_PAGE_SIZE } from './inventoryFormatters'
import { HistoryView } from './HistoryView'
import { ActiveCountView } from './ActiveCountView'
import { CompletedDetailView } from './CompletedDetailView'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CONNECTION_ERROR =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovo.'

// ---------------------------------------------------------------------------
// InventoryCountPage — route entry point
// ---------------------------------------------------------------------------

type ViewKind = 'loading' | 'load-error' | 'history' | 'active' | 'detail'

export default function InventoryCountPage() {
  const [view, setView] = useState<ViewKind>('loading')
  const [activeCount, setActiveCount] = useState<ActiveCount | null>(null)
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [openingCountExists, setOpeningCountExists] = useState(true)
  const [detailCount, setDetailCount] = useState<CountDetail | null>(null)

  const loadHistory = useCallback(async (page: number) => {
    setHistoryLoading(true)
    try {
      const data = await runWithRetry(() => inventoryApi.history(page, HISTORY_PAGE_SIZE))
      setHistoryItems(data.items)
      setHistoryTotal(data.total)
      setHistoryPage(page)
      setOpeningCountExists(data.opening_count_exists)
      setView('history')
    } catch {
      setView('load-error')
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  const initPage = useCallback(async () => {
    setView('loading')
    try {
      const active = await runWithRetry(() => inventoryApi.getActive())
      if (active) {
        setActiveCount(active)
        setView('active')
      } else {
        await loadHistory(1)
      }
    } catch {
      setView('load-error')
    }
  }, [loadHistory])

  useEffect(() => {
    initPage()
  }, [initPage])

  async function handleHistoryRowClick(id: number) {
    try {
      const detail = await runWithRetry(() => inventoryApi.detail(id))
      setDetailCount(detail)
      setView('detail')
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setView('load-error')
        return
      }
      showErrorToast('Greška pri učitavanju inventure.')
    }
  }

  async function handleCountCompleted(countId: number) {
    try {
      const detail = await runWithRetry(() => inventoryApi.detail(countId))
      setDetailCount(detail)
      setView('detail')
    } catch (err) {
      if (isNetworkOrServerError(err)) {
        setView('load-error')
        return
      }
      showErrorToast('Greška pri učitavanju završene inventure.')
      initPage()
    }
  }

  if (view === 'loading') {
    return <FullPageState title="Učitavanje…" loading />
  }

  if (view === 'load-error') {
    return (
      <FullPageState
        title="Greška pri učitavanju"
        message={CONNECTION_ERROR}
        actionLabel="Pokušaj ponovo"
        onAction={initPage}
      />
    )
  }

  if (view === 'active' && activeCount) {
    return (
      <ActiveCountView
        count={activeCount}
        onCompleted={handleCountCompleted}
        onFatalError={() => setView('load-error')}
      />
    )
  }

  if (view === 'detail' && detailCount) {
    return <CompletedDetailView count={detailCount} onBack={initPage} />
  }

  // Default: history view
  return (
    <HistoryView
      items={historyItems}
      total={historyTotal}
      page={historyPage}
      loading={historyLoading}
      openingCountExists={openingCountExists}
      onPageChange={loadHistory}
      onRowClick={handleHistoryRowClick}
      onFatalError={() => setView('load-error')}
      onCountStarted={(active) => {
        setActiveCount(active)
        setView('active')
      }}
    />
  )
}
