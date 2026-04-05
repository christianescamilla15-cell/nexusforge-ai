/**
 * Centralized query key factory for cache invalidation.
 * Pattern: TanStack Query key factory — hierarchical keys enable
 * targeted or broad invalidation.
 *
 * Usage:
 *   invalidateAll('automations') → refetch everything under ['automations']
 *   invalidateAll('dashboardKpis', 'executions', 'analytics') → cascade
 */

export const keys = {
  dashboardKpis: () => ['dashboard', 'kpis'],
  dashboardRecent: () => ['dashboard', 'recent'],
  automations: () => ['automations'],
  automation: (id) => ['automations', id],
  executions: () => ['executions'],
  execution: (id) => ['executions', id],
  analytics: () => ['analytics'],
  workflows: () => ['workflows'],
  swarms: () => ['swarms'],
}

/**
 * Subscribers: components register their refetch callbacks here.
 * When invalidateAll() is called, all matching subscribers re-fetch.
 *
 * This replaces TanStack Query's queryClient.invalidateQueries for
 * projects using plain fetch + useState.
 */
const subscribers = new Map()
let nextId = 0

/**
 * Subscribe a refetch callback to one or more query keys.
 * Returns an unsubscribe function.
 *
 * @param {string[]} keyNames - key names from `keys` (e.g. 'automations', 'dashboardKpis')
 * @param {Function} refetchFn - function to call when any of those keys are invalidated
 */
export function subscribe(keyNames, refetchFn) {
  const id = nextId++
  subscribers.set(id, { keyNames: new Set(keyNames), refetchFn })
  return () => subscribers.delete(id)
}

/**
 * Invalidate one or more query keys — triggers refetch on all subscribers
 * that registered interest in those keys.
 *
 * @param {...string} keyNames - key names to invalidate
 */
export function invalidateAll(...keyNames) {
  const toInvalidate = new Set(keyNames)
  for (const [, sub] of subscribers) {
    for (const k of sub.keyNames) {
      if (toInvalidate.has(k)) {
        try { sub.refetchFn() } catch (_) { /* non-fatal */ }
        break // don't call the same subscriber twice
      }
    }
  }
}

/**
 * Cascade invalidate after any execution completes.
 * Call this from any component that triggers a run.
 */
export function invalidateAfterExecution() {
  invalidateAll(
    'dashboardKpis',
    'dashboardRecent',
    'automations',
    'executions',
    'analytics',
    'workflows',
  )
}
