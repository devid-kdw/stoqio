import type { InventoryCountLine } from '../../api/inventory'

export interface BatchGroup {
  article_id: number
  article_no: string | null
  description: string | null
  uom: string
  decimal_display: boolean
  lines: InventoryCountLine[]
}

export type ActiveDisplayItem =
  | { kind: 'non-batch'; line: InventoryCountLine }
  | { kind: 'batch-group'; group: BatchGroup }

export type FilteredDisplayItem =
  | { kind: 'non-batch'; line: InventoryCountLine }
  | { kind: 'batch-group'; group: BatchGroup; visibleChildren: InventoryCountLine[] }

export function resolveCountedQuantity(
  editValue: number | string | undefined,
  savedQty: number | null
): number | null {
  return typeof editValue === 'number' ? editValue : savedQty
}

export function buildActiveDisplayItems(lines: InventoryCountLine[]): ActiveDisplayItem[] {
  const items: ActiveDisplayItem[] = []
  const seenArticles = new Set<number>()
  const groups = new Map<number, BatchGroup>()

  for (const line of lines) {
    if (line.batch_id !== null && line.article_id !== null) {
      if (!groups.has(line.article_id)) {
        groups.set(line.article_id, {
          article_id: line.article_id,
          article_no: line.article_no,
          description: line.description,
          uom: line.uom,
          decimal_display: line.decimal_display,
          lines: [],
        })
      }
      groups.get(line.article_id)!.lines.push(line)
    }
  }

  for (const line of lines) {
    if (line.batch_id === null) {
      items.push({ kind: 'non-batch', line })
    } else if (line.article_id !== null && !seenArticles.has(line.article_id)) {
      seenArticles.add(line.article_id)
      items.push({ kind: 'batch-group', group: groups.get(line.article_id)! })
    }
  }

  return items
}

interface FilterActiveDisplayItemsOptions {
  filterDiscrepancies: boolean
  filterUncounted: boolean
  getLocalCounted: (line: InventoryCountLine) => number | null
}

export function filterActiveDisplayItems(
  items: ActiveDisplayItem[],
  { filterDiscrepancies, filterUncounted, getLocalCounted }: FilterActiveDisplayItemsOptions
): FilteredDisplayItem[] {
  const filteredItems: FilteredDisplayItem[] = []

  for (const item of items) {
    if (item.kind === 'non-batch') {
      const line = item.line
      const localCounted = getLocalCounted(line)
      if (filterUncounted && localCounted !== null) continue
      if (filterDiscrepancies) {
        if (localCounted === null) continue
        if (localCounted === line.system_quantity) continue
      }
      filteredItems.push({ kind: 'non-batch', line })
      continue
    }

    const visibleChildren = item.group.lines.filter((line) => {
      const localCounted = getLocalCounted(line)
      if (filterUncounted && localCounted !== null) return false
      if (filterDiscrepancies) {
        if (localCounted === null) return false
        if (localCounted === line.system_quantity) return false
      }
      return true
    })

    if (visibleChildren.length > 0) {
      filteredItems.push({ kind: 'batch-group', group: item.group, visibleChildren })
    }
  }

  return filteredItems
}
