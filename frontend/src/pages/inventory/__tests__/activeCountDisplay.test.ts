import { describe, expect, it } from 'vitest'

import type { InventoryCountLine } from '../../../api/inventory'
import {
  buildActiveDisplayItems,
  filterActiveDisplayItems,
  resolveCountedQuantity,
} from '../activeCountDisplay'

function makeLine(overrides: Partial<InventoryCountLine>): InventoryCountLine {
  return {
    line_id: 1,
    article_id: 1,
    article_no: 'INV-001',
    description: 'Test article',
    batch_id: null,
    batch_code: null,
    expiry_date: null,
    system_quantity: 10,
    counted_quantity: null,
    difference: null,
    uom: 'kom',
    decimal_display: false,
    resolution: null,
    ...overrides,
  }
}

describe('activeCountDisplay helpers', () => {
  it('groups batch-tracked lines under a single article entry while keeping list order', () => {
    const items = buildActiveDisplayItems([
      makeLine({ line_id: 1, article_id: 1, article_no: 'INV-001', batch_id: null }),
      makeLine({
        line_id: 2,
        article_id: 2,
        article_no: 'INV-002',
        batch_id: 21,
        batch_code: 'B-21',
      }),
      makeLine({
        line_id: 3,
        article_id: 2,
        article_no: 'INV-002',
        batch_id: 22,
        batch_code: 'B-22',
      }),
      makeLine({ line_id: 4, article_id: 3, article_no: 'INV-003', batch_id: null }),
    ])

    expect(items).toHaveLength(3)
    expect(items[0]).toMatchObject({ kind: 'non-batch', line: { line_id: 1 } })
    expect(items[2]).toMatchObject({ kind: 'non-batch', line: { line_id: 4 } })

    expect(items[1].kind).toBe('batch-group')
    if (items[1].kind !== 'batch-group') {
      throw new Error('Expected batch-group entry')
    }

    expect(items[1].group.article_id).toBe(2)
    expect(items[1].group.lines.map((line) => line.line_id)).toEqual([2, 3])
  })

  it('keeps only discrepant batch children when discrepancy filter is enabled', () => {
    const lines = [
      makeLine({
        line_id: 10,
        article_id: 4,
        article_no: 'INV-004',
        batch_id: 41,
        batch_code: 'B-41',
        system_quantity: 5,
        counted_quantity: 5,
      }),
      makeLine({
        line_id: 11,
        article_id: 4,
        article_no: 'INV-004',
        batch_id: 42,
        batch_code: 'B-42',
        system_quantity: 7,
        counted_quantity: 7,
      }),
    ]

    const filtered = filterActiveDisplayItems(buildActiveDisplayItems(lines), {
      filterDiscrepancies: true,
      filterUncounted: false,
      getLocalCounted: (line) => {
        if (line.line_id === 10) return 8
        return line.counted_quantity
      },
    })

    expect(filtered).toHaveLength(1)
    expect(filtered[0].kind).toBe('batch-group')
    if (filtered[0].kind !== 'batch-group') {
      throw new Error('Expected batch-group entry')
    }

    expect(filtered[0].visibleChildren.map((line) => line.line_id)).toEqual([10])
  })

  it('treats non-numeric edit values as fallback-to-saved quantities', () => {
    expect(resolveCountedQuantity(4, 1)).toBe(4)
    expect(resolveCountedQuantity('', 7)).toBe(7)
    expect(resolveCountedQuantity(undefined, null)).toBeNull()
  })
})
