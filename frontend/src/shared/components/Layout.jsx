import { useState, useEffect } from 'react'
import { t } from '../i18n/translations'

const NAV_ITEMS = [
  { key: 'dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1' },
  { key: 'workflows', icon: 'M4 6h16M4 12h8m-8 6h16' },
  { key: 'executions', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { key: 'agents', icon: 'M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 3.71a.75.75 0 01-.625.334H8.095a.75.75 0 01-.625-.334L5 14.5m14 0H5' },
  { key: 'memory', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
  { key: 'swarms', icon: 'M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z' },
  { key: 'healing', icon: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z' },
  { key: 'documents', icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z' },
  { key: 'settings', icon: 'M10.343 3.94c.09-.542.56-.94 1.11-.94h1.093c.55 0 1.02.398 1.11.94l.149.894c.07.424.384.764.78.93s.844.126 1.197-.094l.758-.474a1.12 1.12 0 011.37.15l.773.773a1.12 1.12 0 01.15 1.37l-.474.758c-.22.353-.254.804-.094 1.197.16.396.506.71.93.78l.894.15c.542.09.94.56.94 1.109v1.094c0 .55-.398 1.02-.94 1.11l-.894.149c-.424.07-.764.384-.93.78s-.126.844.094 1.197l.474.758a1.12 1.12 0 01-.15 1.37l-.773.773a1.12 1.12 0 01-1.37.15l-.758-.474c-.353-.22-.804-.254-1.197-.094-.396.16-.71.506-.78.93l-.15.894c-.09.542-.56.94-1.109.94h-1.094c-.55 0-1.02-.398-1.11-.94l-.148-.894c-.071-.424-.384-.764-.781-.93s-.844-.126-1.197.094l-.757.474a1.12 1.12 0 01-1.37-.15l-.774-.773a1.12 1.12 0 01-.15-1.37l.474-.758c.22-.353.254-.804.094-1.197a2.25 2.25 0 00-.93-.78l-.894-.15c-.542-.09-.94-.56-.94-1.109v-1.094c0-.55.398-1.02.94-1.11l.894-.149c.424-.07.764-.384.93-.78s.126-.844-.094-1.197l-.474-.758a1.12 1.12 0 01.15-1.37l.773-.774a1.12 1.12 0 011.37-.15l.758.474c.353.22.804.254 1.197.094.396-.16.71-.506.78-.93l.15-.894zM15 12a3 3 0 11-6 0 3 3 0 016 0z' },
]

const sidebarWidth = 240
const collapsedWidth = 64
const topBarHeight = 56

export default function Layout({ currentPage, onNavigate, children, lang, toggleLang }) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const w = isMobile ? sidebarWidth : (collapsed ? collapsedWidth : sidebarWidth)

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          aria-label="Close sidebar overlay"
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            zIndex: 40,
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
          background: '#0F1117',
          borderRight: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          flexDirection: 'column',
          transition: isMobile ? 'left 0.3s ease' : 'width 0.2s ease',
          zIndex: 50,
          overflow: 'hidden',
        }}
      >
        {/* Logo */}
        <div style={{
          height: topBarHeight, display: 'flex', alignItems: 'center',
          padding: '0 16px', gap: 10, borderBottom: '1px solid rgba(255,255,255,0.06)',
          flexShrink: 0,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: 14, color: '#fff', flexShrink: 0,
          }}>
            NF
          </div>
          {(!collapsed || isMobile) && (
            <span style={{ fontWeight: 700, fontSize: 16, color: '#E5E7EB', whiteSpace: 'nowrap' }}>
              NexusForge
            </span>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {NAV_ITEMS.map((item) => {
            const active = currentPage === item.key
            const showLabel = !collapsed || isMobile
            return (
              <button
                key={item.key}
                onClick={() => { onNavigate(item.key); setMobileOpen(false) }}
                aria-label={t(item.key, lang)}
                title={(!showLabel) ? t(item.key, lang) : undefined}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: showLabel ? '10px 12px' : '10px 0',
                  justifyContent: showLabel ? 'flex-start' : 'center',
                  borderRadius: 8, border: 'none', width: '100%',
                  background: active ? 'rgba(99,102,241,0.12)' : 'transparent',
                  color: active ? '#818CF8' : '#9CA3AF',
                  fontSize: 14, fontWeight: active ? 500 : 400,
                  transition: 'all 0.15s', cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => {
                  if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
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
        </nav>

        {/* Collapse toggle — hidden on mobile */}
        {!isMobile && (
          <div style={{
            padding: 8, borderTop: '1px solid rgba(255,255,255,0.06)', flexShrink: 0,
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
              onMouseEnter={(e) => e.currentTarget.style.color = '#E5E7EB'}
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
      <div style={{
        marginLeft: isMobile ? 0 : w,
        flex: 1,
        transition: 'margin-left 0.2s ease',
        width: isMobile ? '100%' : undefined,
      }}>
        {/* Top bar */}
        <header style={{
          height: topBarHeight, display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', padding: isMobile ? '0 12px' : '0 24px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          background: '#0A0B0F', position: 'sticky', top: 0, zIndex: 30,
          gap: 8,
        }}>
          {/* Mobile toggle */}
          {isMobile && (
            <button
              onClick={() => setMobileOpen((o) => !o)}
              aria-label="Open menu"
              style={{
                background: 'none', border: 'none',
                color: '#9CA3AF', padding: 4, flexShrink: 0,
              }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}

          {/* Search — hidden on very small screens */}
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
                border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)',
                color: '#E5E7EB', fontSize: 14, outline: 'none',
              }}
              onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
              onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
            />
          </div>

          {/* Right side: lang toggle + avatar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            {/* Language toggle */}
            <div style={{
              display: 'flex', borderRadius: 6, overflow: 'hidden',
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              {['en', 'es'].map((code) => (
                <button
                  key={code}
                  onClick={() => toggleLang()}
                  aria-label={`Switch language to ${code.toUpperCase()}`}
                  style={{
                    padding: '5px 10px', border: 'none', fontSize: 12, fontWeight: 600,
                    cursor: 'pointer', transition: 'all 0.15s',
                    background: lang === code ? 'rgba(99,102,241,0.2)' : 'transparent',
                    color: lang === code ? '#818CF8' : '#6B7280',
                  }}
                >
                  {code.toUpperCase()}
                </button>
              ))}
            </div>

            {/* User avatar */}
            <div style={{
              width: 34, height: 34, borderRadius: '50%',
              background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 600, fontSize: 13, color: '#fff', flexShrink: 0,
            }}
              aria-label="User profile"
            >
              CH
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{
          padding: isMobile ? 12 : 24,
          minHeight: `calc(100vh - ${topBarHeight}px)`,
        }}>
          {children}
        </main>
      </div>
    </div>
  )
}
