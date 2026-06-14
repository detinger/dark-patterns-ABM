import type {
  SimulationCreateRequest,
  SimulationState,
  SimulationSummary,
  TimeseriesResponse,
} from '../types'

const LOCAL_API_BASE = 'http://localhost:8000/api'

function getApiBase() {
  if (!import.meta.env.DEV) {
    return '/api'
  }

  const configuredBase = String(import.meta.env.VITE_API_BASE ?? '').trim()
  const unquotedBase =
    configuredBase.length >= 2 &&
    configuredBase[0] === configuredBase[configuredBase.length - 1] &&
    (configuredBase[0] === '"' || configuredBase[0] === "'")
      ? configuredBase.slice(1, -1).trim()
      : configuredBase

  return (unquotedBase || LOCAL_API_BASE).replace(/\/+$/, '')
}

function getApiUrl(path: string) {
  const apiBase = getApiBase()

  if (apiBase.includes('${{')) {
    throw new Error(
      'VITE_API_BASE contains an unresolved variable. Set it to the local backend URL ending in /api.',
    )
  }

  try {
    const url = new URL(`${apiBase}${path}`, window.location.origin)

    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new Error('unsupported protocol')
    }

    return url
  } catch {
    throw new Error(
      'VITE_API_BASE is not a valid URL. Use a value such as http://localhost:8000/api, without quotes.',
    )
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(getApiUrl(path), {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
    ...options,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed with ${response.status}`)
  }

  return response.json() as Promise<T>
}

async function download(path: string): Promise<Blob> {
  const response = await fetch(getApiUrl(path))

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed with ${response.status}`)
  }

  return response.blob()
}

export const api = {
  listSimulations: () => request<SimulationSummary[]>('/simulations'),
  createSimulation: (payload: SimulationCreateRequest) =>
    request<SimulationSummary>('/simulations', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getSimulation: (simulationId: string) => request<SimulationState>(`/simulations/${simulationId}`),
  stepSimulation: (simulationId: string, count: number) =>
    request<SimulationState>(`/simulations/${simulationId}/step`, {
      method: 'POST',
      body: JSON.stringify({ count }),
    }),
  resetSimulation: (simulationId: string) =>
    request<SimulationState>(`/simulations/${simulationId}/reset`, {
      method: 'POST',
    }),
  getTimeseries: (simulationId: string) =>
    request<TimeseriesResponse>(`/simulations/${simulationId}/timeseries`),
  downloadSimulationCsv: (simulationId: string) =>
    download(`/simulations/${simulationId}/export.csv`),
  deleteSimulation: (simulationId: string) =>
    request<{ message: string }>(`/simulations/${simulationId}`, {
      method: 'DELETE',
    }),
  getLiveSimulationWebSocketUrl: (simulationId: string, intervalMs: number) => {
    const url = getApiUrl(`/simulations/${simulationId}/live`)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.searchParams.set('interval_ms', String(intervalMs))
    return url.toString()
  },
}
