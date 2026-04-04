/**
 * Format large numbers with K/M suffixes.
 * formatNumber(1234) → "1.2K"
 * formatNumber(1234567) → "1.2M"
 * formatNumber(42) → "42"
 */
export function formatNumber(num) {
  if (typeof num !== 'number' || isNaN(num)) return String(num)
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 10000) return `${(num / 1000).toFixed(0)}K`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toLocaleString()
}

/**
 * Format currency with 2-4 decimal places.
 * formatCost(0.0023) → "$0.0023"
 * formatCost(1.5) → "$1.50"
 */
export function formatCost(num) {
  if (typeof num !== 'number') return '$0.00'
  if (num < 0.01) return `$${num.toFixed(4)}`
  return `$${num.toFixed(2)}`
}

/**
 * Format duration in ms to human-readable.
 * formatDuration(1500) → "1.5s"
 * formatDuration(65000) → "1m 5s"
 */
export function formatDuration(ms) {
  if (typeof ms !== 'number' || ms <= 0) return '0s'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.round((ms % 60000) / 1000)
  return `${mins}m ${secs}s`
}
