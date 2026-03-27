import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Loader,
  MultiSelect,
  Pagination,
  Paper,
  ScrollArea,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
  useMantineColorScheme,
  useMantineTheme,
} from '@mantine/core'
import {
  IconChartBar,
  IconChartLine,
  IconFileSpreadsheet,
  IconFileTypePdf,
  IconListDetails,
  IconPackage,
} from '@tabler/icons-react'

import {
  articlesApi,
  type ArticleCategoryLookupItem,
  type ArticleUomLookupItem,
  type WarehouseArticleListItem,
} from '../../api/articles'
import {
  reportsApi,
  type MovementRange,
  type MovementStatisticsItem,
  type MovementStatisticsResponse,
  type PersonalIssuanceStatisticsItem,
  type ReportExportFormat,
  type ReportReorderStatus,
  type ReportTransactionType,
  type ReorderSummaryItem,
  type StockOverviewItem,
  type StockOverviewQuery,
  type StockOverviewResponse,
  type SurplusReportItem,
  type TopConsumptionItem,
  type TopConsumptionPeriod,
  type TopConsumptionResponse,
  type TransactionLogItem,
  type TransactionLogQuery,
} from '../../api/reports'
import FullPageState from '../../components/shared/FullPageState'
import { useAuthStore } from '../../store/authStore'
import { getApiErrorBody, getApiErrorBodyAsync, isNetworkOrServerError, runWithRetry } from '../../utils/http'
import { showErrorToast } from '../../utils/toasts'
import {
  buildUomMap,
  formatCoverageMonths,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatDecimal,
  formatOptionalQuantity,
  formatQuantity,
  formatSignedQuantity,
  getMonthStartIsoDate,
  getReorderStatusBadgeColor,
  getReorderStatusColor,
  getReorderStatusLabel,
  getTodayIsoDate,
  getTransactionTypeLabel,
} from './reportsUtils'

const REPORTS_CONNECTION_ERROR_MESSAGE =
  'Greška pri povezivanju. Provjerite radi li server i pokušajte ponovno.'
const TRANSACTIONS_PER_PAGE = 50

type ReportsTab = 'stock' | 'surplus' | 'transactions' | 'statistics'
type ZoneFilter = 'RED' | 'YELLOW' | 'NORMAL' | null
type AppliedStockFilters = Pick<StockOverviewQuery, 'dateFrom' | 'dateTo' | 'category'>
type AppliedTransactionFilters = Pick<
  TransactionLogQuery,
  'articleId' | 'dateFrom' | 'dateTo' | 'txTypes'
>

interface TransactionArticleOption {
  id: number
  articleNo: string
  description: string
  label: string
}

const TRANSACTION_TYPE_OPTIONS: Array<{ value: ReportTransactionType; label: string }> = [
  { value: 'STOCK_RECEIPT', label: getTransactionTypeLabel('STOCK_RECEIPT') },
  { value: 'OUTBOUND', label: getTransactionTypeLabel('OUTBOUND') },
  { value: 'SURPLUS_CONSUMED', label: getTransactionTypeLabel('SURPLUS_CONSUMED') },
  { value: 'STOCK_CONSUMED', label: getTransactionTypeLabel('STOCK_CONSUMED') },
  { value: 'INVENTORY_ADJUSTMENT', label: getTransactionTypeLabel('INVENTORY_ADJUSTMENT') },
  { value: 'PERSONAL_ISSUE', label: getTransactionTypeLabel('PERSONAL_ISSUE') },
]

function isReorderZone(status: ReportReorderStatus): boolean {
  return status === 'RED' || status === 'YELLOW'
}

function buildTransactionArticleLabel(
  articleNo: string,
  description: string,
  isActive = true
): string {
  const baseLabel = `${articleNo} — ${description}`
  return isActive ? baseLabel : `${baseLabel} (neaktivan)`
}

function mapArticleOption(item: WarehouseArticleListItem): TransactionArticleOption {
  return {
    id: item.id,
    articleNo: item.article_no,
    description: item.description,
    label: buildTransactionArticleLabel(item.article_no, item.description, item.is_active),
  }
}

function validateStockDateRange(dateFrom: string, dateTo: string): {
  dateFrom?: string
  dateTo?: string
} {
  const errors: { dateFrom?: string; dateTo?: string } = {}

  if (!dateFrom) {
    errors.dateFrom = 'Odaberite početni datum.'
  }

  if (!dateTo) {
    errors.dateTo = 'Odaberite završni datum.'
  }

  if (dateFrom && dateTo && dateFrom > dateTo) {
    errors.dateFrom = 'Početni datum mora biti prije završnog datuma.'
    errors.dateTo = 'Završni datum mora biti nakon početnog datuma.'
  }

  return errors
}

function validateOptionalDateRange(dateFrom: string, dateTo: string): {
  dateFrom?: string
  dateTo?: string
} {
  if (dateFrom && dateTo && dateFrom > dateTo) {
    return {
      dateFrom: 'Početni datum mora biti prije završnog datuma.',
      dateTo: 'Završni datum mora biti nakon početnog datuma.',
    }
  }

  return {}
}

function ReorderStatusBadge({ status }: { status: ReportReorderStatus }) {
  return (
    <Group gap={8} wrap="nowrap">
      <span
        aria-hidden="true"
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: getReorderStatusColor(status),
          display: 'inline-block',
          flexShrink: 0,
        }}
      />
      <Badge color={getReorderStatusBadgeColor(status)} variant="light">
        {getReorderStatusLabel(status)}
      </Badge>
    </Group>
  )
}

