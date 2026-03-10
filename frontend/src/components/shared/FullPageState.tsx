import { Button, Center, Loader, Paper, Stack, Text, Title } from '@mantine/core'

interface FullPageStateProps {
  title: string
  message?: string
  actionLabel?: string
  onAction?: () => void
  loading?: boolean
}

export default function FullPageState({
  title,
  message,
  actionLabel,
  onAction,
  loading = false,
}: FullPageStateProps) {
  return (
    <Center
      style={{
        minHeight: '100vh',
        padding: '2rem',
        background:
          'linear-gradient(160deg, rgba(238, 244, 247, 1) 0%, rgba(248, 250, 252, 1) 100%)',
      }}
    >
      <Paper
        withBorder
        radius="lg"
        shadow="md"
        p="xl"
        style={{ width: '100%', maxWidth: 540 }}
      >
        <Stack gap="md" align="flex-start">
          {loading ? <Loader size="sm" /> : null}
          <Title order={2}>{title}</Title>
          {message ? <Text c="dimmed">{message}</Text> : null}
          {!loading && actionLabel && onAction ? (
            <Button onClick={onAction}>{actionLabel}</Button>
          ) : null}
        </Stack>
      </Paper>
    </Center>
  )
}
