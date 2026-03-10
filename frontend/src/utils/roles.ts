export const RoleHomeRoute: Record<string, string> = {
  ADMIN: '/approvals',
  MANAGER: '/warehouse',
  WAREHOUSE_STAFF: '/identifier',
  VIEWER: '/identifier',
  OPERATOR: '/drafts',
}

export const getHomeRouteForRole = (role?: string | null): string => {
  if (!role) return '/login'
  return RoleHomeRoute[role] || '/login'
}