function ConsumptionBarChart({
  items,
  onSelect,
  uomMap,
}: {
  items: TopConsumptionItem[]
  onSelect: (item: TopConsumptionItem) => void
  uomMap: Record<string, ArticleUomLookupItem>
}) {
  const theme = useMantineTheme()
  const { colorScheme } = useMantineColorScheme()
  const isDark = colorScheme === 'dark'
  const maxValue = Math.max(...items.map((item) => item.outbound), 1)

  return (
    <Stack gap="sm">
      {items.map((item) => (
        <button
          key={item.article_id}
          type="button"
          onClick={() => onSelect(item)}
          style={{
            border: `1px solid ${isDark ? theme.colors.dark[4] : '#e9ecef'}`,
            borderRadius: 14,
            background: isDark ? theme.colors.dark[6] : '#fff',
            padding: '0.9rem 1rem',
            textAlign: 'left',
            cursor: 'pointer',
          }}
        >
          <Stack gap={8}>
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <div style={{ minWidth: 0 }}>
                <Text fw={600} size="sm" lineClamp={1}>
                  {item.description}
                </Text>
                <Text size="xs" c="dimmed">
                  {item.article_no}
                </Text>
              </div>

              <Text size="sm" fw={600}>
                {formatQuantity(item.outbound, item.uom, uomMap)}
              </Text>
            </Group>

            <div
              aria-hidden="true"
              style={{
                height: 12,
                borderRadius: 999,
                background: isDark ? theme.colors.dark[4] : '#edf2f7',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${(item.outbound / maxValue) * 100}%`,
                  minWidth: item.outbound > 0 ? 8 : 0,
                  height: '100%',
                  borderRadius: 999,
                  background: 'linear-gradient(90deg, #0b7285 0%, #15aabf 100%)',
                }}
              />
            </div>

            <Text size="xs" c="dimmed">
              Kliknite za otvaranje transakcijskog dnevnika artikla.
            </Text>
          </Stack>
        </button>
      ))}
    </Stack>
  )
}

function MovementLineChart({ items }: { items: MovementStatisticsItem[] }) {
  const width = 720
  const height = 280
  const padding = { top: 24, right: 24, bottom: 46, left: 30 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const maxValue = Math.max(
    1,
    ...items.flatMap((item) => [item.inbound, item.outbound])
  )
  const step = items.length > 1 ? plotWidth / (items.length - 1) : 0
  const labelStep = items.length > 8 ? 2 : 1

  const coordinates = items.map((item, index) => ({
    x: items.length === 1 ? padding.left + plotWidth / 2 : padding.left + index * step,
    inboundY: padding.top + plotHeight - (item.inbound / maxValue) * plotHeight,
    outboundY: padding.top + plotHeight - (item.outbound / maxValue) * plotHeight,
    label: item.label,
  }))

  const inboundPolyline = coordinates.map((point) => `${point.x},${point.inboundY}`).join(' ')
  const outboundPolyline = coordinates.map((point) => `${point.x},${point.outboundY}`).join(' ')

  return (
    <Stack gap="sm">
      <Group gap="md">
        <Group gap={8} wrap="nowrap">
          <span
            aria-hidden="true"
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: '#2f9e44',
              display: 'inline-block',
            }}
          />
          <Text size="sm">Ulaz</Text>
        </Group>

        <Group gap={8} wrap="nowrap">
          <span
            aria-hidden="true"
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: '#c92a2a',
              display: 'inline-block',
            }}
          />
          <Text size="sm">Izlaz</Text>
        </Group>
      </Group>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <svg
          aria-label="Graf kretanja ulaza i izlaza"
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', minWidth: 560, display: 'block' }}
        >
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = padding.top + plotHeight - ratio * plotHeight
            return (
              <line
                key={ratio}
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="#e9ecef"
                strokeWidth="1"
              />
            )
          })}

          <polyline
            fill="none"
            stroke="#2f9e44"
            strokeWidth="3"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={inboundPolyline}
          />
          <polyline
            fill="none"
            stroke="#c92a2a"
            strokeWidth="3"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={outboundPolyline}
          />

          {coordinates.map((point, index) => (
            <g key={items[index].bucket}>
              <circle cx={point.x} cy={point.inboundY} r="4" fill="#2f9e44" />
              <circle cx={point.x} cy={point.outboundY} r="4" fill="#c92a2a" />
              {index % labelStep === 0 || index === coordinates.length - 1 ? (
                <text
                  x={point.x}
                  y={height - 16}
                  fill="#868e96"
                  fontSize="12"
                  textAnchor="middle"
                >
                  {point.label}
                </text>
              ) : null}
            </g>
          ))}
        </svg>
      </div>
    </Stack>
  )
}

export default function ReportsPage() {
  const theme = useMantineTheme()
  const { colorScheme } = useMantineColorScheme()
  const isDark = colorScheme === 'dark'
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.role === 'ADMIN'

  const initialDateTo = useMemo(() => getTodayIsoDate(), [])
  const initialDateFrom = useMemo(() => getMonthStartIsoDate(), [])

  const [activeTab, setActiveTab] = useState<ReportsTab>('stock')
  const [fatalError, setFatalError] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [pageError, setPageError] = useState<string | null>(null)

  const [categories, setCategories] = useState<ArticleCategoryLookupItem[]>([])
  const [uoms, setUoms] = useState<ArticleUomLookupItem[]>([])

  const [stockDateFrom, setStockDateFrom] = useState(initialDateFrom)
  const [stockDateTo, setStockDateTo] = useState(initialDateTo)
  const [stockCategory, setStockCategory] = useState<string | null>(null)
  const [stockReorderOnly, setStockReorderOnly] = useState(false)
  const [stockZoneFilter, setStockZoneFilter] = useState<ZoneFilter>(null)
  const [appliedStockFilters, setAppliedStockFilters] = useState<AppliedStockFilters>({
    dateFrom: initialDateFrom,
    dateTo: initialDateTo,
    category: null,
  })
  const [stockErrors, setStockErrors] = useState<{ dateFrom?: string; dateTo?: string }>({})
  const [stockOverview, setStockOverview] = useState<StockOverviewResponse | null>(null)
  const [stockLoading, setStockLoading] = useState(false)
  const [stockError, setStockError] = useState<string | null>(null)
  const [stockExportFormat, setStockExportFormat] = useState<ReportExportFormat | null>(null)

  const [surplusItems, setSurplusItems] = useState<SurplusReportItem[]>([])
  const [surplusTotal, setSurplusTotal] = useState(0)
  const [surplusLoaded, setSurplusLoaded] = useState(false)
  const [surplusLoading, setSurplusLoading] = useState(false)
  const [surplusError, setSurplusError] = useState<string | null>(null)
  const [surplusExportFormat, setSurplusExportFormat] = useState<ReportExportFormat | null>(null)

  const [transactionDateFrom, setTransactionDateFrom] = useState('')
  const [transactionDateTo, setTransactionDateTo] = useState(initialDateTo)
  const [transactionTypes, setTransactionTypes] = useState<ReportTransactionType[]>([])
  const [transactionArticleSearch, setTransactionArticleSearch] = useState('')
  const [selectedTransactionArticle, setSelectedTransactionArticle] =
    useState<TransactionArticleOption | null>(null)
  const [transactionArticleOptions, setTransactionArticleOptions] = useState<
    TransactionArticleOption[]
  >([])
  const [transactionArticleLookupError, setTransactionArticleLookupError] = useState<string | null>(
    null
  )
  const [transactionArticleLoading, setTransactionArticleLoading] = useState(false)
  const [transactionErrors, setTransactionErrors] = useState<{ dateFrom?: string; dateTo?: string }>(
    {}
  )
  const [appliedTransactionFilters, setAppliedTransactionFilters] =
    useState<AppliedTransactionFilters>({
      dateTo: initialDateTo,
      txTypes: [],
    })
  const [transactions, setTransactions] = useState<TransactionLogItem[]>([])
  const [transactionsTotal, setTransactionsTotal] = useState(0)
  const [transactionsPage, setTransactionsPage] = useState(1)
  const [transactionsLoaded, setTransactionsLoaded] = useState(false)
  const [transactionsLoading, setTransactionsLoading] = useState(false)
  const [transactionsError, setTransactionsError] = useState<string | null>(null)
  const [transactionsExportFormat, setTransactionsExportFormat] =
    useState<ReportExportFormat | null>(null)

  const [statisticsInitialized, setStatisticsInitialized] = useState(false)
  const [topPeriod, setTopPeriod] = useState<TopConsumptionPeriod>('month')
  const [topConsumption, setTopConsumption] = useState<TopConsumptionResponse | null>(null)
  const [topLoading, setTopLoading] = useState(false)
  const [topError, setTopError] = useState<string | null>(null)

  const [movementRange, setMovementRange] = useState<MovementRange>('6m')
  const [movementStatistics, setMovementStatistics] = useState<MovementStatisticsResponse | null>(null)
  const [movementLoading, setMovementLoading] = useState(false)
  const [movementError, setMovementError] = useState<string | null>(null)

  const [reorderSummary, setReorderSummary] = useState<ReorderSummaryItem[]>([])
  const [reorderSummaryLoading, setReorderSummaryLoading] = useState(false)
  const [reorderSummaryError, setReorderSummaryError] = useState<string | null>(null)

  const [personalIssuancesYear, setPersonalIssuancesYear] = useState<number | null>(null)
  const [personalIssuances, setPersonalIssuances] = useState<PersonalIssuanceStatisticsItem[]>([])
  const [personalIssuancesLoading, setPersonalIssuancesLoading] = useState(false)
  const [personalIssuancesError, setPersonalIssuancesError] = useState<string | null>(null)

  const uomMap = useMemo(() => buildUomMap(uoms), [uoms])

  const transactionSelectData = useMemo(() => {
    const seen = new Set<number>()

    return [selectedTransactionArticle, ...transactionArticleOptions].reduce<
      Array<{ value: string; label: string }>
    >((accumulator, option) => {
      if (!option || seen.has(option.id)) {
        return accumulator
      }

      seen.add(option.id)
      accumulator.push({
        value: String(option.id),
        label: option.label,
      })
      return accumulator
    }, [])
  }, [selectedTransactionArticle, transactionArticleOptions])

  const displayedStockItems = useMemo(() => {
    if (!stockOverview) {
      return []
    }

    return stockOverview.items.filter((item) => {
      if (stockReorderOnly && !isReorderZone(item.reorder_status)) {
        return false
      }

      if (stockZoneFilter && item.reorder_status !== stockZoneFilter) {
        return false
      }

      return true
    })
  }, [stockOverview, stockReorderOnly, stockZoneFilter])

  const loadInitialData = useCallback(
    async (query: { dateFrom: string; dateTo: string; category?: string | null }) => {
      setPageLoading(true)
      setPageError(null)
      setFatalError(false)

      try {
        const [categoryResponse, uomResponse, stockResponse] = await runWithRetry(() =>
          Promise.all([
            articlesApi.lookupCategories(),
            articlesApi.lookupUoms(),
            reportsApi.getStockOverview({
              dateFrom: query.dateFrom,
              dateTo: query.dateTo,
              category: query.category,
            }),
          ])
        )

        setCategories(categoryResponse)
        setUoms(uomResponse)
        setStockOverview(stockResponse)
        setAppliedStockFilters(query)
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        setPageError(getApiErrorBody(error)?.message ?? 'Izvještaji nisu dostupni.')
      } finally {
        setPageLoading(false)
      }
    },
    []
  )

  const loadStockOverview = useCallback(
    async (query: { dateFrom: string; dateTo: string; category?: string | null }) => {
      setStockLoading(true)
      setStockError(null)
      setFatalError(false)

      try {
        const response = await runWithRetry(() =>
          reportsApi.getStockOverview({
            dateFrom: query.dateFrom,
            dateTo: query.dateTo,
            category: query.category,
          })
        )

        setStockOverview(response)
        setAppliedStockFilters(query)
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        setStockError(getApiErrorBody(error)?.message ?? 'Pregled zaliha nije dostupan.')
      } finally {
        setStockLoading(false)
      }
    },
    []
  )

  const loadSurplus = useCallback(async () => {
    setSurplusLoading(true)
    setSurplusError(null)
    setFatalError(false)

    try {
      const response = await runWithRetry(() => reportsApi.getSurplus())
      setSurplusItems(response.items)
      setSurplusTotal(response.total)
      setSurplusLoaded(true)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setSurplusError(getApiErrorBody(error)?.message ?? 'Popis viškova nije dostupan.')
    } finally {
      setSurplusLoaded(true)
      setSurplusLoading(false)
    }
  }, [])

  const loadTransactions = useCallback(
    async (query: TransactionLogQuery, nextAppliedFilters?: AppliedTransactionFilters) => {
      setTransactionsLoading(true)
      setTransactionsError(null)
      setFatalError(false)

      try {
        const response = await runWithRetry(() => reportsApi.getTransactions(query))
        setTransactions(response.items)
        setTransactionsTotal(response.total)
        setTransactionsPage(response.page)
        setTransactionsLoaded(true)
        if (nextAppliedFilters) {
          setAppliedTransactionFilters(nextAppliedFilters)
        }
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        setTransactionsError(
          getApiErrorBody(error)?.message ?? 'Transakcijski dnevnik nije dostupan.'
        )
      } finally {
        setTransactionsLoaded(true)
        setTransactionsLoading(false)
      }
    },
    []
  )

  const loadTopConsumption = useCallback(async (period: TopConsumptionPeriod) => {
    setTopLoading(true)
    setTopError(null)
    setFatalError(false)

    try {
      const response = await runWithRetry(() => reportsApi.getTopConsumption(period))
      setTopConsumption(response)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setTopError(getApiErrorBody(error)?.message ?? 'Statistika potrošnje nije dostupna.')
    } finally {
      setTopLoading(false)
    }
  }, [])

  const loadMovementStatistics = useCallback(async (range: MovementRange) => {
    setMovementLoading(true)
    setMovementError(null)
    setFatalError(false)

    try {
      const response = await runWithRetry(() => reportsApi.getMovementStatistics(range))
      setMovementStatistics(response)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setMovementError(getApiErrorBody(error)?.message ?? 'Trendovi kretanja nisu dostupni.')
    } finally {
      setMovementLoading(false)
    }
  }, [])

  const loadReorderSummary = useCallback(async () => {
    setReorderSummaryLoading(true)
    setReorderSummaryError(null)
    setFatalError(false)

    try {
      const response = await runWithRetry(() => reportsApi.getReorderSummary())
      setReorderSummary(response.items)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setReorderSummaryError(getApiErrorBody(error)?.message ?? 'Sažetak zona nije dostupan.')
    } finally {
      setReorderSummaryLoading(false)
    }
  }, [])

  const loadPersonalIssuances = useCallback(async () => {
    setPersonalIssuancesLoading(true)
    setPersonalIssuancesError(null)
    setFatalError(false)

    try {
      const response = await runWithRetry(() => reportsApi.getPersonalIssuancesStatistics())
      setPersonalIssuancesYear(response.year)
      setPersonalIssuances(response.items)
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      setPersonalIssuancesError(
        getApiErrorBody(error)?.message ?? 'Osobna izdavanja nisu dostupna.'
      )
    } finally {
      setPersonalIssuancesLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadInitialData({
      dateFrom: initialDateFrom,
      dateTo: initialDateTo,
      category: null,
    })
  }, [initialDateFrom, initialDateTo, loadInitialData])

  useEffect(() => {
    if (activeTab !== 'surplus' || surplusLoaded || surplusLoading) {
      return
    }

    void loadSurplus()
  }, [activeTab, loadSurplus, surplusLoaded, surplusLoading])

  useEffect(() => {
    if (activeTab !== 'transactions' || transactionsLoaded || transactionsLoading) {
      return
    }

    void loadTransactions(
      {
        dateTo: transactionDateTo || undefined,
        page: 1,
        perPage: TRANSACTIONS_PER_PAGE,
      },
      {
        dateTo: transactionDateTo || undefined,
        txTypes: [],
      }
    )
  }, [activeTab, loadTransactions, transactionDateTo, transactionsLoaded, transactionsLoading])

  useEffect(() => {
    if (activeTab !== 'statistics' || statisticsInitialized) {
      return
    }

    setStatisticsInitialized(true)
    void loadTopConsumption(topPeriod)
    void loadMovementStatistics(movementRange)
    void loadReorderSummary()
    void loadPersonalIssuances()
  }, [
    activeTab,
    loadMovementStatistics,
    loadPersonalIssuances,
    loadReorderSummary,
    loadTopConsumption,
    movementRange,
    statisticsInitialized,
    topPeriod,
  ])

  useEffect(() => {
    if (activeTab !== 'transactions') {
      return
    }

    const searchQuery = transactionArticleSearch.trim()
    if (searchQuery.length < 2 || searchQuery === selectedTransactionArticle?.label) {
      if (!selectedTransactionArticle) {
        setTransactionArticleOptions([])
      }
      setTransactionArticleLookupError(null)
      setTransactionArticleLoading(false)
      return
    }

    const timer = window.setTimeout(async () => {
      setTransactionArticleLoading(true)
      setTransactionArticleLookupError(null)
      setFatalError(false)

      try {
        const response = await runWithRetry(() =>
          articlesApi.listWarehouse({
            page: 1,
            perPage: 10,
            q: searchQuery,
            includeInactive: true,
          })
        )

        setTransactionArticleOptions(response.items.map(mapArticleOption))
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        setTransactionArticleLookupError(
          getApiErrorBody(error)?.message ?? 'Pretraga artikala nije uspjela.'
        )
      } finally {
        setTransactionArticleLoading(false)
      }
    }, 300)

    return () => window.clearTimeout(timer)
  }, [activeTab, selectedTransactionArticle, transactionArticleSearch])

  const handleRetryPage = useCallback(() => {
    void loadInitialData({
      dateFrom: stockDateFrom,
      dateTo: stockDateTo,
      category: stockCategory,
    })
  }, [loadInitialData, stockCategory, stockDateFrom, stockDateTo])

  const handleApplyStockFilters = useCallback(() => {
    const errors = validateStockDateRange(stockDateFrom, stockDateTo)
    setStockErrors(errors)

    if (errors.dateFrom || errors.dateTo) {
      return
    }

    void loadStockOverview({
      dateFrom: stockDateFrom,
      dateTo: stockDateTo,
      category: stockCategory,
    })
  }, [loadStockOverview, stockCategory, stockDateFrom, stockDateTo])

  const handleStockExport = useCallback(
    async (format: ReportExportFormat) => {
      setStockExportFormat(format)

      try {
        await runWithRetry(() =>
          reportsApi.exportStockOverview(format, {
            dateFrom: appliedStockFilters.dateFrom,
            dateTo: appliedStockFilters.dateTo,
            category: appliedStockFilters.category,
            reorderOnly: stockReorderOnly,
          })
        )
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        showErrorToast((await getApiErrorBodyAsync(error))?.message ?? 'Izvoz pregleda zaliha nije uspio.')
      } finally {
        setStockExportFormat(null)
      }
    },
    [appliedStockFilters, stockReorderOnly]
  )

  const handleSurplusExport = useCallback(async (format: ReportExportFormat) => {
    setSurplusExportFormat(format)

    try {
      await runWithRetry(() => reportsApi.exportSurplus(format))
    } catch (error) {
      if (isNetworkOrServerError(error)) {
        setFatalError(true)
        return
      }

      showErrorToast((await getApiErrorBodyAsync(error))?.message ?? 'Izvoz viškova nije uspio.')
    } finally {
      setSurplusExportFormat(null)
    }
  }, [])

  const handleApplyTransactionFilters = useCallback(() => {
    const errors = validateOptionalDateRange(transactionDateFrom, transactionDateTo)
    setTransactionErrors(errors)

    if (errors.dateFrom || errors.dateTo) {
      return
    }

    const nextAppliedFilters: AppliedTransactionFilters = {
      articleId: selectedTransactionArticle?.id ?? undefined,
      dateFrom: transactionDateFrom || undefined,
      dateTo: transactionDateTo || undefined,
      txTypes: transactionTypes,
    }

    void loadTransactions(
      {
        ...nextAppliedFilters,
        page: 1,
        perPage: TRANSACTIONS_PER_PAGE,
      },
      nextAppliedFilters
    )
  }, [
    loadTransactions,
    selectedTransactionArticle,
    transactionDateFrom,
    transactionDateTo,
    transactionTypes,
  ])

  const handleTransactionPageChange = useCallback(
    (page: number) => {
      void loadTransactions({
        articleId: appliedTransactionFilters.articleId,
        dateFrom: appliedTransactionFilters.dateFrom,
        dateTo: appliedTransactionFilters.dateTo,
        txTypes: appliedTransactionFilters.txTypes,
        page,
        perPage: TRANSACTIONS_PER_PAGE,
      })
    },
    [appliedTransactionFilters, loadTransactions]
  )

  const handleTransactionsExport = useCallback(
    async (format: ReportExportFormat) => {
      setTransactionsExportFormat(format)

      try {
        await runWithRetry(() =>
          reportsApi.exportTransactions(format, {
            articleId: appliedTransactionFilters.articleId,
            dateFrom: appliedTransactionFilters.dateFrom,
            dateTo: appliedTransactionFilters.dateTo,
            txTypes: appliedTransactionFilters.txTypes,
          })
        )
      } catch (error) {
        if (isNetworkOrServerError(error)) {
          setFatalError(true)
          return
        }

        showErrorToast((await getApiErrorBodyAsync(error))?.message ?? 'Izvoz transakcija nije uspio.')
      } finally {
        setTransactionsExportFormat(null)
      }
    },
    [appliedTransactionFilters]
  )

  const handleTopPeriodChange = useCallback(
    (value: string) => {
      const nextPeriod = value as TopConsumptionPeriod
      setTopPeriod(nextPeriod)
      if (activeTab === 'statistics') {
        void loadTopConsumption(nextPeriod)
      }
    },
    [activeTab, loadTopConsumption]
  )

  const handleMovementRangeChange = useCallback(
    (value: string) => {
      const nextRange = value as MovementRange
      setMovementRange(nextRange)
      if (activeTab === 'statistics') {
        void loadMovementStatistics(nextRange)
      }
    },
    [activeTab, loadMovementStatistics]
  )

  const handleTopConsumptionSelect = useCallback(
    (item: TopConsumptionItem) => {
      const selectedArticle = {
        id: item.article_id,
        articleNo: item.article_no,
        description: item.description,
        label: buildTransactionArticleLabel(item.article_no, item.description),
      }
      const nextDateFrom = topConsumption?.date_from ?? ''
      const nextDateTo = topConsumption?.date_to ?? getTodayIsoDate()

      setSelectedTransactionArticle(selectedArticle)
      setTransactionArticleSearch(selectedArticle.label)
      setTransactionDateFrom(nextDateFrom)
      setTransactionDateTo(nextDateTo)
      setTransactionTypes([])
      setTransactionErrors({})
      setActiveTab('transactions')

      void loadTransactions(
        {
          articleId: selectedArticle.id,
          dateFrom: nextDateFrom || undefined,
          dateTo: nextDateTo || undefined,
          txTypes: [],
          page: 1,
          perPage: TRANSACTIONS_PER_PAGE,
        },
        {
          articleId: selectedArticle.id,
          dateFrom: nextDateFrom || undefined,
          dateTo: nextDateTo || undefined,
          txTypes: [],
        }
      )
    },
    [loadTransactions, topConsumption]
  )

  const handleReorderDrilldown = useCallback((status: ZoneFilter) => {
    if (!status) {
      return
    }

    setStockZoneFilter(status)
    setStockReorderOnly(false)
    setActiveTab('stock')
  }, [])

  if (fatalError) {
    return (
      <FullPageState
        title="Greška pri povezivanju"
        message={REPORTS_CONNECTION_ERROR_MESSAGE}
        actionLabel="Pokušaj ponovno"
        onAction={() => window.location.reload()}
      />
    )
  }

  if (pageLoading) {
    return <FullPageState title="Učitavanje…" loading />
  }

  if (pageError) {
    return (
      <FullPageState
        title="Izvještaji nisu dostupni."
        message={pageError}
        actionLabel="Pokušaj ponovno"
        onAction={handleRetryPage}
      />
    )
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>Izvještaji</Title>
          <Text c="dimmed" mt={4}>
            Pregled zaliha, viškova, transakcija i ključnih trendova skladišta.
          </Text>
        </div>
      </Group>

      <Tabs
        value={activeTab}
        onChange={(value) => setActiveTab((value as ReportsTab | null) ?? 'stock')}
      >
        <Tabs.List>
          <Tabs.Tab value="stock" leftSection={<IconPackage size={16} />}>
            Doseg zaliha
          </Tabs.Tab>
          <Tabs.Tab value="surplus" leftSection={<IconListDetails size={16} />}>
            Viškovi
          </Tabs.Tab>
          <Tabs.Tab value="transactions" leftSection={<IconPackage size={16} />}>
            Transakcijski dnevnik
          </Tabs.Tab>
          <Tabs.Tab value="statistics" leftSection={<IconChartBar size={16} />}>
            Statistike
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="stock" pt="md">
          <Stack gap="lg">
            <Paper withBorder radius="lg" p="lg">
              <Stack gap="md">
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Title order={3}>Doseg zaliha</Title>
                    <Text c="dimmed" mt={4}>
                      Pregled trenutne raspoloživosti i potrošnje po artiklu.
                    </Text>
                  </div>

                  {isAdmin ? (
                    <Group>
                      <Button
                        variant="default"
                        leftSection={<IconFileSpreadsheet size={16} />}
                        loading={stockExportFormat === 'xlsx'}
                        disabled={stockExportFormat !== null}
                        onClick={() => void handleStockExport('xlsx')}
                      >
                        Excel
                      </Button>
                      <Button
                        variant="default"
                        leftSection={<IconFileTypePdf size={16} />}
                        loading={stockExportFormat === 'pdf'}
                        disabled={stockExportFormat !== null}
                        onClick={() => void handleStockExport('pdf')}
                      >
                        PDF
                      </Button>
                    </Group>
                  ) : null}
                </Group>

                <SimpleGrid cols={{ base: 1, md: 4 }}>
                  <TextInput
                    label="Datum od"
                    type="date"
                    value={stockDateFrom}
                    onChange={(event) => {
                      setStockDateFrom(event.currentTarget.value)
                      setStockErrors((current) => ({ ...current, dateFrom: undefined }))
                    }}
                    error={stockErrors.dateFrom}
                  />

                  <TextInput
                    label="Datum do"
                    type="date"
                    value={stockDateTo}
                    onChange={(event) => {
                      setStockDateTo(event.currentTarget.value)
                      setStockErrors((current) => ({ ...current, dateTo: undefined }))
                    }}
                    error={stockErrors.dateTo}
                  />

                  <Select
                    label="Kategorija"
                    placeholder="Sve kategorije"
                    clearable
                    searchable
                    nothingFoundMessage="Nema rezultata."
                    data={categories.map((category) => ({
                      value: category.key,
                      label: category.label_hr,
                    }))}
                    value={stockCategory}
                    onChange={setStockCategory}
                  />

                  <Checkbox
                    label="Prikaži samo zonu naručivanja"
                    checked={stockReorderOnly}
                    onChange={(event) => {
                      const checked = event.currentTarget.checked
                      setStockReorderOnly(checked)
                      if (checked && stockZoneFilter === 'NORMAL') {
                        setStockZoneFilter(null)
                      }
                    }}
                    mt={28}
                  />
                </SimpleGrid>

                <Group justify="space-between" align="center">
                  <Group gap="xs">
                    <Button onClick={handleApplyStockFilters} loading={stockLoading}>
                      Primijeni filtre
                    </Button>
                    {stockLoading && stockOverview ? (
                      <Group gap="xs">
                        <Loader size="xs" />
                        <Text size="sm" c="dimmed">
                          Osvježavanje pregleda…
                        </Text>
                      </Group>
                    ) : null}
                  </Group>

                  <Text size="sm" c="dimmed">
                    Prikazano: {displayedStockItems.length}
                    {stockOverview ? ` / ${stockOverview.total}` : ''}
                  </Text>
                </Group>

                {stockZoneFilter ? (
                  <Alert
                    color={stockZoneFilter === 'RED' ? 'red' : stockZoneFilter === 'YELLOW' ? 'yellow' : 'green'}
                    title={`Aktivan drilldown: ${getReorderStatusLabel(stockZoneFilter)}`}
                  >
                    <Group justify="space-between" align="center">
                      <Text size="sm">
                        Drilldown iz kartice Statistike vrijedi samo za prikaz na stranici.
                      </Text>
                      <Button variant="subtle" size="xs" onClick={() => setStockZoneFilter(null)}>
                        Ukloni drilldown
                      </Button>
                    </Group>
                  </Alert>
                ) : null}

                {stockOverview ? (
                  <Alert color="blue" title="Ukupna vrijednost skladišta">
                    <Text size="sm" fw={600}>
                      {formatCurrency(stockOverview.summary.warehouse_total_value)}
                    </Text>
                    {stockOverview.items.some((item: StockOverviewItem) => item.unit_value === null) ? (
                      <Text size="xs" c="dimmed" mt={4}>
                        Ukupna vrijednost ne uključuje artikle bez podatka o cijeni.
                      </Text>
                    ) : null}
                  </Alert>
                ) : null}

                {stockError ? (
                  <Alert color="red" title="Pregled zaliha nije dostupan">
                    {stockError}
                  </Alert>
                ) : null}

                {!stockOverview || (stockLoading && !stockOverview.items.length) ? (
                  <Paper withBorder radius="lg" p="xl">
                    <Group justify="center" py="xl">
                      <Loader />
                    </Group>
                  </Paper>
                ) : (
                  <ScrollArea>
                    <Table withTableBorder striped highlightOnHover verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Broj artikla</Table.Th>
                          <Table.Th>Opis</Table.Th>
                          <Table.Th>Dobavljač</Table.Th>
                          <Table.Th>Zaliha</Table.Th>
                          <Table.Th>Višak</Table.Th>
                          <Table.Th>Ukupno dostupno</Table.Th>
                          <Table.Th>Ulaz (period)</Table.Th>
                          <Table.Th>Izlaz (period)</Table.Th>
                          <Table.Th>Prosj. mjesečna potrošnja</Table.Th>
                          <Table.Th>Pokrivenost (mj.)</Table.Th>
                          <Table.Th>Prag naručivanja</Table.Th>
                          <Table.Th>Status</Table.Th>
                          <Table.Th>Vrijednost / jed.</Table.Th>
                          <Table.Th>Ukupna vrijednost</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {displayedStockItems.length === 0 ? (
                          <Table.Tr>
                            <Table.Td colSpan={14}>
                              <Text c="dimmed" ta="center" py="md">
                                {stockZoneFilter
                                  ? 'Nema artikala u odabranoj zoni za trenutne filtre.'
                                  : 'Nema artikala za odabrane filtre.'}
                              </Text>
                            </Table.Td>
                          </Table.Tr>
                        ) : (
                          displayedStockItems.map((item: StockOverviewItem) => (
                            <Table.Tr key={item.article_id}>
                              <Table.Td>{item.article_no}</Table.Td>
                              <Table.Td>{item.description}</Table.Td>
                              <Table.Td>{item.supplier_name ?? '—'}</Table.Td>
                              <Table.Td>{formatQuantity(item.stock, item.uom, uomMap)}</Table.Td>
                              <Table.Td>{formatOptionalQuantity(item.surplus, item.uom, uomMap)}</Table.Td>
                              <Table.Td>
                                {formatQuantity(item.total_available, item.uom, uomMap)}
                              </Table.Td>
                              <Table.Td>{formatQuantity(item.inbound, item.uom, uomMap)}</Table.Td>
                              <Table.Td>{formatQuantity(item.outbound, item.uom, uomMap)}</Table.Td>
                              <Table.Td>{formatDecimal(item.avg_monthly_consumption, 2)}</Table.Td>
                              <Table.Td>{formatCoverageMonths(item.coverage_months)}</Table.Td>
                              <Table.Td>
                                {item.reorder_threshold === null
                                  ? '—'
                                  : formatQuantity(item.reorder_threshold, item.uom, uomMap)}
                              </Table.Td>
                              <Table.Td>
                                <ReorderStatusBadge status={item.reorder_status} />
                              </Table.Td>
                              <Table.Td>{formatCurrency(item.unit_value)}</Table.Td>
                              <Table.Td>{formatCurrency(item.total_value)}</Table.Td>
                            </Table.Tr>
                          ))
                        )}
                      </Table.Tbody>
                    </Table>
                  </ScrollArea>
                )}
              </Stack>
            </Paper>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="surplus" pt="md">
          <Paper withBorder radius="lg" p="lg">
            <Stack gap="md">
              <Group justify="space-between" align="flex-start">
                <div>
                  <Title order={3}>Viškovi</Title>
                  <Text c="dimmed" mt={4}>
                    Evidentirani višak materijala otkriven tijekom inventure.
                  </Text>
                </div>

                <Group>
                  <Button variant="default" onClick={() => void loadSurplus()} loading={surplusLoading}>
                    Osvježi
                  </Button>
                  {isAdmin ? (
                    <>
                      <Button
                        variant="default"
                        leftSection={<IconFileSpreadsheet size={16} />}
                        loading={surplusExportFormat === 'xlsx'}
                        disabled={surplusExportFormat !== null}
                        onClick={() => void handleSurplusExport('xlsx')}
                      >
                        Excel
                      </Button>
                      <Button
                        variant="default"
                        leftSection={<IconFileTypePdf size={16} />}
                        loading={surplusExportFormat === 'pdf'}
                        disabled={surplusExportFormat !== null}
                        onClick={() => void handleSurplusExport('pdf')}
                      >
                        PDF
                      </Button>
                    </>
                  ) : null}
                </Group>
              </Group>

              {surplusError ? (
                <Alert color="red" title="Popis viškova nije dostupan">
                  {surplusError}
                </Alert>
              ) : null}

              {surplusLoading && !surplusLoaded ? (
                <Paper withBorder radius="lg" p="xl">
                  <Group justify="center" py="xl">
                    <Loader />
                  </Group>
                </Paper>
              ) : (
                <>
                  <Text size="sm" c="dimmed">
                    Ukupno stavki: {surplusTotal}
                  </Text>

                  <ScrollArea>
                    <Table withTableBorder striped highlightOnHover verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Broj artikla</Table.Th>
                          <Table.Th>Opis</Table.Th>
                          <Table.Th>Šarža</Table.Th>
                          <Table.Th>Rok trajanja</Table.Th>
                          <Table.Th>Količina viška</Table.Th>
                          <Table.Th>Otkriveno</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {surplusItems.length === 0 ? (
                          <Table.Tr>
                            <Table.Td colSpan={6}>
                              <Text c="dimmed" ta="center" py="md">
                                Nema evidentiranih viškova.
                              </Text>
                            </Table.Td>
                          </Table.Tr>
                        ) : (
                          surplusItems.map((item) => (
                            <Table.Tr key={item.id}>
                              <Table.Td>{item.article_no ?? '—'}</Table.Td>
                              <Table.Td>{item.description ?? '—'}</Table.Td>
                              <Table.Td>{item.batch_code ?? '—'}</Table.Td>
                              <Table.Td>{formatDate(item.expiry_date)}</Table.Td>
                              <Table.Td>{formatQuantity(item.surplus_qty, item.uom, uomMap)}</Table.Td>
                              <Table.Td>{formatDate(item.discovered)}</Table.Td>
                            </Table.Tr>
                          ))
                        )}
                      </Table.Tbody>
                    </Table>
                  </ScrollArea>
                </>
              )}
            </Stack>
          </Paper>
        </Tabs.Panel>

        <Tabs.Panel value="transactions" pt="md">
          <Paper withBorder radius="lg" p="lg">
            <Stack gap="md">
              <Group justify="space-between" align="flex-start">
                <div>
                  <Title order={3}>Transakcijski dnevnik</Title>
                  <Text c="dimmed" mt={4}>
                    Povijest svih kretanja zaliha po artiklu, vrsti transakcije i razdoblju.
                  </Text>
                </div>

                {isAdmin ? (
                  <Group>
                    <Button
                      variant="default"
                      leftSection={<IconFileSpreadsheet size={16} />}
                      loading={transactionsExportFormat === 'xlsx'}
                      disabled={transactionsExportFormat !== null}
                      onClick={() => void handleTransactionsExport('xlsx')}
                    >
                      Excel
                    </Button>
                    <Button
                      variant="default"
                      leftSection={<IconFileTypePdf size={16} />}
                      loading={transactionsExportFormat === 'pdf'}
                      disabled={transactionsExportFormat !== null}
                      onClick={() => void handleTransactionsExport('pdf')}
                    >
                      PDF
                    </Button>
                  </Group>
                ) : null}
              </Group>

              <SimpleGrid cols={{ base: 1, md: 2 }}>
                <Select
                  label="Artikl"
                  placeholder="Pretražite artikl"
                  searchable
                  clearable
                  data={transactionSelectData}
                  searchValue={transactionArticleSearch}
                  onSearchChange={(value) => {
                    setTransactionArticleSearch(value)
                    setTransactionArticleLookupError(null)
                    if (selectedTransactionArticle && value !== selectedTransactionArticle.label) {
                      setSelectedTransactionArticle(null)
                    }
                  }}
                  value={selectedTransactionArticle ? String(selectedTransactionArticle.id) : null}
                  onChange={(value) => {
                    if (!value) {
                      setSelectedTransactionArticle(null)
                      setTransactionArticleSearch('')
                      setTransactionArticleOptions([])
                      return
                    }

                    const selected = [selectedTransactionArticle, ...transactionArticleOptions].find(
                      (option) => option?.id === Number(value)
                    )

                    if (!selected) {
                      return
                    }

                    setSelectedTransactionArticle(selected)
                    setTransactionArticleSearch(selected.label)
                  }}
                  nothingFoundMessage={
                    transactionArticleSearch.trim().length < 2
                      ? 'Upišite najmanje 2 znaka.'
                      : 'Nema rezultata.'
                  }
                  rightSection={transactionArticleLoading ? <Loader size="xs" /> : null}
                />

                <MultiSelect
                  label="Vrsta transakcije"
                  placeholder="Sve vrste"
                  clearable
                  searchable
                  nothingFoundMessage="Nema rezultata."
                  data={TRANSACTION_TYPE_OPTIONS}
                  value={transactionTypes}
                  onChange={(value) => setTransactionTypes(value as ReportTransactionType[])}
                />
              </SimpleGrid>

              <SimpleGrid cols={{ base: 1, md: 2 }}>
                <TextInput
                  label="Datum od"
                  type="date"
                  value={transactionDateFrom}
                  onChange={(event) => {
                    setTransactionDateFrom(event.currentTarget.value)
                    setTransactionErrors((current) => ({ ...current, dateFrom: undefined }))
                  }}
                  error={transactionErrors.dateFrom}
                />

                <TextInput
                  label="Datum do"
                  type="date"
                  value={transactionDateTo}
                  onChange={(event) => {
                    setTransactionDateTo(event.currentTarget.value)
                    setTransactionErrors((current) => ({ ...current, dateTo: undefined }))
                  }}
                  error={transactionErrors.dateTo}
                />
              </SimpleGrid>

              {transactionArticleLookupError ? (
                <Alert color="red" title="Pretraga artikala nije uspjela">
                  {transactionArticleLookupError}
                </Alert>
              ) : null}

              {transactionsError ? (
                <Alert color="red" title="Transakcijski dnevnik nije dostupan">
                  {transactionsError}
                </Alert>
              ) : null}

              <Group justify="space-between" align="center">
                <Group gap="xs">
                  <Button onClick={handleApplyTransactionFilters} loading={transactionsLoading}>
                    Primijeni filtre
                  </Button>
                  {transactionsLoading && transactionsLoaded ? (
                    <Group gap="xs">
                      <Loader size="xs" />
                      <Text size="sm" c="dimmed">
                        Osvježavanje dnevnika…
                      </Text>
                    </Group>
                  ) : null}
                </Group>

                <Text size="sm" c="dimmed">
                  Ukupno zapisa: {transactionsTotal}
                </Text>
              </Group>

              {transactionsLoading && !transactionsLoaded ? (
                <Paper withBorder radius="lg" p="xl">
                  <Group justify="center" py="xl">
                    <Loader />
                  </Group>
                </Paper>
              ) : (
                <>
                  <ScrollArea>
                    <Table withTableBorder striped highlightOnHover verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Datum i vrijeme</Table.Th>
                          <Table.Th>Broj artikla</Table.Th>
                          <Table.Th>Opis</Table.Th>
                          <Table.Th>Vrsta</Table.Th>
                          <Table.Th>Količina</Table.Th>
                          <Table.Th>Šarža</Table.Th>
                          <Table.Th>Referenca</Table.Th>
                          <Table.Th>Korisnik</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {transactions.length === 0 ? (
                          <Table.Tr>
                            <Table.Td colSpan={8}>
                              <Text c="dimmed" ta="center" py="md">
                                Nema transakcija za odabrane filtre.
                              </Text>
                            </Table.Td>
                          </Table.Tr>
                        ) : (
                          transactions.map((item) => (
                            <Table.Tr key={item.id}>
                              <Table.Td>{formatDateTime(item.occurred_at)}</Table.Td>
                              <Table.Td>{item.article_no ?? '—'}</Table.Td>
                              <Table.Td>{item.description ?? '—'}</Table.Td>
                              <Table.Td>{getTransactionTypeLabel(item.type)}</Table.Td>
                              <Table.Td>{formatSignedQuantity(item.quantity, item.uom, uomMap)}</Table.Td>
                              <Table.Td>{item.batch_code ?? '—'}</Table.Td>
                              <Table.Td>{item.reference ?? '—'}</Table.Td>
                              <Table.Td>{item.user ?? '—'}</Table.Td>
                            </Table.Tr>
                          ))
                        )}
                      </Table.Tbody>
                    </Table>
                  </ScrollArea>

                  {Math.ceil(transactionsTotal / TRANSACTIONS_PER_PAGE) > 1 ? (
                    <Group justify="center">
                      <Pagination
                        total={Math.max(1, Math.ceil(transactionsTotal / TRANSACTIONS_PER_PAGE))}
                        value={transactionsPage}
                        onChange={handleTransactionPageChange}
                      />
                    </Group>
                  ) : null}
                </>
              )}
            </Stack>
          </Paper>
        </Tabs.Panel>

        <Tabs.Panel value="statistics" pt="md">
          <Stack gap="lg">
            <SimpleGrid cols={{ base: 1, md: 2 }}>
              <Paper withBorder radius="lg" p="lg">
                <Stack gap="md">
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Group gap="xs">
                        <IconChartBar size={18} />
                        <Title order={3}>Top 10 po potrošnji</Title>
                      </Group>
                      <Text c="dimmed" mt={4}>
                        Najviše trošeni artikli u odabranom razdoblju.
                      </Text>
                    </div>

                    <SegmentedControl
                      value={topPeriod}
                      onChange={handleTopPeriodChange}
                      disabled={topLoading}
                      data={[
                        { value: 'week', label: 'Tjedan' },
                        { value: 'month', label: 'Mjesec' },
                        { value: 'year', label: 'Godina' },
                      ]}
                    />
                  </Group>

                  {topError ? (
                    <Alert color="red" title="Statistika potrošnje nije dostupna">
                      {topError}
                    </Alert>
                  ) : null}

                  {topLoading && !topConsumption ? (
                    <Group justify="center" py="xl">
                      <Loader />
                    </Group>
                  ) : topConsumption && topConsumption.items.length > 0 ? (
                    <>
                      <Text size="sm" c="dimmed">
                        Razdoblje: {formatDate(topConsumption.date_from)} -{' '}
                        {formatDate(topConsumption.date_to)}
                      </Text>
                      <ConsumptionBarChart
                        items={topConsumption.items}
                        onSelect={handleTopConsumptionSelect}
                        uomMap={uomMap}
                      />
                    </>
                  ) : (
                    <Text c="dimmed" ta="center" py="xl">
                      Nema potrošnje za odabrano razdoblje.
                    </Text>
                  )}
                </Stack>
              </Paper>

              <Paper withBorder radius="lg" p="lg">
                <Stack gap="md">
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Group gap="xs">
                        <IconChartLine size={18} />
                        <Title order={3}>Ulaz i izlaz kroz vrijeme</Title>
                      </Group>
                      <Text c="dimmed" mt={4}>
                        Trendovi ulaza i izlaza po tjednima ili mjesecima.
                      </Text>
                    </div>

                    <SegmentedControl
                      value={movementRange}
                      onChange={handleMovementRangeChange}
                      disabled={movementLoading}
                      data={[
                        { value: '3m', label: '3 mj.' },
                        { value: '6m', label: '6 mj.' },
                        { value: '12m', label: '12 mj.' },
                      ]}
                    />
                  </Group>

                  {movementError ? (
                    <Alert color="red" title="Trendovi kretanja nisu dostupni">
                      {movementError}
                    </Alert>
                  ) : null}

                  {movementLoading && !movementStatistics ? (
                    <Group justify="center" py="xl">
                      <Loader />
                    </Group>
                  ) : movementStatistics ? (
                    <>
                      <MovementLineChart items={movementStatistics.items} />
                      <Text size="sm" c="dimmed">
                        {movementStatistics.note}
                      </Text>
                    </>
                  ) : (
                    <Text c="dimmed" ta="center" py="xl">
                      Nema podataka za prikaz trendova.
                    </Text>
                  )}
                </Stack>
              </Paper>
            </SimpleGrid>

            <SimpleGrid cols={{ base: 1, md: 3 }}>
              <Paper withBorder radius="lg" p="lg">
                <Stack gap="md">
                  <Title order={3}>Sažetak zona naručivanja</Title>
                  <Text c="dimmed">
                    Klik na zonu otvara Doseg zaliha s lokalnim drilldown filtrom.
                  </Text>

                  {reorderSummaryError ? (
                    <Alert color="red" title="Sažetak zona nije dostupan">
                      {reorderSummaryError}
                    </Alert>
                  ) : null}

                  {reorderSummaryLoading && reorderSummary.length === 0 ? (
                    <Group justify="center" py="xl">
                      <Loader />
                    </Group>
                  ) : (
                    <Stack gap="sm">
                      {reorderSummary.map((item) => (
                        <button
                          key={item.reorder_status}
                          type="button"
                          onClick={() => handleReorderDrilldown(item.reorder_status as ZoneFilter)}
                          style={{
                            border: `1px solid ${isDark ? theme.colors.dark[4] : '#e9ecef'}`,
                            borderRadius: 14,
                            background: isDark ? theme.colors.dark[6] : '#fff',
                            padding: '0.95rem 1rem',
                            textAlign: 'left',
                            cursor: 'pointer',
                          }}
                        >
                          <Group justify="space-between" align="center">
                            <Group gap="sm" wrap="nowrap">
                              <span
                                aria-hidden="true"
                                style={{
                                  width: 12,
                                  height: 12,
                                  borderRadius: '50%',
                                  display: 'inline-block',
                                  background: getReorderStatusColor(item.reorder_status),
                                }}
                              />
                              <Text fw={600}>{getReorderStatusLabel(item.reorder_status)}</Text>
                            </Group>
                            <Badge color={getReorderStatusBadgeColor(item.reorder_status)} variant="light">
                              {item.count}
                            </Badge>
                          </Group>
                        </button>
                      ))}
                    </Stack>
                  )}
                </Stack>
              </Paper>

              <Paper withBorder radius="lg" p="lg" style={{ gridColumn: 'span 2' }}>
                <Stack gap="md">
                  <Title order={4}>Osobna izdavanja</Title>
                  <Text c="dimmed">
                    {personalIssuancesYear
                      ? `Pregled izdanja po zaposleniku za ${personalIssuancesYear}.`
                      : 'Pregled izdanja po zaposleniku za tekuću godinu.'}
                  </Text>

                  {personalIssuancesError ? (
                    <Alert color="red" title="Osobna izdavanja nisu dostupna">
                      {personalIssuancesError}
                    </Alert>
                  ) : null}

                  {personalIssuancesLoading && personalIssuances.length === 0 ? (
                    <Group justify="center" py="xl">
                      <Loader />
                    </Group>
                  ) : (
                    <ScrollArea>
                      <Table withTableBorder striped highlightOnHover verticalSpacing="sm">
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>Zaposlenik</Table.Th>
                            <Table.Th>Radno mjesto</Table.Th>
                            <Table.Th>Artikl</Table.Th>
                            <Table.Th>Izdano ove godine</Table.Th>
                            <Table.Th>Kvota</Table.Th>
                            <Table.Th>Preostalo</Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {personalIssuances.length === 0 ? (
                            <Table.Tr>
                              <Table.Td colSpan={6}>
                                <Text c="dimmed" ta="center" py="md">
                                  Nema osobnih izdavanja za tekuću godinu.
                                </Text>
                              </Table.Td>
                            </Table.Tr>
                          ) : (
                            personalIssuances.map((item) => (
                              <Table.Tr key={`${item.employee_id}-${item.article_id}`}>
                                <Table.Td>{item.employee_name ?? '—'}</Table.Td>
                                <Table.Td>{item.job_title ?? '—'}</Table.Td>
                                <Table.Td>
                                  <Stack gap={2}>
                                    <Text size="sm" fw={500}>
                                      {item.article}
                                    </Text>
                                    <Text size="xs" c="dimmed">
                                      {item.article_no}
                                    </Text>
                                  </Stack>
                                </Table.Td>
                                <Table.Td>
                                  {formatQuantity(item.quantity_issued, item.uom ?? item.quota_uom, uomMap)}
                                </Table.Td>
                                <Table.Td>
                                  {item.quota === null
                                    ? '—'
                                    : formatQuantity(item.quota, item.quota_uom ?? item.uom, uomMap)}
                                </Table.Td>
                                <Table.Td>
                                  {item.remaining === null
                                    ? '—'
                                    : formatQuantity(item.remaining, item.quota_uom ?? item.uom, uomMap)}
                                </Table.Td>
                              </Table.Tr>
                            ))
                          )}
                        </Table.Tbody>
                      </Table>
                    </ScrollArea>
                  )}
                </Stack>
              </Paper>
            </SimpleGrid>
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}
