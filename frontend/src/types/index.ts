export type NetworkType = 'small_world' | 'scale_free' | 'random'

export interface SimulationCreateRequest {
  scenario?: string | null
  num_users: number
  network_type: NetworkType
  avg_degree: number
  rewire_prob: number
  max_steps: number
  seed?: number | null
  dark_pattern_intensity: number
  pattern_forced_trial: boolean
  pattern_hard_cancel: boolean
  pattern_drip_pricing: boolean
  customer_support_quality: number
  adaptive_platform: boolean
  social_influence_strength: number
  review_visibility: number
}

export interface Metrics {
  active_users: number
  mean_trust: number
  mean_trust_all: number
  mean_harm: number
  churn_rate: number
  cumulative_churn: number
  reputation: number
  negative_wom_rate: number
  short_term_revenue: number
  long_term_revenue: number
  step_churns: number
  step_negative_wom_count: number
  step_positive_wom_count: number
  step_base_revenue: number
  step_dp_revenue: number
  step_revenue: number
  step_costs: number
  step_profit: number
  cumulative_revenue: number
  cumulative_costs: number
  net_value: number
  platform_reputation: number
  avg_trust_skeptic: number
  avg_trust_naive: number
  avg_trust_activist: number
}

export interface NetworkNode {
  nodeId: number | string
  id: number
  nodeType: 'user' | 'platform'
  label?: string
  user_type?: 'skeptic' | 'naive' | 'activist'
  trust: number
  perceived_fairness: number
  harm: number
  negative_wom: number
  active: boolean
  last_exposure: number
  last_churn_probability: number
  warning_awareness?: number
  reputation?: number
  dark_pattern_intensity?: number
  customer_support_quality?: number
}

export interface NetworkEdge {
  source: number | string
  target: number | string
}

export interface NetworkSnapshot {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
}

export interface PlatformState {
  dark_pattern_intensity: number
  customer_support_quality: number
  adaptive_platform: boolean
  reputation: number
  short_term_revenue: number
  long_term_revenue: number
}

export interface TippingPointState {
  label: string
  description: string
  triggered: boolean
  step: number | null
}

export interface RecentSocialEdge {
  source: number
  target: number
  intensity: number
}

export interface RecentEventsState {
  step: number
  direct_exposures: number[]
  social_edges: RecentSocialEdge[]
  churned_nodes: number[]
}

export interface SimulationState {
  simulation_id: string
  steps: number
  max_steps: number
  params: Record<string, unknown>
  metrics: Metrics
  network_snapshot: NetworkSnapshot
  platform: PlatformState
  tipping_points: Record<string, TippingPointState>
  recent_events: RecentEventsState
}

export interface SimulationSummary {
  simulation_id: string
  steps: number
  max_steps: number
  params: Record<string, unknown>
}

export interface TimeseriesResponse {
  simulation_id: string
  series: Array<Record<string, number>>
}

export type LiveTransport = 'websocket' | 'polling'

export interface LiveStreamPayload {
  event: 'snapshot' | 'tick' | 'complete' | 'error'
  message?: string
  state?: SimulationState
  series?: TimeseriesResponse['series']
  simulations?: SimulationSummary[]
}
