import { useState, useEffect, useCallback } from 'react'
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
import ExecutionTimelineViewer from './features/executions/ExecutionTimelineViewer'
import AnalyzePage from './features/analyze/AnalyzePage'
import IntegrationManagerPage from './features/integrations/IntegrationManagerPage'
import WizardPage from './features/wizard/WizardPage'
import AutomationsPage from './features/automations/AutomationsPage'
import SmartDashboardPage from './pages/SmartDashboardPage'

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [selectedWorkflow, setSelectedWorkflow] = useState(null)
  const [selectedExecution, setSelectedExecution] = useState(null)
  const [editWorkflowId, setEditWorkflowId] = useState(null)
  const [initialDashboardId, setInitialDashboardId] = useState(null)
  const [selectedAutomationId, setSelectedAutomationId] = useState(null)
  const { lang, setLang, toggle: toggleLang } = useLanguage()
  const [theme, setTheme] = useState(() => localStorage.getItem('nexusforge_theme') || 'light')
  const [showTour, setShowTour] = useState(() => {
    try { return !localStorage.getItem('nxf-tour-done') } catch { return false }
  })
  // Auth state
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('nf_user')
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })

  // Toast system
  const toast = useToastState()

  const handleLogin = useCallback((userData) => {
    setUser(userData)
    setCurrentPage('dashboard')
  }, [])

  const handleLogout = useCallback(() => {
    localStorage.removeItem('nf_token')
    localStorage.removeItem('nf_user')
    setUser(null)
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('nexusforge_theme', theme)
  }, [theme])

  const navigate = (page) => {
    setCurrentPage(page)
    setSelectedWorkflow(null)
    setSelectedExecution(null)
    if (page !== 'workflow-builder') setEditWorkflowId(null)
    if (page !== 'automations') {
      setInitialDashboardId(null)
      setSelectedAutomationId(null)
    }
  }

  const navigateToBuilder = (workflowId = null) => {
    setEditWorkflowId(workflowId)
    setCurrentPage('workflow-builder')
    setSelectedWorkflow(null)
    setSelectedExecution(null)
  }

  // Auth gate — must be AFTER all hooks
  if (!user) {
    return (
      <ToastContext.Provider value={toast}>
        <AuthPage onLogin={handleLogin} lang={lang} />
        <ToastContainer toasts={toast.toasts} onDismiss={toast.dismiss} />
      </ToastContext.Provider>
    )
  }

  const renderPage = () => {
    if (currentPage === 'workflows' && selectedWorkflow) {
      return (
        <WorkflowDetailPage
          workflowId={selectedWorkflow}
          onBack={() => setSelectedWorkflow(null)}
          onEdit={() => {
            navigateToBuilder(selectedWorkflow)
          }}
          onNavigateToExecution={(runId) => {
            setCurrentPage('executions')
            setSelectedWorkflow(null)
            setSelectedExecution(runId)
          }}
          lang={lang}
        />
      )
    }

    if (currentPage === 'executions' && selectedExecution) {
      return (
        <ExecutionDetailPage
          runId={selectedExecution}
          onBack={() => setSelectedExecution(null)}
          lang={lang}
        />
      )
    }

    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage lang={lang} onNavigate={navigate} />
      case 'integrations':
        return <IntegrationManagerPage lang={lang} />
      case 'wizard':
        return (
          <WizardPage
            lang={lang}
            onNavigate={navigate}
            onNavigateToBuilder={navigateToBuilder}
            onNavigateToAutomation={(autoId) => {
              setInitialDashboardId(autoId)
              setCurrentPage('automations')
            }}
          />
        )
      case 'workflow-builder':
        return <WorkflowBuilderPage lang={lang} editWorkflowId={editWorkflowId} onNavigate={navigate} />
      case 'workflows':
        return (
          <WorkflowListPage
            onSelectWorkflow={(id) => setSelectedWorkflow(id)}
            onEditWorkflow={(id) => navigateToBuilder(id)}
            lang={lang}
          />
        )
      case 'executions':
        return (
          <ExecutionListPage
            onSelectExecution={(id) => setSelectedExecution(id)}
            lang={lang}
          />
        )
      case 'agents':
        return <AgentListPage lang={lang} />
      case 'swarms':
        return <SwarmListPage lang={lang} />
      case 'automations':
        if (selectedAutomationId) {
          return (
            <SmartDashboardPage
              automationId={selectedAutomationId}
              onBack={() => setSelectedAutomationId(null)}
              onRun={(auto) => {
                setSelectedAutomationId(null)
              }}
              lang={lang}
            />
          )
        }
        return (
          <AutomationsPage
            lang={lang}
            initialDashboardId={initialDashboardId}
            onNavigateToExecution={(runId) => {
              setCurrentPage('executions')
              setSelectedExecution(runId)
            }}
            onOpenDashboard={(id) => setSelectedAutomationId(id)}
          />
        )
      case 'analyze':
        return <AnalyzePage lang={lang} />
      case 'cost-metrics':
        return <CostTokenDashboard lang={lang} />
      case 'timeline':
        return <ExecutionTimelineViewer lang={lang} />
      case 'settings':
        return (
          <SettingsPage
            lang={lang}
            setLang={setLang}
            theme={theme}
            setTheme={setTheme}
            onResetTour={() => {
              try { localStorage.removeItem('nxf-tour-done') } catch { /* */ }
              setShowTour(true)
              setCurrentPage('dashboard')
            }}
          />
        )
      default:
        return <DashboardPage lang={lang} />
    }
  }

  return (
    <ToastContext.Provider value={toast}>
      <Layout currentPage={currentPage} onNavigate={navigate} lang={lang} toggleLang={toggleLang} theme={theme} setTheme={setTheme} user={user} onLogout={handleLogout}>
        {renderPage()}
      </Layout>
      {showTour && (
        <OnboardingTour
          lang={lang}
          onSetLang={setLang}
          onNavigate={navigate}
          onComplete={() => { setShowTour(false); try { localStorage.setItem('nxf-tour-done', '1') } catch {} }}
        />
      )}
      <ChatAssistant lang={lang} />
      <ToastContainer toasts={toast.toasts} onDismiss={toast.dismiss} />
    </ToastContext.Provider>
  )
}
