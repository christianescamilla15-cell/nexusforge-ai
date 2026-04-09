import { useState, useEffect } from 'react'
import { t } from '../i18n/translations'
import { getApiUrl, fetchAPI } from '../../services/api'
import { useIsMobile } from '../hooks/useIsMobile'
import NotificationBell from './NotificationBell'

function ConnectionDot({ lang }) {
  const [status, setStatus] = useState('unknown') // healthy | degraded | down | unknown
  useEffect(() => {
    const check = () => {
      fetchAPI('/health').then(res => {
        if (res.error) setStatus('down')
        else setStatus(res.data?.status || 'healthy')
      }).catch(() => setStatus('down'))
    }
    check()
    const interval = setInterval(check, 60000)
    return () => clearInterval(interval)
  }, [])
  const color = status === 'healthy' ? '#10B981' : status === 'degraded' ? '#F59E0B' : status === 'down' ? '#EF4444' : '#9CA3AF'
  const label = { healthy: lang === 'es' ? 'Conectado' : 'Connected', degraded: lang === 'es' ? 'Degradado' : 'Degraded', down: lang === 'es' ? 'Desconectado' : 'Disconnected', unknown: '...' }
  return (
    <div title={label[status] || ''} style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'default' }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block', boxShadow: `0 0 4px ${color}40` }} />
    </div>
  )
}

