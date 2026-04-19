import { useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import type {
  LiveStreamPayload,
  LiveTransport,
  SimulationCreateRequest,
  SimulationState,
  SimulationSummary,
  TimeseriesResponse,
} from '../types'

export const defaultCreatePayload: SimulationCreateRequest = {
  num_users: 500,
  network_type: 'small_world',
  avg_degree: 8,
  rewire_prob: 0.08,
  max_steps: 312,
  seed: 42,
  dark_pattern_intensity: 0.4,
  pattern_forced_trial: true,
  pattern_hard_cancel: true,
  pattern_drip_pricing: true,
  customer_support_quality: 0.3,
  adaptive_platform: false,
  social_influence_strength: 0.18,
  review_visibility: 0.35,
}

function getLiveDelayMs(liveSpeed: number) {
  return Math.max(80, 760 - liveSpeed * 80)
}

export function useSimulation() {
  const [simulations, setSimulations] = useState<SimulationSummary[]>([])
  const [currentSimulationId, setCurrentSimulationId] = useState<string | null>(null)
  const [state, setState] = useState<SimulationState | null>(null)
  const [timeseries, setTimeseries] = useState<TimeseriesResponse['series']>([])
  const [loading, setLoading] = useState(false)
  const [liveRunning, setLiveRunning] = useState(false)
  const [liveSpeed, setLiveSpeed] = useState(6)
  const [liveTransport, setLiveTransport] = useState<LiveTransport>('websocket')
  const [error, setError] = useState<string | null>(null)

  const applyLivePayload = (payload: LiveStreamPayload) => {
    if (payload.state) {
      setState(payload.state)
    }
    if (payload.series) {
      setTimeseries(payload.series)
    }
    if (payload.simulations) {
      setSimulations(payload.simulations)
    }
  }

  const refreshList = async () => {
    const list = await api.listSimulations()
    setSimulations(list)
  }

  const loadSimulation = async (simulationId: string) => {
    setLiveRunning(false)
    setLoading(true)
    setError(null)
    try {
      const [simulationState, timeseriesState] = await Promise.all([
        api.getSimulation(simulationId),
        api.getTimeseries(simulationId),
      ])
      setCurrentSimulationId(simulationId)
      setState(simulationState)
      setTimeseries(timeseriesState.series)
      await refreshList()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load simulation')
    } finally {
      setLoading(false)
    }
  }

  const createSimulation = async (payload: SimulationCreateRequest) => {
    setLiveRunning(false)
    setLoading(true)
    setError(null)
    try {
      const summary = await api.createSimulation(payload)
      await loadSimulation(summary.simulation_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create simulation')
    } finally {
      setLoading(false)
    }
  }

  const stepSimulation = async (count: number) => {
    if (!currentSimulationId) return
    setLiveRunning(false)
    setLoading(true)
    setError(null)
    try {
      const simulationState = await api.stepSimulation(currentSimulationId, count)
      const timeseriesState = await api.getTimeseries(currentSimulationId)
      setState(simulationState)
      setTimeseries(timeseriesState.series)
      await refreshList()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to step simulation')
    } finally {
      setLoading(false)
    }
  }

  const resetSimulation = async () => {
    if (!currentSimulationId) return
    setLiveRunning(false)
    setLoading(true)
    setError(null)
    try {
      const simulationState = await api.resetSimulation(currentSimulationId)
      const timeseriesState = await api.getTimeseries(currentSimulationId)
      setState(simulationState)
      setTimeseries(timeseriesState.series)
      await refreshList()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset simulation')
    } finally {
      setLoading(false)
    }
  }

  const deleteSimulation = async (simulationId: string) => {
    if (currentSimulationId === simulationId) {
      setLiveRunning(false)
    }
    setLoading(true)
    setError(null)
    try {
      await api.deleteSimulation(simulationId)
      await refreshList()
      if (currentSimulationId === simulationId) {
        setCurrentSimulationId(null)
        setState(null)
        setTimeseries([])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete simulation')
    } finally {
      setLoading(false)
    }
  }

  const exportSimulation = async () => {
    if (!currentSimulationId || !state) return

    setLoading(true)
    setError(null)
    try {
      const blob = await api.downloadSimulationCsv(currentSimulationId)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `simulation-${currentSimulationId}.csv`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export simulation')
    } finally {
      setLoading(false)
    }
  }

  const toggleLiveSimulation = async () => {
    if (!currentSimulationId || !state) return

    setError(null)
    setLiveRunning((current) => {
      if (current) return false
      return state.steps < state.max_steps
    })
  }

  useEffect(() => {
    refreshList().catch((err) => {
      setError(err instanceof Error ? err.message : 'Failed to fetch simulations')
    })
  }, [])

  useEffect(() => {
    if (!liveRunning || !currentSimulationId || !state) return
    if (liveTransport !== 'polling') return
    if (state.steps >= state.max_steps) {
      setLiveRunning(false)
      return
    }

    let cancelled = false
    const liveDelayMs = getLiveDelayMs(liveSpeed)
    const timeoutId = window.setTimeout(async () => {
      try {
        const simulationState = await api.stepSimulation(currentSimulationId, 1)
        const timeseriesState = await api.getTimeseries(currentSimulationId)
        const list = await api.listSimulations()

        if (cancelled) return

        setState(simulationState)
        setTimeseries(timeseriesState.series)
        setSimulations(list)

        if (simulationState.steps >= simulationState.max_steps) {
          setLiveRunning(false)
        }
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to run live simulation')
        setLiveRunning(false)
      }
    }, liveDelayMs)

    return () => {
      cancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [currentSimulationId, liveRunning, liveSpeed, liveTransport, state])

  useEffect(() => {
    if (!liveRunning || !currentSimulationId || !state) return
    if (liveTransport !== 'websocket') return
    if (state.steps >= state.max_steps) {
      setLiveRunning(false)
      return
    }

    let cancelled = false
    let finished = false
    const socket = new WebSocket(
      api.getLiveSimulationWebSocketUrl(currentSimulationId, getLiveDelayMs(liveSpeed)),
    )

    socket.onmessage = (event) => {
      if (cancelled) return

      let payload: LiveStreamPayload
      try {
        payload = JSON.parse(event.data) as LiveStreamPayload
      } catch {
        setError('Received an invalid WebSocket payload')
        setLiveRunning(false)
        socket.close()
        return
      }

      if (payload.event === 'error') {
        finished = true
        setError(payload.message ?? 'WebSocket live stream failed')
        setLiveRunning(false)
        socket.close()
        return
      }

      applyLivePayload(payload)

      if (payload.event === 'complete') {
        finished = true
        setLiveRunning(false)
      }
    }

    socket.onerror = () => {
      if (cancelled || finished) return
      finished = true
      setError('WebSocket live stream failed; switch to polling or retry.')
      setLiveRunning(false)
    }

    socket.onclose = () => {
      if (cancelled || finished) return
      finished = true
      setError('WebSocket live stream disconnected unexpectedly.')
      setLiveRunning(false)
    }

    return () => {
      cancelled = true
      socket.close()
    }
  }, [currentSimulationId, liveRunning, liveSpeed, liveTransport])

  const derived = useMemo(() => {
    const latest = timeseries[timeseries.length - 1]
    return {
      latestStep: latest?.step ?? 0,
      hasSimulation: Boolean(state),
    }
  }, [state, timeseries])

  return {
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
  }
}
