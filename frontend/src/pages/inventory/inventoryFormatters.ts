import { formatNumber } from '../../utils/locale'

export const HISTORY_PAGE_SIZE = 50

export function fmtQty(n: number, decimalDisplay: boolean): string {
  return formatNumber(n, decimalDisplay ? 2 : 0)
}

export function fmtDiff(n: number, decimalDisplay: boolean): string {
  const sign = n > 0 ? '+' : ''
  return `${sign}${fmtQty(n, decimalDisplay)}`
}
