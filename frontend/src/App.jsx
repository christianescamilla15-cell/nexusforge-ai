import { useState } from 'react'
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

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [selectedWorkflow, setSelectedWorkflow] = useState(null)
  const [selectedExecution, setSelectedExecution] = useState(null)
  const { lang, setLang, toggle: toggleLang } = useLanguage()
  const [showTour, setShowTour] = useState(true)
  const [showOnboarding, setShowOnboarding] = useState(() => {
    try { return !localStorage.getItem('nxf-onboarding-done') } catch { return true }
  })

  const navigate = (page) => {
    setCurrentPage(page)
    setSelectedWorkflow(null)
    setSelectedExecution(null)
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
      case 'settings':
        return (
          <SettingsPage
            lang={lang}
            setLang={setLang}
            onResetTour={() => {
              try { localStorage.removeItem('nxf-tour-done') } catch { /* */ }
              try { localStorage.removeItem('nxf-onboarding-done') } catch { /* */ }
              setShowTour(true)
              setShowOnboarding(true)
            }}
          />
        )
      default:
        return <DashboardPage lang={lang} />
    }
  }

  return (
    <>
      <Layout currentPage={currentPage} onNavigate={navigate} lang={lang} toggleLang={toggleLang}>
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
