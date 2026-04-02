import { useState, useEffect, useCallback } from 'react'
import AuthPage from './features/auth/AuthPage'
import Layout from './shared/components/Layout'
import OnboardingTour from './shared/components/OnboardingTour'
import Onboarding from './shared/components/Onboarding'
import { useLanguage } from './shared/hooks/useLanguage'
import DashboardPage from './features/dashboard/DashboardPage'
import WorkflowListPage from './features/workflows/WorkflowListPage'
import WorkflowDetailPage from './features/workflows/WorkflowDetailPage'
import ExecutionListPage from './features/executions/ExecutionListPage'
import ExecutionDetailPage from './features/executions/ExecutionDetailPage'
import AgentListPage from './features/agents/AgentListPage'
import MemoryPage from './features/memory/MemoryPage'
import SwarmListPage from './features/swarms/SwarmListPage'
import HealingPage from './features/healing/HealingPage'
import DocumentListPage from './features/documents/DocumentListPage'
import SettingsPage from './features/settings/SettingsPage'
import ChatAssistant from './features/chat/ChatAssistant'
import EnterpriseOpsPage from './features/enterprise-ops/EnterpriseOpsPage'
import PlaygroundPage from './features/playground/PlaygroundPage'
import CostTokenDashboard from './features/metrics/CostTokenDashboard'
import ExecutionTimelineViewer from './features/executions/ExecutionTimelineViewer'
import EvaluationPage from './features/evaluations/EvaluationPage'
import FeedbackPage from './features/feedback/FeedbackPage'
import AnalyzePage from './features/analyze/AnalyzePage'

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [selectedWorkflow, setSelectedWorkflow] = useState(null)
  const [selectedExecution, setSelectedExecution] = useState(null)
  const { lang, setLang, toggle: toggleLang } = useLanguage()
  const [theme, setTheme] = useState(() => localStorage.getItem('nexusforge_theme') || 'light')
  const [showTour, setShowTour] = useState(true)
  const [showOnboarding, setShowOnboarding] = useState(() => {
    try { return !localStorage.getItem('nxf-onboarding-done') } catch { return true }
  })

  // Auth state
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('nf_user')
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })

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
  }

  // Auth gate — must be AFTER all hooks
  if (!user) {
    return <AuthPage onLogin={handleLogin} lang={lang} />
  }

  const renderPage = () => {
    if (currentPage === 'workflows' && selectedWorkflow) {
      return (
        <WorkflowDetailPage
          workflowId={selectedWorkflow}
          onBack={() => setSelectedWorkflow(null)}
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
        return (
          <>
            {showOnboarding && (
              <Onboarding
                lang={lang}
                setLang={setLang}
                onDismiss={() => {
                  setShowOnboarding(false)
                  try { localStorage.setItem('nxf-onboarding-done', '1') } catch { /* */ }
                }}
              />
            )}
            <DashboardPage lang={lang} />
          </>
        )
      case 'workflows':
        return (
          <WorkflowListPage
            onSelectWorkflow={(id) => setSelectedWorkflow(id)}
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
      case 'memory':
        return <MemoryPage lang={lang} />
      case 'swarms':
        return <SwarmListPage lang={lang} />
      case 'healing':
        return <HealingPage lang={lang} />
      case 'documents':
        return <DocumentListPage lang={lang} />
      case 'enterprise-ops':
        return <EnterpriseOpsPage lang={lang} />
      case 'analyze':
        return <AnalyzePage lang={lang} />
      case 'playground':
        return <PlaygroundPage lang={lang} />
      case 'cost-metrics':
        return <CostTokenDashboard lang={lang} />
      case 'timeline':
        return <ExecutionTimelineViewer lang={lang} />
      case 'evaluations':
        return <EvaluationPage lang={lang} />
      case 'feedback':
        return <FeedbackPage lang={lang} />
      case 'settings':
        return (
          <SettingsPage
            lang={lang}
            setLang={setLang}
            theme={theme}
            setTheme={setTheme}
            onResetTour={() => {
              try { localStorage.removeItem('nxf-tour-done') } catch { /* */ }
              try { localStorage.removeItem('nxf-onboarding-done') } catch { /* */ }
              setShowTour(true)
              setShowOnboarding(true)
              setCurrentPage('dashboard')
            }}
          />
        )
      default:
        return <DashboardPage lang={lang} />
    }
  }

  return (
    <>
      <Layout currentPage={currentPage} onNavigate={navigate} lang={lang} toggleLang={toggleLang} theme={theme} setTheme={setTheme} user={user} onLogout={handleLogout}>
        {renderPage()}
      </Layout>
      {showTour && (
        <OnboardingTour
          lang={lang}
          onSetLang={setLang}
          onNavigate={navigate}
          onComplete={() => setShowTour(false)}
          onSelectWorkflow={(id) => { setCurrentPage('workflows'); setSelectedWorkflow(id) }}
          onSelectExecution={(id) => { setCurrentPage('executions'); setSelectedExecution(id) }}
        />
      )}
      <ChatAssistant lang={lang} />
    </>
  )
}
