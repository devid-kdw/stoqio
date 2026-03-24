import type { CSSProperties, ReactNode } from 'react'
import { Box } from '@mantine/core'

interface AuthLayoutProps {
  children: ReactNode
  /** Optional style overrides — useful for page-specific backgrounds or padding. */
  style?: CSSProperties
}

/**
 * Shared full-viewport centering wrapper for auth and setup screens.
 * Scoped to /login and /setup — do not use in the authenticated app shell.
 */
export default function AuthLayout({ children, style }: AuthLayoutProps) {
  return (
    <Box
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...style,
      }}
    >
      {children}
    </Box>
  )
}
