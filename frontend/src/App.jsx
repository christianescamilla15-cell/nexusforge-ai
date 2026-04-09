import { useState, useEffect, useCallback, useMemo, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams, useLocation } from 'react-router-dom'
import ErrorBoundary from './shared/components/ErrorBoundary'
import WhatsNew from './shared/components/WhatsNew'
import KeyboardShortcuts from './shared/components/KeyboardShortcuts'
import AuthPage from './features/auth/AuthPage'
import Layout from './shared/components/Layout'
import OnboardingTour from './shared/components/OnboardingTour'
import ToastContainer from './shared/components/Toast'
import { useLanguage } from './shared/hooks/useLanguage'
import { useToastState, ToastContext } from './shared/hooks/useToast'
import Skeleton from './shared/components/Skeleton'

// Eager: Chat-first dashboard (first page users see) + Chat (always visible)
import ChatFirstDashboard from './features/chat-first/ChatFirstDashboard'
import ChatAssistant from './features/chat/ChatAssistant'
import CommandPalette from './shared/components/CommandPalette'

// Lazy: all other pages (loaded on navigation)
const AutomationsPage = lazy(() => import('./features/automations/AutomationsPage'))
const SmartDashboardPage = lazy(() => import('./pages/SmartDashboardPage'))
const WizardPage = lazy(() => import('./features/wizard/WizardPage'))
const WorkflowListPage = lazy(() => import('./features/workflows/WorkflowListPage'))
const WorkflowDetailPage = lazy(() => import('./features/workflows/WorkflowDetailPage'))
const WorkflowBuilderPage = lazy(() => import('./features/workflows/WorkflowBuilderPage'))
const ExecutionListPage = lazy(() => import('./features/executions/ExecutionListPage'))
const ExecutionDetailPage = lazy(() => import('./features/executions/ExecutionDetailPage'))
const AgentListPage = lazy(() => import('./features/agents/AgentListPage'))
const SwarmListPage = lazy(() => import('./features/swarms/SwarmListPage'))
const IntegrationManagerPage = lazy(() => import('./features/integrations/IntegrationManagerPage'))
const SettingsPage = lazy(() => import('./features/settings/SettingsPage'))
const IntelligenceHubPage = lazy(() => import('./features/intelligence/IntelligenceHubPage'))
const ConnectorHubPage = lazy(() => import('./features/connectors/ConnectorHubPage'))
const AuditLog = lazy(() => import('./features/audit/AuditLog'))
const CostTokenDashboard = lazy(() => import('./features/metrics/CostTokenDashboard'))
const StatusPage = lazy(() => import('./features/status/StatusPage'))
const AnalyzePage = lazy(() => import('./features/analyze/AnalyzePage'))
const ApiDocsPage = lazy(() => import('./features/docs/ApiDocsPage'))
const RefactorDashboard = lazy(() => import('./features/refactor/RefactorDashboard'))
const ExecutiveDashboard = lazy(() => import('./features/refactor/ExecutiveDashboard'))
const AdminDashboard = lazy(() => import('./features/admin/AdminDashboard'))

import TopLoadingBar from './shared/components/TopLoadingBar'
import OfflineIndicator from './shared/components/OfflineIndicator'
import SessionExpiry from './shared/components/SessionExpiry'
import FeedbackWidget from './shared/components/FeedbackWidget'
import NotFoundPage from './shared/components/NotFoundPage'

// Suspense fallback
const PageLoader = () => <div style={{ padding: 40 }}><Skeleton.Grid count={3} /></div>

// Map old page keys → URL paths (backwards compat for onNavigate callbacks)
const PAGE_TO_PATH = {
  dashboard: '/',
  automations: '/automations',
  wizard: '/wizard',
  integrations: '/integrations',
  settings: '/settings',
  workflows: '/workflows',
  executions: '/executions',
  agents: '/agents',
  swarms: '/swarms',
  intelligence: '/intelligence',
  connectors: '/connectors',
  audit: '/audit',
  analyze: '/analyze',
  metrics: '/metrics',
  status: '/status',
  docs: '/docs',
  'workflow-builder': '/workflows/builder',
}

const PATH_TO_PAGE = Object.fromEntries(
  Object.entries(PAGE_TO_PATH).map(([k, v]) => [v, k])
)

