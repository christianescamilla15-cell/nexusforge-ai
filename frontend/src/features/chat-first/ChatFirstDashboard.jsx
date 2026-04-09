import { useState } from 'react'
import { PreviewEventProvider } from './hooks/usePreviewEvents'
import ChatPanel from './ChatPanel'
import PreviewPanel from './PreviewPanel'
import { useIsMobile } from '../../shared/hooks/useIsMobile'

/**
 * Chat-first dashboard — the new default view at "/".
 * Left: Conversational AI assistant (60%)
 * Right: Live preview of what's being built (40%)
 * Mobile: Tab-based toggle between chat and preview.
 */
export default function ChatFirstDashboard({ lang = 'es', onNavigate }) {
  const isMobile = useIsMobile(900)
  const [activeTab, setActiveTab] = useState('chat') // chat | preview

  return (
    <PreviewEventProvider>
      {/* Hide floating chat bubble on this page */}
      <style>{`
        .nf-chat-fab, [class*="chat-fab"], [class*="ChatAssistant"] > button:last-child {
          display: none !important;
        }
      `}</style>

      <div data-page="chat-first" style={{
        height: 'calc(100vh - 56px)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
        margin: isMobile ? '-12px' : '-24px',
        width: isMobile ? 'calc(100% + 24px)' : 'calc(100% + 48px)',
      }}>
        {/* Mobile tab switcher */}
        {isMobile && (
          <div style={{
            display: 'flex', borderBottom: '1px solid #E5E7EB',
            background: '#fff',
          }}>
            {[
              { key: 'chat', label: lang === 'es' ? '\u2728 Chat' : '\u2728 Chat' },
              { key: 'preview', label: lang === 'es' ? '\uD83D\uDCCA Vista previa' : '\uD83D\uDCCA Preview' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  flex: 1, padding: '12px 0', border: 'none',
                  background: activeTab === tab.key ? '#EEF2FF' : '#fff',
                  borderBottom: activeTab === tab.key ? '2px solid #6366F1' : '2px solid transparent',
                  color: activeTab === tab.key ? '#6366F1' : '#9CA3AF',
                  fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}

        {/* Panels */}
        <div style={{
          flex: 1, display: 'flex', overflow: 'hidden',
        }}>
          {/* Chat panel */}
          <div style={{
            flex: isMobile ? 1 : 6,
            display: isMobile && activeTab !== 'chat' ? 'none' : 'flex',
            flexDirection: 'column', minWidth: 0,
            overflow: 'hidden',
          }}>
            <ChatPanel lang={lang} />
          </div>

          {/* Preview panel */}
          <div style={{
            flex: isMobile ? 1 : 4,
            display: isMobile && activeTab !== 'preview' ? 'none' : 'flex',
            flexDirection: 'column', minWidth: 0,
            overflow: 'hidden',
          }}>
            <PreviewPanel lang={lang} />
          </div>
        </div>
      </div>
    </PreviewEventProvider>
  )
}
