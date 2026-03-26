import { useState } from 'react'
import Layout from './shared/components/Layout'
import OnboardingTour from './shared/components/OnboardingTour'
import { useLanguage } from './shared/hooks/useLanguage'
import DashboardPage from './features/dashboard/DashboardPage'
import WorkflowListPage from './features/workflows/WorkflowListPage'
import WorkflowDetailPage from './features/workflows/WorkflowDetailPage'
import ExecutionListPage from './features/executions/ExecutionListPage'
import ExecutionDetailPage from './features/executions/ExecutionDetailPage'
import AgentListPage from './features/agents/AgentListPage'
import SwarmListPage from './features/swarms/SwarmListPage'
import DocumentListPage from './features/documents/DocumentListPage'
import SettingsPage from './features/settings/SettingsPage'
import ChatAssistant from './features/chat/ChatAssistant'

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [selectedWorkflow, setSelectedWorkflow] = useState(null)
  const [selectedExecution, setSelectedExecution] = useState(null)
  const { lang, setLang, toggle: toggleLang } = useLanguage()
  const [showTour, setShowTour] = useState(() => !localStorage.getItem('nxf-tour-done'))

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
        return <DashboardPage lang={lang} />
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
      case 'swarms':
        return <SwarmListPage lang={lang} />
      case 'documents':
        return <DocumentListPage lang={lang} />
      case 'settings':
        return (
          <SettingsPage
            lang={lang}
            setLang={setLang}
            onResetTour={() => {
              localStorage.removeItem('nxf-tour-done')
              setShowTour(true)
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
          onNavigate={navigate}
          onComplete={() => setShowTour(false)}
        />
      )}
      <ChatAssistant lang={lang} />
    </>
  )
}