function AppRoutes() {
  const routerNavigate = useNavigate()
  const location = useLocation()
  const { lang, setLang, toggle: toggleLang } = useLanguage()
  const [theme, setTheme] = useState(() => localStorage.getItem('nexusforge_theme') || 'light')

  // Tab title with notification count
  useEffect(() => {
    const update = () => {
      try {
        const notifs = JSON.parse(localStorage.getItem('nxf_notifications') || '[]')
        const unread = notifs.filter(n => !n.read).length
        document.title = unread > 0 ? `(${unread}) NexusForge AI` : 'NexusForge AI'
      } catch { document.title = 'NexusForge AI' }
    }
    update()
    window.addEventListener('nxf-notification', update)
    const interval = setInterval(update, 10000)
    return () => { window.removeEventListener('nxf-notification', update); clearInterval(interval) }
  }, [])

  // Scroll to top on route change + remember last page
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    if (location.pathname !== '/') {
      try { localStorage.setItem('nxf_last_page', location.pathname) } catch {}
    }
  }, [location.pathname])

  const [showTour, setShowTour] = useState(() => {
    try { return !localStorage.getItem('nxf-tour-done') } catch { return false }
  })
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('nf_user')
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })

  const toast = useToastState()

  const handleLogin = useCallback((userData) => {
    setUser(userData)
    // Redirect to last visited page or dashboard
    const lastPage = (() => { try { return localStorage.getItem('nxf_last_page') } catch { return null } })()
    routerNavigate(lastPage || '/')
  }, [routerNavigate])

  const handleLogout = useCallback(() => {
    localStorage.removeItem('nf_token')
    localStorage.removeItem('nf_user')
    setUser(null)
    routerNavigate('/')
  }, [routerNavigate])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('nexusforge_theme', theme)
  }, [theme])

  // Bridge: old navigate(pageKey) → React Router push
  const navigate = useCallback((page) => {
    const path = PAGE_TO_PATH[page] || '/'
    routerNavigate(path)
  }, [routerNavigate])

  const navigateToBuilder = useCallback((workflowId = null) => {
    if (workflowId) {
      routerNavigate(`/workflows/builder/${workflowId}`)
    } else {
      routerNavigate('/workflows/builder')
    }
  }, [routerNavigate])

  // Derive currentPage from URL for Layout sidebar highlighting
  const currentPage = useMemo(() => {
    const path = location.pathname
    if (path === '/') return 'dashboard'
    // Check exact matches first
    const exact = PATH_TO_PAGE[path]
    if (exact) return exact
    // Check prefix matches
    if (path.startsWith('/automations')) return 'automations'
    if (path.startsWith('/workflows')) return 'workflows'
    if (path.startsWith('/executions')) return 'executions'
    return 'dashboard'
  }, [location.pathname])

  // Dynamic page title
  useEffect(() => {
    const PAGE_TITLES = {
      dashboard: 'Dashboard', automations: 'Automations', wizard: 'AI Wizard',
      intelligence: 'Intelligence', integrations: 'Integrations', settings: 'Settings',
      workflows: 'Workflows', executions: 'Executions', agents: 'Agents',
      swarms: 'Swarms', connectors: 'Connectors', audit: 'Audit', metrics: 'Metrics', status: 'Status',
    }
    const title = PAGE_TITLES[currentPage] || 'NexusForge AI'
    // Preserve notification count prefix if present
    const existing = document.title
    const match = existing.match(/^\(\d+\)\s/)
    document.title = match ? `${match[0]}${title} — NexusForge AI` : `${title} — NexusForge AI`
  }, [currentPage])

  // Auth gate
  if (!user) {
    return (
      <ToastContext.Provider value={toast}>
        <AuthPage onLogin={handleLogin} lang={lang} />
        <ToastContainer toasts={toast.toasts} onDismiss={toast.dismiss} />
      </ToastContext.Provider>
    )
  }

  return (
    <ToastContext.Provider value={toast}>
      <TopLoadingBar />
      <Layout currentPage={currentPage} onNavigate={navigate} lang={lang} toggleLang={toggleLang} theme={theme} setTheme={setTheme} user={user} onLogout={handleLogout}>
        <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<ChatFirstDashboard lang={lang} onNavigate={navigate} />} />

          {/* Automations */}
          <Route path="/automations" element={
            <AutomationsPage
              lang={lang}
              onNavigateToExecution={(runId) => routerNavigate(`/executions/${runId}`)}
              onOpenDashboard={(id) => routerNavigate(`/automations/${id}`)}
            />
          } />
          <Route path="/automations/:automationId" element={<AutomationDashboardRoute lang={lang} navigate={navigate} />} />

          {/* Wizard */}
          <Route path="/wizard" element={
            <WizardPage
              lang={lang}
              onNavigate={navigate}
              onNavigateToBuilder={navigateToBuilder}
              onNavigateToAutomation={(autoId) => routerNavigate(`/automations/${autoId}`)}
            />
          } />

          {/* Workflows */}
          <Route path="/workflows" element={
            <WorkflowListPage
              onSelectWorkflow={(id) => routerNavigate(`/workflows/${id}`)}
              onEditWorkflow={(id) => navigateToBuilder(id)}
              lang={lang}
            />
          } />
          <Route path="/workflows/builder" element={<WorkflowBuilderPage lang={lang} editWorkflowId={null} onNavigate={navigate} />} />
          <Route path="/workflows/builder/:workflowId" element={<WorkflowBuilderRoute lang={lang} navigate={navigate} />} />
          <Route path="/workflows/:workflowId" element={<WorkflowDetailRoute lang={lang} navigate={navigate} navigateToBuilder={navigateToBuilder} />} />

          {/* Executions */}
          <Route path="/executions" element={
            <ExecutionListPage
              onSelectExecution={(id) => routerNavigate(`/executions/${id}`)}
              lang={lang}
            />
          } />
          <Route path="/executions/:runId" element={<ExecutionDetailRoute lang={lang} />} />

          {/* Intelligence */}
          <Route path="/agents" element={<AgentListPage lang={lang} />} />
          <Route path="/swarms" element={<SwarmListPage lang={lang} />} />

          {/* Advanced */}
          <Route path="/intelligence" element={<IntelligenceHubPage lang={lang} />} />
          <Route path="/connectors" element={<ConnectorHubPage lang={lang} />} />
          <Route path="/audit" element={<AuditLog lang={lang} />} />
          <Route path="/analyze" element={<AnalyzePage lang={lang} />} />
          <Route path="/metrics" element={<CostTokenDashboard lang={lang} />} />
          <Route path="/status" element={<StatusPage lang={lang} />} />
          <Route path="/docs" element={<ApiDocsPage lang={lang} />} />
          <Route path="/refactor" element={<RefactorDashboard lang={lang} />} />
          <Route path="/executive" element={<ExecutiveDashboard lang={lang} />} />
          <Route path="/admin" element={<AdminDashboard lang={lang} />} />

          {/* Config */}
          <Route path="/integrations" element={<IntegrationManagerPage lang={lang} />} />
          <Route path="/settings" element={
            <SettingsPage
              lang={lang}
              setLang={setLang}
              theme={theme}
              setTheme={setTheme}
              onResetTour={() => {
                try { localStorage.removeItem('nxf-tour-done') } catch { /* */ }
                setShowTour(true)
                routerNavigate('/')
              }}
            />
          } />

          {/* 404 */}
          <Route path="*" element={<NotFoundPage lang={lang} />} />
        </Routes>
        </Suspense>
      </Layout>
      <SessionExpiry lang={lang} onLogout={handleLogout} />
      {showTour && (
        <OnboardingTour
          lang={lang}
          onSetLang={setLang}
          onNavigate={navigate}
          onComplete={() => { setShowTour(false); try { localStorage.setItem('nxf-tour-done', '1') } catch {} }}
        />
      )}
      <WhatsNew lang={lang} />
      <KeyboardShortcuts lang={lang} />
      <CommandPalette onNavigate={navigate} lang={lang} onRunAutomation={(auto) => routerNavigate(`/automations/${auto.id}`)} />
      <ChatAssistant lang={lang} />
      <OfflineIndicator lang={lang} />
      <FeedbackWidget lang={lang} />
      <ToastContainer toasts={toast.toasts} onDismiss={toast.dismiss} />
    </ToastContext.Provider>
  )
}

