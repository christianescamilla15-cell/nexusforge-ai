import { useState, useEffect, useCallback, useMemo } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams, useLocation } from 'react-router-dom'
import AuthPage from './features/auth/AuthPage'
import Layout from './shared/components/Layout'
import OnboardingTour from './shared/components/OnboardingTour'
import ToastContainer from './shared/components/Toast'
import { useLanguage } from './shared/hooks/useLanguage'
import { useToastState, ToastContext } from './shared/hooks/useToast'
import DashboardPage from './features/dashboard/DashboardPage'
import WorkflowListPage from './features/workflows/WorkflowListPage'
import WorkflowDetailPage from './features/workflows/WorkflowDetailPage'
import WorkflowBuilderPage from './features/workflows/WorkflowBuilderPage'
import ExecutionListPage from './features/executions/ExecutionListPage'
import ExecutionDetailPage from './features/executions/ExecutionDetailPage'
import AgentListPage from './features/agents/AgentListPage'
import SwarmListPage from './features/swarms/SwarmListPage'
import SettingsPage from './features/settings/SettingsPage'
import ChatAssistant from './features/chat/ChatAssistant'
import CostTokenDashboard from './features/metrics/CostTokenDashboard'
import AnalyzePage from './features/analyze/AnalyzePage'
import IntegrationManagerPage from './features/integrations/IntegrationManagerPage'
import WizardPage from './features/wizard/WizardPage'
import AutomationsPage from './features/automations/AutomationsPage'
import SmartDashboardPage from './pages/SmartDashboardPage'
import CommandPalette from './shared/components/CommandPalette'
import ConnectorHubPage from './features/connectors/ConnectorHubPage'
import AuditLog from './features/audit/AuditLog'
import IntelligenceHubPage from './features/intelligence/IntelligenceHubPage'

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
    routerNavigate('/')
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
      <Layout currentPage={currentPage} onNavigate={navigate} lang={lang} toggleLang={toggleLang} theme={theme} setTheme={setTheme} user={user} onLogout={handleLogout}>
        <Routes>
          <Route path="/" element={<DashboardPage lang={lang} onNavigate={navigate} />} />

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

          {/* Catch-all → Dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
      {showTour && (
        <OnboardingTour
          lang={lang}
          onSetLang={setLang}
          onNavigate={navigate}
          onComplete={() => { setShowTour(false); try { localStorage.setItem('nxf-tour-done', '1') } catch {} }}
        />
      )}
      <CommandPalette onNavigate={navigate} lang={lang} />
      <ChatAssistant lang={lang} />
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
      onRun={() => routerNavigate('/automations')}
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
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
