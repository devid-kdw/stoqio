import { notifications } from '@mantine/notifications'

const APP_NOTIFICATION_ID = 'app-notification'

interface ToastOptions {
  title: string
  message: string
  color: 'green' | 'red' | 'yellow'
}

const showToast = ({ title, message, color }: ToastOptions) => {
  notifications.clean()
  notifications.show({
    id: APP_NOTIFICATION_ID,
    title,
    message,
    color,
    autoClose: 4000,
  })
}

export const showErrorToast = (message: string) => {
  showToast({
    title: 'Greška',
    message,
    color: 'red',
  })
}

export const showSuccessToast = (message: string) => {
  showToast({
    title: 'Uspjeh',
    message,
    color: 'green',
  })
}

export const showWarningToast = (message: string) => {
  showToast({
    title: 'Upozorenje',
    message,
    color: 'yellow',
  })
}