// Route wrappers that extract URL params and pass to components
function AutomationDashboardRoute({ lang, navigate }) {
  const { automationId } = useParams()
  const routerNavigate = useNavigate()
  return (
    <SmartDashboardPage
      automationId={automationId}
      onBack={() => routerNavigate('/automations')}
      onViewExecution={(runId) => routerNavigate(`/executions/${runId}`)}
      lang={lang}
    />
  )
}

function WorkflowDetailRoute({ lang, navigate, navigateToBuilder }) {
  const { workflowId } = useParams()
  const routerNavigate = useNavigate()
  return (
    <WorkflowDetailPage
      workflowId={workflowId}
      onBack={() => routerNavigate('/workflows')}
      onEdit={() => navigateToBuilder(workflowId)}
      onNavigateToExecution={(runId) => routerNavigate(`/executions/${runId}`)}
      lang={lang}
    />
  )
}

function WorkflowBuilderRoute({ lang, navigate }) {
  const { workflowId } = useParams()
  return <WorkflowBuilderPage lang={lang} editWorkflowId={workflowId} onNavigate={navigate} />
}

function ExecutionDetailRoute({ lang }) {
  const { runId } = useParams()
  const routerNavigate = useNavigate()
  return (
    <ExecutionDetailPage
      runId={runId}
      onBack={() => routerNavigate('/executions')}
      lang={lang}
    />
  )
}

// Root component wraps everything in BrowserRouter
export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ErrorBoundary>
  )
}