const NAV_ITEMS = [
  { key: 'dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1' },
  { key: 'automations', icon: 'M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z' },
  { key: 'wizard', icon: 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM12 6v6h4.5' },
  { key: 'intelligence', icon: 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z' },
  { key: 'integrations', icon: 'M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244' },
  { key: 'settings', icon: 'M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93s.844.126 1.197-.094l.758-.474a1.12 1.12 0 011.37.15l.773.773a1.12 1.12 0 01.15 1.37l-.474.758c-.22.353-.254.804-.094 1.197.16.396.506.71.93.78l.894.15c.542.09.94.56.94 1.109v1.094c0 .55-.398 1.02-.94 1.11l-.894.149c-.424.07-.764.384-.93.78s-.126.844.094 1.197l.474.758a1.12 1.12 0 01-.15 1.37l-.773.773a1.12 1.12 0 01-1.37.15l-.758-.474c-.353-.22-.804-.254-1.197-.094-.396.16-.71.506-.78.93l-.15.894c-.09.542-.56.94-1.109.94h-1.094c-.55 0-1.02-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93s-.844-.126-1.197.094l-.757.474a1.12 1.12 0 01-1.37-.15l-.774-.773a1.12 1.12 0 01-.15-1.37l.474-.758c.22-.353.254-.804.094-1.197a2.25 2.25 0 00-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.764-.384.93-.78s.126-.844-.094-1.197l-.474-.758a1.12 1.12 0 01.15-1.37l.773-.774a1.12 1.12 0 011.37-.15l.758.474c.353.22.804.254 1.197.094.396-.16.71-.506.78-.93l.15-.894zM15 12a3 3 0 11-6 0 3 3 0 016 0z' },
]

const ADVANCED_ITEMS = [
  { key: 'workflows', icon: 'M4 6h16M4 12h8m-8 6h16' },
  { key: 'executions', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { key: 'agents', icon: 'M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 3.71a.75.75 0 01-.625.334H8.095a.75.75 0 01-.625-.334L5 14.5m14 0H5' },
  { key: 'swarms', icon: 'M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z' },
  { key: 'connectors', icon: 'M11.42 15.17l-3.12-3.12a4 4 0 010-5.66l3.12-3.12a4 4 0 015.66 0l3.12 3.12a4 4 0 010 5.66l-3.12 3.12a4 4 0 01-5.66 0z' },
  { key: 'analyze', icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z' },
  { key: 'audit', icon: 'M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z' },
  { key: 'metrics', icon: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z' },
  { key: 'status', icon: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
  { key: 'docs', icon: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25' },
]

const sidebarWidth = 240
const collapsedWidth = 64
const topBarHeight = 56

export default function Layout({ currentPage, onNavigate, children, lang, toggleLang, theme = 'light', setTheme, user, onLogout }) {
  const isDark = theme === 'dark'
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const isMobile = useIsMobile()
  const [advancedOpen, setAdvancedOpen] = useState(() => {
    try { return localStorage.getItem('nxf-advanced-open') === '1' } catch { return false }
  })

  const toggleAdvanced = () => {
    setAdvancedOpen(prev => {
      const next = !prev
      try { localStorage.setItem('nxf-advanced-open', next ? '1' : '0') } catch { /* */ }
      return next
    })
  }

  // If currently on an advanced page, ensure advanced section is open
  useEffect(() => {
    const advancedKeys = ADVANCED_ITEMS.map(i => i.key)
    if (advancedKeys.includes(currentPage) && !advancedOpen) {
      setAdvancedOpen(true)
      try { localStorage.setItem('nxf-advanced-open', '1') } catch { /* */ }
    }
  }, [currentPage, advancedOpen])

  const w = isMobile ? sidebarWidth : (collapsed ? collapsedWidth : sidebarWidth)

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: isDark ? '#0F1117' : '#F9FAFB' }}>
      {/* Mobile overlay — semi-transparent, closes sidebar on tap */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          aria-label="Close sidebar overlay"
          style={{
            position: 'fixed', inset: 0,
            background: isDark ? 'rgba(0,0,0,0.6)' : 'rgba(0,0,0,0.3)',
            zIndex: 40,
            backdropFilter: 'blur(2px)', WebkitBackdropFilter: 'blur(2px)',
          }}
        />
      )}

      {/* Sidebar */}
      <aside
        className="nxf-sidebar"
        style={{
          width: isMobile ? sidebarWidth : w,
          minWidth: isMobile ? sidebarWidth : w,
          height: '100vh',
          position: 'fixed',
          top: 0,
          left: isMobile ? (mobileOpen ? 0 : -sidebarWidth) : 0,
          background: isDark ? '#0F1117' : '#FFFFFF',
          borderRight: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`,
          display: 'flex',
          flexDirection: 'column',
          transition: isMobile ? 'left 0.3s ease' : 'width 0.2s ease',
          zIndex: 50,
          overflow: 'hidden',
        }}
      >
        {/* Logo + close button on mobile */}
        <div style={{
          height: topBarHeight, display: 'flex', alignItems: 'center',
          padding: '0 16px', gap: 10, borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`,
          flexShrink: 0, justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: isDark ? '#6366F1' : '#2563EB',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: 14, color: '#fff', flexShrink: 0,
          }}>
            NF
          </div>
          {(!collapsed || isMobile) && (
            <span style={{ fontWeight: 700, fontSize: 16, color: isDark ? '#E5E7EB' : '#111827', whiteSpace: 'nowrap' }}>
              NexusForge
            </span>
          )}
          </div>
          {/* Close button — mobile only */}
          {isMobile && mobileOpen && (
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
              style={{
                background: 'none', border: 'none', padding: 4, cursor: 'pointer',
                color: isDark ? '#9CA3AF' : '#6B7280', fontSize: 20,
              }}
            >✕</button>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto' }}>
          {NAV_ITEMS.map((item) => {
            const active = currentPage === item.key
            const showLabel = !collapsed || isMobile
            return (
              <button
                key={item.key}
                data-nav={item.key}
                onClick={() => { onNavigate(item.key); setMobileOpen(false) }}
                aria-label={t(item.key, lang)}
                title={(!showLabel) ? t(item.key, lang) : undefined}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: showLabel ? '10px 12px' : '10px 0',
                  justifyContent: showLabel ? 'flex-start' : 'center',
                  borderRadius: 8, border: 'none', width: '100%',
                  background: active ? (isDark ? 'rgba(99,102,241,0.15)' : 'rgba(37,99,235,0.08)') : 'transparent',
                  color: active ? (isDark ? '#818CF8' : '#2563EB') : (isDark ? '#9CA3AF' : '#4B5563'),
                  fontSize: 14, fontWeight: active ? 600 : 400,
                  transition: 'all 0.15s', cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => {
                  if (!active) e.currentTarget.style.background = isDark ? 'rgba(255,255,255,0.05)' : '#F3F4F6'
                }}
                onMouseLeave={(e) => {
                  if (!active) e.currentTarget.style.background = 'transparent'
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
                  style={{ flexShrink: 0 }}>
                  <path d={item.icon} />
                </svg>
                {showLabel && <span>{t(item.key, lang)}</span>}
              </button>
            )
          })}

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Advanced section - collapsible */}
          <div style={{ borderTop: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6'}`, paddingTop: 8, marginTop: 4 }}>
            <button
              onClick={toggleAdvanced}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: (!collapsed || isMobile) ? '8px 12px' : '8px 0',
                justifyContent: (!collapsed || isMobile) ? 'flex-start' : 'center',
                borderRadius: 8, border: 'none', width: '100%',
                background: 'transparent',
                color: isDark ? '#6B7280' : '#9CA3AF',
                fontSize: 11, fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '0.05em',
                cursor: 'pointer', transition: 'all 0.15s',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => e.currentTarget.style.color = isDark ? '#9CA3AF' : '#6B7280'}
              onMouseLeave={(e) => e.currentTarget.style.color = isDark ? '#6B7280' : '#9CA3AF'}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                style={{ flexShrink: 0, transform: advancedOpen ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
                <path d="M9 5l7 7-7 7" />
              </svg>
              {(!collapsed || isMobile) && <span>{lang === 'es' ? 'Avanzado' : 'Advanced'}</span>}
            </button>

            {advancedOpen && ADVANCED_ITEMS.map((item) => {
              const active = currentPage === item.key
              const showLabel = !collapsed || isMobile
              return (
                <button
                  key={item.key}
                  data-nav={item.key}
                  onClick={() => { onNavigate(item.key); setMobileOpen(false) }}
                  aria-label={t(item.key, lang)}
                  title={(!showLabel) ? t(item.key, lang) : undefined}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: showLabel ? '10px 12px 10px 20px' : '10px 0',
                    justifyContent: showLabel ? 'flex-start' : 'center',
                    borderRadius: 8, border: 'none', width: '100%',
                    background: active ? (isDark ? 'rgba(99,102,241,0.15)' : 'rgba(37,99,235,0.08)') : 'transparent',
                    color: active ? (isDark ? '#818CF8' : '#2563EB') : (isDark ? '#9CA3AF' : '#4B5563'),
                    fontSize: 13, fontWeight: active ? 600 : 400,
                    transition: 'all 0.15s', cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                  onMouseEnter={(e) => {
                    if (!active) e.currentTarget.style.background = isDark ? 'rgba(255,255,255,0.05)' : '#F3F4F6'
                  }}
                  onMouseLeave={(e) => {
                    if (!active) e.currentTarget.style.background = 'transparent'
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
                    style={{ flexShrink: 0 }}>
                    <path d={item.icon} />
                  </svg>
                  {showLabel && <span>{t(item.key, lang)}</span>}
                </button>
              )
            })}
          </div>
        </nav>

        {/* Keyboard shortcut hint */}
        {!collapsed && !isMobile && (
          <div style={{
            padding: '6px 16px', fontSize: 11, color: '#9CA3AF',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <kbd style={{
              padding: '1px 5px', borderRadius: 3, background: isDark ? '#2D2E42' : '#F3F4F6',
              border: `1px solid ${isDark ? '#3D3E52' : '#E5E7EB'}`, fontSize: 10,
            }}>{navigator.platform.includes('Mac') ? '\u2318' : 'Ctrl'}</kbd>
            <kbd style={{
              padding: '1px 5px', borderRadius: 3, background: isDark ? '#2D2E42' : '#F3F4F6',
              border: `1px solid ${isDark ? '#3D3E52' : '#E5E7EB'}`, fontSize: 10,
            }}>K</kbd>
            <span>{lang === 'es' ? 'Buscar' : 'Search'}</span>
          </div>
        )}

        {/* Collapse toggle -- hidden on mobile */}
        {!isMobile && (
          <div style={{
            padding: 8, borderTop: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`, flexShrink: 0,
          }}>
            <button
              onClick={() => setCollapsed((c) => !c)}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: '100%', padding: 10, borderRadius: 8, border: 'none',
                background: 'transparent', color: '#9CA3AF', cursor: 'pointer',
                transition: 'color 0.15s',
              }}
              onMouseEnter={(e) => e.currentTarget.style.color = isDark ? '#E5E7EB' : '#111827'}
              onMouseLeave={(e) => e.currentTarget.style.color = '#9CA3AF'}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                style={{ transform: collapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
                <path d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          </div>
        )}
      </aside>

      {/* Main content */}
      <div className="nxf-main-content" style={{
        marginLeft: isMobile ? 0 : w,
        flex: 1,
        transition: 'margin-left 0.2s ease',
        width: isMobile ? '100%' : undefined,
        overflowX: 'hidden',
        maxWidth: isMobile ? '100%' : `calc(100vw - ${w}px)`,
      }}>
        {/* Top bar */}
        <header style={{
          height: topBarHeight, display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', padding: isMobile ? '0 12px' : '0 24px',
          borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`,
          background: isDark ? '#0F1117' : '#FFFFFF', position: 'sticky', top: 0, zIndex: 30,
          gap: 8,
        }}>
          {/* Mobile toggle */}
          {isMobile && (
            <button
              onClick={() => setMobileOpen((o) => !o)}
              aria-label="Open menu"
              style={{
                background: 'none', border: 'none',
                color: isDark ? '#9CA3AF' : '#4B5563', padding: 4, flexShrink: 0,
              }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}

          {/* Search -- hidden on very small screens */}
          <div className="nxf-search" style={{
            position: 'relative', maxWidth: 400, flex: 1,
            display: isMobile ? 'none' : 'block',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round"
              style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }}>
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              placeholder={t('searchWorkflowsAgents', lang)}
              aria-label={t('search', lang)}
              style={{
                width: '100%', padding: '8px 12px 8px 36px', borderRadius: 8,
                border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'}`, background: isDark ? '#1A1B2E' : '#F9FAFB',
                color: isDark ? '#E5E7EB' : '#111827', fontSize: 14, outline: 'none',
                transition: 'border-color 0.15s',
              }}
              onFocus={(e) => e.target.style.borderColor = isDark ? '#6366F1' : '#2563EB'}
              onBlur={(e) => e.target.style.borderColor = isDark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'}
            />
          </div>

          {/* Right side: lang toggle + avatar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>

            {/* Theme toggle */}
            <button
              onClick={() => setTheme && setTheme(isDark ? 'light' : 'dark')}
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              title={isDark ? 'Light mode' : 'Dark mode'}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 18, padding: 4, lineHeight: 1,
                color: isDark ? '#F59E0B' : '#6B7280',
              }}
            >
              {isDark ? '\u2600\uFE0F' : '\uD83C\uDF19'}
            </button>

            {/* Language toggle */}
            <div style={{
              display: 'flex', borderRadius: 6, overflow: 'hidden',
              border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`,
            }}>
              {['en', 'es'].map((code) => (
                <button
                  key={code}
                  onClick={() => toggleLang()}
                  aria-label={`Switch language to ${code.toUpperCase()}`}
                  style={{
                    padding: '5px 10px', border: 'none', fontSize: 12, fontWeight: 600,
                    cursor: 'pointer', transition: 'all 0.15s',
                    background: lang === code ? (isDark ? 'rgba(99,102,241,0.15)' : 'rgba(37,99,235,0.08)') : (isDark ? '#1A1B2E' : '#FFFFFF'),
                    color: lang === code ? (isDark ? '#818CF8' : '#2563EB') : '#9CA3AF',
                  }}
                >
                  {code.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Connection status dot */}
            <ConnectionDot lang={lang} />

            {/* Notification bell */}
            <NotificationBell lang={lang} isDark={isDark} />

            {/* User avatar + dropdown */}
            <div style={{ position: 'relative' }}
              onMouseEnter={() => !isMobile && setShowUserMenu(true)}
              onMouseLeave={() => !isMobile && setShowUserMenu(false)}
              onClick={() => isMobile && setShowUserMenu(prev => !prev)}
            >
              <div style={{
                width: 34, height: 34, borderRadius: '50%',
                background: '#2563EB',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontWeight: 600, fontSize: 13, color: '#fff', flexShrink: 0,
                cursor: 'pointer',
              }}>
                {user?.name ? user.name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase() : 'U'}
              </div>

              {showUserMenu && (
                <div style={{
                  position: 'absolute', right: 0, top: 40, width: 260,
                  background: isDark ? '#1A1D23' : '#FFFFFF',
                  border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'}`,
                  borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
                  padding: 8, zIndex: 100,
                }}>
                  {/* User info */}
                  <div style={{ padding: '12px 12px 8px', borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6'}` }}>
                    <div style={{ fontWeight: 600, fontSize: 14, color: isDark ? '#F3F4F6' : '#111827' }}>
                      {user?.name || 'User'}
                    </div>
                    <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 2 }}>{user?.email || ''}</div>
                    <div style={{
                      display: 'inline-block', marginTop: 6, padding: '2px 8px',
                      borderRadius: 4, fontSize: 11, fontWeight: 600,
                      background: user?.plan === 'pro' ? 'rgba(37,99,235,0.1)' : user?.plan === 'team' ? 'rgba(124,58,237,0.1)' : 'rgba(107,114,128,0.1)',
                      color: user?.plan === 'pro' ? '#2563EB' : user?.plan === 'team' ? '#7C3AED' : '#6B7280',
                    }}>
                      {(user?.plan || 'free').toUpperCase()} PLAN
                    </div>
                  </div>

                  {/* Menu items */}
                  {[
                    { label: lang === 'es' ? 'Mi Perfil' : 'My Profile', icon: '👤', action: () => onNavigate('settings') },
                    { label: lang === 'es' ? 'Facturacion' : 'Billing', icon: '💳', action: () => onNavigate('settings') },
                    { label: lang === 'es' ? 'Uso de API' : 'API Usage', icon: '📊', action: () => onNavigate('cost-metrics') },
                    { label: lang === 'es' ? 'Configuracion' : 'Settings', icon: '⚙️', action: () => onNavigate('settings') },
                  ].map((item, i) => (
                    <div key={i}
                      onClick={() => { item.action(); setShowUserMenu(false) }}
                      style={{
                        padding: '8px 12px', borderRadius: 8, cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: 10,
                        fontSize: 13, color: isDark ? '#D1D5DB' : '#374151',
                        transition: 'background 0.15s',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = isDark ? 'rgba(255,255,255,0.05)' : '#F9FAFB'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <span style={{ fontSize: 15 }}>{item.icon}</span>
                      {item.label}
                    </div>
                  ))}

                  {/* Divider + Logout */}
                  <div style={{ borderTop: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6'}`, marginTop: 4, paddingTop: 4 }}>
                    <div
                      onClick={() => { if (onLogout) onLogout(); setShowUserMenu(false) }}
                      style={{
                        padding: '8px 12px', borderRadius: 8, cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: 10,
                        fontSize: 13, color: '#EF4444',
                        transition: 'background 0.15s',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.06)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <span style={{ fontSize: 15 }}>🚪</span>
                      {lang === 'es' ? 'Cerrar Sesion' : 'Sign Out'}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{
          padding: isMobile ? 12 : 24,
          minHeight: isMobile ? 'auto' : `calc(100vh - ${topBarHeight}px)`,
        }}>
          {children}

          {/* Footer stats */}
          {!isMobile && (
            <footer style={{
              padding: '8px 24px', borderTop: `1px solid ${isDark ? 'rgba(255,255,255,0.04)' : '#F3F4F6'}`,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              fontSize: 11, color: isDark ? '#4B5563' : '#D1D5DB',
            }}>
              <span>NexusForge AI v2.5</span>
              <span>24 {t('agents', lang)} &middot; 6 {t('swarms', lang) || 'topologies'} &middot; 8 {lang === 'es' ? 'integraciones' : 'integrations'}</span>
            </footer>
          )}
        </main>
      </div>

      {/* Mobile bottom navigation */}
      <nav className="nxf-mobile-bottom-nav" style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: isDark ? '#0F1117' : '#FFFFFF',
        borderTop: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : '#E5E7EB'}`,
        padding: '6px 0 env(safe-area-inset-bottom, 6px)',
        zIndex: 100,
        justifyContent: 'space-around',
        alignItems: 'center',
        boxShadow: isDark ? '0 -2px 8px rgba(0,0,0,0.3)' : '0 -2px 8px rgba(0,0,0,0.04)',
      }}>
        {[
          { key: 'dashboard', label: t('dashboard', lang), icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1' },
          { key: 'automations', label: t('automations', lang) || 'Automations', icon: 'M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z' },
          { key: 'wizard', label: 'AI Wizard', icon: 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM12 6v6h4.5' },
          { key: 'settings', label: t('settings', lang), icon: 'M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93s.844.126 1.197-.094l.758-.474a1.12 1.12 0 011.37.15l.773.773a1.12 1.12 0 01.15 1.37l-.474.758c-.22.353-.254.804-.094 1.197.16.396.506.71.93.78l.894.15c.542.09.94.56.94 1.109v1.094c0 .55-.398 1.02-.94 1.11l-.894.149c-.424.07-.764.384-.93.78s-.126.844.094 1.197l.474.758a1.12 1.12 0 01-.15 1.37l-.773.773a1.12 1.12 0 01-1.37.15l-.758-.474c-.353-.22-.804-.254-1.197-.094-.396.16-.71.506-.78.93l-.15.894c-.09.542-.56.94-1.109.94h-1.094c-.55 0-1.02-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93s-.844-.126-1.197.094l-.757.474a1.12 1.12 0 01-1.37-.15l-.774-.773a1.12 1.12 0 01-.15-1.37l.474-.758c.22-.353.254-.804.094-1.197a2.25 2.25 0 00-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.764-.384.93-.78s.126-.844-.094-1.197l-.474-.758a1.12 1.12 0 01.15-1.37l.773-.774a1.12 1.12 0 011.37-.15l.758.474c.353.22.804.254 1.197.094.396-.16.71-.506.78-.93l.15-.894zM15 12a3 3 0 11-6 0 3 3 0 016 0z' },
        ].map((item) => {
          const active = currentPage === item.key
          return (
            <button
              key={item.key}
              onClick={() => { onNavigate(item.key); setMobileOpen(false) }}
              aria-label={item.label}
              style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
                background: 'none', border: 'none', padding: '8px 12px',
                color: active ? (isDark ? '#818CF8' : '#2563EB') : '#9CA3AF',
                fontSize: 12, fontWeight: active ? 600 : 400,
                cursor: 'pointer', minHeight: 44,
              }}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d={item.icon} />
              </svg>
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>
    </div>
  )
}
