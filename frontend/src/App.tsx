import { useState, useEffect, useCallback } from 'react'
import { Sidebar } from './components/Sidebar'
import { Header } from './components/Header'
import type { NavItemId } from './types/navigation'
import type { HealthResponse } from './types/api'
import { apiService } from './services/api'

import { OverviewView } from './views/OverviewView'
import { InvestigationsView } from './views/InvestigationsView'
import { GraphExplorerView } from './views/GraphExplorerView'
import { EvidenceView } from './views/EvidenceView'
import { AttackLabView } from './views/AttackLabView'
import { EvaluationView } from './views/EvaluationView'

function App() {
  const [activeTab, setActiveTab] = useState<NavItemId>('overview')
  const [selectedTxForGraph, setSelectedTxForGraph] = useState<string>('TX_FLAGGED_9823')
  const [selectedTxForDossier, setSelectedTxForDossier] = useState<string>('TX_FLAGGED_9823')

  // Shared backend health state
  const [healthState, setHealthState] = useState<{
    health: HealthResponse | null
    loading: boolean
    error: string | null
  }>({
    health: null,
    loading: true,
    error: null,
  })

  const checkHealth = useCallback(async () => {
    setHealthState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const data = await apiService.getHealth()
      setHealthState({ health: data, loading: false, error: null })
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to connect to backend server'
      setHealthState({ health: null, loading: false, error: errorMsg })
    }
  }, [])

  useEffect(() => {
    checkHealth()
  }, [checkHealth])

  const handleSelectTransactionForGraph = (txId: string) => {
    setSelectedTxForGraph(txId)
    setActiveTab('graph-explorer')
  }

  const handleSelectTransactionForDossier = (txId: string) => {
    setSelectedTxForDossier(txId)
    setActiveTab('evidence')
  }

  const getPageTitle = (id: NavItemId): string => {
    switch (id) {
      case 'overview':
        return 'Overview'
      case 'investigations':
        return 'Investigations'
      case 'graph-explorer':
        return 'Graph Explorer'
      case 'evidence':
        return 'Evidence'
      case 'attack-lab':
        return 'Attack Lab'
      case 'evaluation':
        return 'Evaluation'
      default:
        return 'Overview'
    }
  }

  const renderActiveView = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <OverviewView
            healthState={healthState}
            onRefreshHealth={checkHealth}
            onNavigate={(id) => setActiveTab(id)}
            onSelectTransactionForGraph={handleSelectTransactionForGraph}
            onSelectTransactionForDossier={handleSelectTransactionForDossier}
          />
        )
      case 'investigations':
        return (
          <InvestigationsView
            onSelectTransactionForGraph={handleSelectTransactionForGraph}
            onSelectTransactionForDossier={handleSelectTransactionForDossier}
          />
        )
      case 'graph-explorer':
        return <GraphExplorerView initialTransactionId={selectedTxForGraph} />
      case 'evidence':
        return <EvidenceView initialTransactionId={selectedTxForDossier} />
      case 'attack-lab':
        return (
          <AttackLabView
            onSelectTransactionForGraph={handleSelectTransactionForGraph}
            onSelectTransactionForDossier={handleSelectTransactionForDossier}
          />
        )
      case 'evaluation':
        return <EvaluationView />
      default:
        return (
          <OverviewView
            healthState={healthState}
            onRefreshHealth={checkHealth}
            onNavigate={(id) => setActiveTab(id)}
            onSelectTransactionForGraph={handleSelectTransactionForGraph}
            onSelectTransactionForDossier={handleSelectTransactionForDossier}
          />
        )
    }
  }

  return (
    <div className="app-container">
      <Sidebar
        activeItemId={activeTab}
        onSelectNavItem={(id) => setActiveTab(id)}
      />
      <main className="main-workspace">
        <Header
          title={getPageTitle(activeTab)}
          health={healthState.health}
          loading={healthState.loading}
          error={healthState.error}
        />
        <section className="workspace-body">{renderActiveView()}</section>
      </main>
    </div>
  )
}

export default App
