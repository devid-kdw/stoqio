import { Badge } from '@mantine/core'
import type { ShortageApprovalSummary } from '../../api/inventory'

export function ShortageApprovalBadge({ summary }: { summary: ShortageApprovalSummary | undefined }) {
  if (!summary || summary.total === 0) return null
  if (summary.pending > 0) {
    return <Badge color="yellow">Na čekanju ({summary.pending})</Badge>
  }
  if (summary.rejected === 0) {
    return <Badge color="green">Odobreno</Badge>
  }
  if (summary.approved > 0) {
    return <Badge color="red">Djelomično odbijeno</Badge>
  }
  return <Badge color="red">Odbijeno</Badge>
}
