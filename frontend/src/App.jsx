import { useState } from 'react'
import Layout from './shared/components/Layout'
import DashboardPage from './features/dashboard/DashboardPage'
import WorkflowListPage from './features/workflows/WorkflowListPage'
import WorkflowDetailPage from './features/workflows/WorkflowDetailPage'
import ExecutionListPage from './features/executions/ExecutionListPage'
import ExecutionDetailPage from './features/executions/ExecutionDetailPage'
import AgentListPage from './features/agents/AgentListPage'
import SwarmListPage from './features/swarms/SwarmListPage'
import DocumentListPage from './features/documents/DocumentListPage'
import SettingsPage from './features/settings/SettingsPage'

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [selectedWorkflow, setSelectedWorkflow] = useState(null)
  const [selectedExecution, setSelectedExecution] = useState(null)

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
        />
      )
    }

    if (currentPage === 'executions' && selectedExecution) {
      return (
        <ExecutionDetailPage
          runId={selectedExecution}
          onBack={() => setSelectedExecution(null)}
        />
      )
    }

    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />
      case 'workflows':
        return (
          <WorkflowListPage
            onSelectWorkflow={(id) => setSelectedWorkflow(id)}
          />
        )
      case 'executions':
        return (
          <ExecutionListPage
            onSelectExecution={(id) => setSelectedExecution(id)}
          />
        )
      case 'agents':
        return <AgentListPage />
      case 'swarms':
        return <SwarmListPage />
      case 'documents':
        return <DocumentListPage />
      case 'settings':
        return <SettingsPage />
      default:
        return <DashboardPage />
    }
  }

  return (
    <Layout currentPage={currentPage} onNavigate={navigate}>
      {renderPage()}
    </Layout>
  )
}
