import { lazy, Suspense, useEffect, useState } from 'react'
import './styles.css'
import { ChartsPanel } from './components/ChartsPanel'
import { ControlPanel } from './components/ControlPanel'
import { KpiCards } from './components/KpiCards'
import { SimulationList } from './components/SimulationList'
import { TippingPointsPanel } from './components/TippingPointsPanel'
import { useSimulation } from './hooks/useSimulation'

const NetworkGraphPanel = lazy(() =>
  import('./components/NetworkGraphPanel').then((m) => ({ default: m.NetworkGraphPanel })),
)

type ThemeMode = 'light' | 'dark'

function getInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'light'
  }

  const storedTheme = window.localStorage.getItem('dark-patterns-theme')
  if (storedTheme === 'light' || storedTheme === 'dark') {
    return storedTheme
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export default function App() {
  const {
    simulations,
    currentSimulationId,
    state,
    timeseries,
    loading,
    liveRunning,
    liveSpeed,
    liveTransport,
    error,
    derived,
    createSimulation,
    loadSimulation,
    stepSimulation,
    resetSimulation,
    setLiveSpeed,
    setLiveTransport,
    toggleLiveSimulation,
    exportSimulation,
    deleteSimulation,
  } = useSimulation()
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('dark-patterns-theme', theme)
  }, [theme])

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Mesa + FastAPI + React</p>
          <h1>Dark Patterns ABM Simulation</h1>
          <p className="hero-copy">
            A dashboard for exploring long-term trust erosion under dark patterns with Python Mesa backend.
          </p>
        </div>
        <button
          className="theme-toggle secondary"
          onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
          type="button"
        >
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <div className="layout-grid">
        <div className="sidebar">
          <ControlPanel
            onCreate={createSimulation}
            onStep={stepSimulation}
            onReset={resetSimulation}
            onToggleLive={toggleLiveSimulation}
            onExport={exportSimulation}
            onLiveSpeedChange={setLiveSpeed}
            onLiveTransportChange={setLiveTransport}
            disabled={loading}
            hasSimulation={derived.hasSimulation}
            liveRunning={liveRunning}
            liveSpeed={liveSpeed}
            liveTransport={liveTransport}
            activeParams={state?.params ?? null}
          />
          <SimulationList
            simulations={simulations}
            currentSimulationId={currentSimulationId}
            onSelect={loadSimulation}
            onDelete={deleteSimulation}
          />
        </div>

        <div className="content">
          {state ? (
            <>
              <KpiCards metrics={state.metrics} steps={state.steps} maxSteps={state.max_steps} />
              <TippingPointsPanel tippingPoints={state.tipping_points} />
              <ChartsPanel series={timeseries} tippingPoints={state.tipping_points} />
              <Suspense fallback={<section className="panel"><p>Loading network graph…</p></section>}>
                <NetworkGraphPanel
                  simulationId={state.simulation_id}
                  steps={state.steps}
                  snapshot={state.network_snapshot}
                  recentEvents={state.recent_events}
                />
              </Suspense>
            </>
          ) : (
            <section className="panel empty-state">
              <h2>No simulation loaded</h2>
              <p>Create a simulation from the panel to begin.</p>
            </section>
          )}
        </div>
      </div>
    </main>
  )
}
