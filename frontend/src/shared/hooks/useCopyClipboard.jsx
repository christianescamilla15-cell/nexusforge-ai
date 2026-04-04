import { useState, useCallback } from 'react'

/**
 * Hook for copy-to-clipboard with visual feedback.
 * Returns [copied, copy] where:
 * - copied: boolean (true for 2 seconds after copy)
 * - copy(text): function
 */
export function useCopyClipboard(timeout = 2000) {
  const [copied, setCopied] = useState(false)

  const copy = useCallback(async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), timeout)
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), timeout)
    }
  }, [timeout])

  return [copied, copy]
}

/**
 * Tiny copy button component.
 * Usage: <CopyButton text="value to copy" lang="en" />
 */
export function CopyButton({ text, lang = 'en', size = 'sm' }) {
  const [copied, copy] = useCopyClipboard()

  const styles = size === 'sm'
    ? { padding: '3px 8px', fontSize: 11, borderRadius: 4 }
    : { padding: '6px 12px', fontSize: 12, borderRadius: 6 }

  return (
    <button
      onClick={() => copy(text)}
      title={copied ? (lang === 'es' ? 'Copiado!' : 'Copied!') : (lang === 'es' ? 'Copiar' : 'Copy')}
      style={{
        ...styles,
        border: '1px solid #E5E7EB',
        background: copied ? '#DCFCE7' : '#fff',
        color: copied ? '#166534' : '#6B7280',
        cursor: 'pointer',
        fontWeight: 600,
        transition: 'all 0.15s',
      }}
    >
      {copied ? '\u2713' : '\uD83D\uDCCB'}
    </button>
  )
}
