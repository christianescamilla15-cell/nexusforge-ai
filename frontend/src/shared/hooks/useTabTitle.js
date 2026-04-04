import { useEffect } from 'react'

const BASE_TITLE = 'NexusForge AI'

/**
 * Updates browser tab title with unread notification count.
 * Listens for custom 'nxf-notification' events from NotificationBell.
 */
export function useTabTitle() {
  useEffect(() => {
    const update = () => {
      try {
        const notifs = JSON.parse(localStorage.getItem('nxf_notifications') || '[]')
        const unread = notifs.filter(n => !n.read).length
        document.title = unread > 0 ? `(${unread}) ${BASE_TITLE}` : BASE_TITLE
      } catch {
        document.title = BASE_TITLE
      }
    }

    update()

    // Listen for notification changes
    window.addEventListener('nxf-notification', update)
    window.addEventListener('storage', update)

    // Poll every 10s as fallback
    const interval = setInterval(update, 10000)

    return () => {
      window.removeEventListener('nxf-notification', update)
      window.removeEventListener('storage', update)
      clearInterval(interval)
    }
  }, [])
}
