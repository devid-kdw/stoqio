import { Badge } from '@mantine/core'

export function ResolutionBadge({ resolution }: { resolution: string | null }) {
  if (!resolution) return <span>—</span>
  const map: Record<string, { label: string; color: string }> = {
    NO_CHANGE: { label: 'Bez promjena', color: 'green' },
    SURPLUS_ADDED: { label: 'Višak dodan', color: 'blue' },
    SHORTAGE_DRAFT_CREATED: { label: 'Manjak (nacrt)', color: 'yellow' },
    OPENING_STOCK_SET: { label: 'Početno stanje', color: 'violet' },
  }
  const entry = map[resolution]
  if (!entry) return <Badge>{resolution}</Badge>
  return <Badge color={entry.color}>{entry.label}</Badge>
}
