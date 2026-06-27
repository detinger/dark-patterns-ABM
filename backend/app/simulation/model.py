"""
Combined Dark-Pattern Trust Model.

Ties together config.py, patterns.py, agents.py, and metrics.py into a
single Mesa 3.x model with:
    - User-type-driven heterogeneous agents (skeptic / naive / activist)
    - Per-pattern detection, harm, and WOM propagation
    - Platform economics, reputation, and adaptation
    - Tipping-point tracking
    - FastAPI-facing API methods (get_latest_metrics, get_timeseries, etc.)
"""

from __future__ import annotations

import networkx as nx
import mesa

from app.simulation.agents import UserAgent, PlatformAgent, clamp
from app.simulation.config import (
    DEFAULT_TYPE_DISTRIBUTION,
    DEFAULT_REPUTATION_RANGE,
    NEGATIVE_WOM_DECAY_RATE,
    POSITIVE_WOM_DECAY_RATE,
    SATISFIED_TRUST_THRESHOLD,
    WOM_COOLDOWN_PERIOD,
    EXIT_WOM_HARM_THRESHOLD,
    BASE_REVENUE_PER_USER,
    CHURN_REPLACEMENT_COST,
    REPUTATION_DAMAGE_COST,
    SUPPORT_COST_RATE,
    REPUTATION_HEALTH_TRUST_WEIGHT,
    REPUTATION_ADJUST_RATE,
    REPUTATION_INTENSITY_DRAG,
    REPUTATION_CHURN_DRAG,
    REPUTATION_NATURAL_CAP,
    TIPPING_POINT_PERSISTENCE,
    MAX_TRUST_LOSS_PER_STEP,
    MAX_HARM_GAIN_PER_STEP,
    NATURAL_ATTRITION_PROBABILITY,
    HIDDEN_EXTRACTION_MULTIPLIER,
    REPUTATION_FLOOR,
    INITIAL_CUMULATIVE_REVENUE,
    REPUTATION_REVENUE_EXPONENT,
    REPUTATION_HEALTHY_REFERENCE,
)
from app.simulation.metrics import build_all_reporters
from app.simulation.patterns import DarkPattern


class DarkPatternTrustModel(mesa.Model):
    """Combined ABM of dark-pattern exposure, trust erosion, and churn."""

    def __init__(
        self,
        num_users=500,
        network_type="small_world",
        avg_degree=8,
        rewire_prob=0.08,
        max_steps=104,
        seed=None,
        dark_pattern_intensity=0.40,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        customer_support_quality=0.30,
        adaptive_platform=False,
        social_influence_strength=0.18,
        review_visibility=0.35,
        retention_bonus=0.0,
        reputation_range=None,
    ):
        super().__init__(rng=seed)

        # ── Store parameters ──────────────────────────────────────────
        self.max_steps = max_steps
        self.network_type = network_type
        self.avg_degree = avg_degree
        self.rewire_prob = rewire_prob
        self.social_influence_strength = social_influence_strength
        self.review_visibility = review_visibility
        self.retention_bonus = retention_bonus
        self.dark_pattern_intensity = dark_pattern_intensity
        self.pattern_forced_trial = pattern_forced_trial
        self.pattern_hard_cancel = pattern_hard_cancel
        self.pattern_drip_pricing = pattern_drip_pricing

        # ── User-type distribution (agents read this) ─────────────────
        self.type_distribution = dict(DEFAULT_TYPE_DISTRIBUTION)

        # ── Dark-pattern objects ──────────────────────────────────────
        self.dark_patterns: dict[str, DarkPattern] = {}
        pattern_flags = {
            "forced_trial": pattern_forced_trial,
            "hard_cancel": pattern_hard_cancel,
            "drip_pricing": pattern_drip_pricing,
        }
        for name, enabled in pattern_flags.items():
            intensity = dark_pattern_intensity if enabled else 0.0
            self.dark_patterns[name] = DarkPattern.from_config(name, intensity)

        # ── Platform agent ────────────────────────────────────────────
        self.platform = PlatformAgent(
            self,
            dark_pattern_intensity=dark_pattern_intensity,
            customer_support_quality=customer_support_quality,
            adaptive_platform=adaptive_platform,
        )

        # ── Network ───────────────────────────────────────────────────
        self.graph = self._build_network(num_users, network_type, avg_degree, rewire_prob)

        # ── User agents ───────────────────────────────────────────────
        self.user_agents: list[UserAgent] = []
        for _ in range(num_users):
            agent = UserAgent(self)
            self.user_agents.append(agent)

        # Assign agents to graph nodes and build lookup dict
        self.user_by_network: dict[int, UserAgent] = {}
        for node_id, agent in zip(self.graph.nodes(), self.user_agents):
            self.graph.nodes[node_id]["agent"] = agent
            agent.network_id = int(node_id)
            self.user_by_network[int(node_id)] = agent

        # ── Per-step counters ─────────────────────────────────────────
        self._step_churns: int = 0
        self._step_negative_wom: int = 0
        self._step_positive_wom: int = 0

        # ── Cumulative counters ───────────────────────────────────────
        self._cumulative_negative_wom: int = 0
        self._cumulative_positive_wom: int = 0

        # ── Aggregate state ───────────────────────────────────────────
        self.churn_rate: float = 0.0
        self.cumulative_churn: float = 0.0

        # ── Per-pattern step counters ─────────────────────────────────
        self._step_detections_by_pattern: dict[str, int] = {p: 0 for p in self.dark_patterns}
        self._step_trust_loss_by_pattern: dict[str, float] = {p: 0.0 for p in self.dark_patterns}
        self._step_exposure_count_by_pattern: dict[str, int] = {p: 0 for p in self.dark_patterns}

        # ── Economics ─────────────────────────────────────────────────
        rep_range = reputation_range if reputation_range is not None else DEFAULT_REPUTATION_RANGE
        self.platform_reputation: float = self.random.uniform(*rep_range)
        self._step_revenue: float = 0.0
        self._step_base_revenue: float = 0.0
        self._step_dp_revenue: float = 0.0
        self._step_costs: float = 0.0
        self._step_profit: float = 0.0
        self._cumulative_revenue: float = INITIAL_CUMULATIVE_REVENUE
        self._cumulative_base_revenue: float = 0.0
        self._cumulative_costs: float = 0.0
        self._net_value: float = INITIAL_CUMULATIVE_REVENUE
        # Opportunity-cost baseline: revenue an idealized no-dark-pattern platform
        # would earn — FULL user retention at a fixed healthy reputation. This is
        # the same clean reference for every scenario (so cross-scenario gaps are
        # comparable) and is high enough that the control never out-earns it,
        # keeping opportunity_cost coherent (>= 0 for control).
        healthy_rep_factor = (REPUTATION_HEALTHY_REFERENCE / 100.0) ** REPUTATION_REVENUE_EXPONENT
        self._projected_step_revenue: float = (
            len(self.user_agents) * BASE_REVENUE_PER_USER * healthy_rep_factor
        )
        self._cumulative_projected_revenue: float = INITIAL_CUMULATIVE_REVENUE
        self._opportunity_cost: float = 0.0

        # ── Tipping points ────────────────────────────────────────────
        self.tipping_point_persistence: int = TIPPING_POINT_PERSISTENCE
        self._tipping_streaks: dict[str, int] = {
            "trust_collapse": 0,
            "social_contagion": 0,
            "churn_cascade": 0,
            "extractive_divergence": 0,
        }
        self.tipping_points: dict[str, dict] = {
            "trust_collapse": {
                "label": "Trust Collapse",
                "description": f"Mean trust stays at or below 0.50 for {self.tipping_point_persistence} consecutive steps.",
                "triggered": False,
                "step": None,
            },
            "social_contagion": {
                "label": "Social Contagion",
                "description": f"Negative WOM stays at or above 0.22 for {self.tipping_point_persistence} consecutive steps.",
                "triggered": False,
                "step": None,
            },
            "churn_cascade": {
                "label": "Churn Cascade",
                "description": f"Cumulative churn stays at or above 0.35 for {self.tipping_point_persistence} consecutive steps.",
                "triggered": False,
                "step": None,
            },
            "extractive_divergence": {
                "label": "Extractive Divergence",
                "description": f"Revenue gap exceeds 20% of short-term revenue while cumulative churn stays at or above 0.15 for {self.tipping_point_persistence} consecutive steps.",
                "triggered": False,
                "step": None,
            },
        }

        # ── Recent events (for frontend) ──────────────────────────────
        self.recent_events: dict = self._empty_recent_events()

        # ── Data collector ────────────────────────────────────────────
        self.datacollector = mesa.DataCollector(
            model_reporters=build_all_reporters(),
        )
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # Network helpers
    # ------------------------------------------------------------------

    def _build_network(
        self, num_users: int, network_type: str, avg_degree: int, rewire_prob: float
    ):
        seed = self.random.randint(0, 1_000_000)
        if network_type == "small_world":
            return nx.watts_strogatz_graph(num_users, avg_degree, rewire_prob, seed=seed)
        if network_type == "scale_free":
            return nx.barabasi_albert_graph(num_users, max(1, avg_degree // 2), seed=seed)
        p = avg_degree / max(1, num_users - 1)
        return nx.erdos_renyi_graph(num_users, p, seed=seed)

    def _empty_recent_events(self) -> dict:
        return {
            "step": 0,
            "direct_exposures": [],
            "social_edges": [],
            "churned_nodes": [],
        }

    # ------------------------------------------------------------------
    # Main simulation step
    # ------------------------------------------------------------------

    def step(self):
        if self.steps >= self.max_steps:
            self.running = False
            return

        # ── Reset per-step counters ───────────────────────────────────
        self._step_churns = 0
        self._step_negative_wom = 0
        self._step_positive_wom = 0
        self._step_detections_by_pattern = {p: 0 for p in self.dark_patterns}
        self._step_trust_loss_by_pattern = {p: 0.0 for p in self.dark_patterns}
        self._step_exposure_count_by_pattern = {p: 0 for p in self.dark_patterns}

        direct_exposures: list[int] = []

        # ── 1. Per-user exposure / detection / harm ───────────────────
        for user in self.user_agents:
            if not user.active:
                continue

            # Reset per-step scratch
            user._step_detected_patterns = []
            user._step_total_harm = 0.0
            user._step_wom_received = 0
            user.last_exposure = 0.0

            # Decay
            user.warning_awareness = max(
                0.0, user.warning_awareness * (1 - NEGATIVE_WOM_DECAY_RATE)
            )
            user.positive_sentiment = max(
                0.0, user.positive_sentiment * (1 - POSITIVE_WOM_DECAY_RATE)
            )

            # Snapshot pre-exposure state for per-step caps
            pre_trust = user.trust
            pre_harm = user.harm

            # Exposure / detection / harm per pattern
            for pname, pattern in self.dark_patterns.items():
                if pattern.intensity <= 0.0:
                    continue

                prev_harm = user._step_total_harm
                detected = user.apply_direct_exposure(pattern, pattern.intensity)

                if detected:
                    self._step_detections_by_pattern[pname] += 1

                harm_delta = user._step_total_harm - prev_harm
                if harm_delta > 0:
                    self._step_trust_loss_by_pattern[pname] += harm_delta
                    self._step_exposure_count_by_pattern[pname] += 1

            # Cap per-step trust loss and harm gain.
            # The doc formula assumes ONE aggregated exposure per step;
            # 3 simultaneous patterns would otherwise triple the loss.
            trust_loss = pre_trust - user.trust
            if trust_loss > MAX_TRUST_LOSS_PER_STEP:
                user.trust = pre_trust - MAX_TRUST_LOSS_PER_STEP
                user.perceived_fairness = max(
                    user.perceived_fairness,
                    user.trust,
                )
            harm_gain = user.harm - pre_harm
            if harm_gain > MAX_HARM_GAIN_PER_STEP:
                user.harm = pre_harm + MAX_HARM_GAIN_PER_STEP

            if user.last_exposure > 0 and user.network_id is not None:
                direct_exposures.append(user.network_id)

        # ── 2. Social signal propagation (negative WOM) ───────────────
        social_edges: list[dict] = []
        for user in self.user_agents:
            if not user.active:
                continue
            user.decide_word_of_mouth()
            if user.negative_wom > 0:
                edges = user.spread_negative_wom(
                    self.graph, self.social_influence_strength
                )
                social_edges.extend(edges)
                self._step_negative_wom += len(edges)

        # Apply accumulated social signals
        for user in self.user_agents:
            user.apply_social_signal()

        # ── 3. Recovery ───────────────────────────────────────────────
        for user in self.user_agents:
            user.apply_recovery()

        # ── 3b. Natural trust recovery ───────────────────────────────
        for user in self.user_agents:
            user.apply_natural_recovery()

        # ── 4. Positive WOM ───────────────────────────────────────────
        # Snapshot positive_wom_sent before the loop so we can track delta
        pos_wom_snapshot: dict[int, int] = {}
        for user in self.user_agents:
            if user.active:
                pos_wom_snapshot[user.unique_id] = user.positive_wom_sent

        for user in self.user_agents:
            if not user.active:
                continue
            if (not user._step_detected_patterns
                    and user.trust >= SATISFIED_TRUST_THRESHOLD
                    and user.negative_wom <= 0
                    and user.harm <= 0
                    and user.cumulative_exposure <= 0):
                cooldown_clear = (
                    self.steps - user.last_negative_wom_received_step
                ) >= WOM_COOLDOWN_PERIOD
                if cooldown_clear:
                    user.spread_positive_wom(
                        self.graph, self.social_influence_strength
                    )

        # Count the delta
        for user in self.user_agents:
            if user.active and user.unique_id in pos_wom_snapshot:
                delta = user.positive_wom_sent - pos_wom_snapshot[user.unique_id]
                self._step_positive_wom += delta

        # ── 5. Churn decisions ────────────────────────────────────────
        churned_nodes: list[int] = []
        for user in self.user_agents:
            if user.maybe_churn():
                self._step_churns += 1
                if user.network_id is not None:
                    churned_nodes.append(user.network_id)
                # Exit WOM for high-harm churners (force=True bypasses active check)
                if user.harm >= EXIT_WOM_HARM_THRESHOLD:
                    edges = user.spread_negative_wom(
                        self.graph, self.social_influence_strength, force=True
                    )
                    social_edges.extend(edges)
                    self._step_negative_wom += len(edges)

        # ── 5b. Natural attrition ─────────────────────────────────────
        # Background churn unrelated to dark patterns (~0.01% per agent/step).
        for user in self.user_agents:
            if user.active and self.random.random() < NATURAL_ATTRITION_PROBABILITY:
                user.active = False
                self._step_churns += 1
                if user.network_id is not None:
                    churned_nodes.append(user.network_id)

        # ── 6. Update platform outcomes ───────────────────────────────
        self._update_platform_outcomes()
        self.platform.adapt_strategy()
        self._update_economics()
        self._update_reputation()
        self._update_tipping_points()

        # ── 7. Cumulative counters ────────────────────────────────────
        self._cumulative_negative_wom += self._step_negative_wom
        self._cumulative_positive_wom += self._step_positive_wom

        # ── 8. Store recent events for frontend ───────────────────────
        self.recent_events = {
            "step": int(self.steps),
            "direct_exposures": direct_exposures,
            "social_edges": social_edges,
            "churned_nodes": churned_nodes,
        }

        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # Platform outcome helpers
    # ------------------------------------------------------------------

    def _update_platform_outcomes(self) -> None:
        """Compute cumulative churn, churn rate, and the 0-1 reputation health
        signal.  Revenue ledgers are owned by _update_economics (single source
        of truth) so short-term / long-term revenue stay consistent with the
        charted cumulative_revenue series."""
        active = [a for a in self.user_agents if a.active]
        churned = [a for a in self.user_agents if not a.active]
        prev_cumulative = self.cumulative_churn
        self.cumulative_churn = len(churned) / len(self.user_agents) if self.user_agents else 0.0
        self.churn_rate = max(0.0, self.cumulative_churn - prev_cumulative)

        # Instantaneous reputation "health" (0-1): the same trust/WOM blend that
        # drives the 0-100 model-level reputation target (REPUTATION_HEALTH_TRUST_WEIGHT).
        mean_tr = sum(a.trust for a in active) / len(active) if active else 0.0
        mean_wom = sum(a.negative_wom for a in active) / len(active) if active else 0.0
        w = REPUTATION_HEALTH_TRUST_WEIGHT
        self.platform.reputation = clamp(w * mean_tr + (1.0 - w) * (1.0 - mean_wom))

    def _update_economics(self) -> None:
        """Compute step-level and cumulative economics."""
        active_count = sum(1 for a in self.user_agents if a.active)

        reputation_factor = (
            self.platform_reputation / 100.0
        ) ** REPUTATION_REVENUE_EXPONENT

        step_base_revenue = active_count * BASE_REVENUE_PER_USER * reputation_factor

        # Dark-pattern revenue: undetected exposures are MORE profitable than
        # detected ones — silent extraction (hidden charges, forced upsells,
        # drip fees) carries no complaint or churn signal for the platform.
        step_dp_revenue = 0.0
        for dp in self.dark_patterns.values():
            if dp.intensity <= 0.0:
                continue
            detected = self._step_detections_by_pattern.get(dp.name, 0)
            exposed = self._step_exposure_count_by_pattern.get(dp.name, 0)
            undetected = max(0, exposed - detected)
            step_dp_revenue += (
                detected * dp.intensity * dp.short_term_gain_weight
                + undetected * dp.intensity * dp.short_term_gain_weight * HIDDEN_EXTRACTION_MULTIPLIER
            ) * reputation_factor

        # Persist breakdown for metrics / charts
        self._step_base_revenue = step_base_revenue
        self._step_dp_revenue = step_dp_revenue

        step_churn_cost = self._step_churns * CHURN_REPLACEMENT_COST
        step_support_cost = (
            active_count * SUPPORT_COST_RATE * self.platform.customer_support_quality
        )
        step_wom_damage = self._step_negative_wom * REPUTATION_DAMAGE_COST

        self._step_revenue = step_base_revenue + step_dp_revenue
        self._step_costs = step_churn_cost + step_support_cost + step_wom_damage
        self._step_profit = self._step_revenue - self._step_costs
        self._cumulative_revenue += self._step_revenue
        self._cumulative_base_revenue += step_base_revenue
        self._cumulative_costs += self._step_costs
        self._net_value = self._cumulative_revenue - self._cumulative_costs
        self._cumulative_projected_revenue += self._projected_step_revenue
        self._opportunity_cost = self._cumulative_projected_revenue - self._cumulative_revenue

        # Unified revenue ledgers (single source of truth — same components as
        # the charted cumulative_revenue, excluding the pre-sim seed balance).
        #   short_term : gross booked revenue, INCLUDING dark-pattern extraction
        #   long_term  : sustainable revenue = base only, eroded by abandonment
        # Their gap drives the extractive_divergence tipping point, so it now
        # actually rises with extraction (previously the extraction term
        # cancelled out, leaving a pure churn×trust quantity).
        self.platform.short_term_revenue = (
            self._cumulative_revenue - INITIAL_CUMULATIVE_REVENUE
        )
        self.platform.long_term_revenue = (
            self._cumulative_base_revenue * (1.0 - self.cumulative_churn)
        )

    def _update_reputation(self) -> None:
        """Mean-revert the model-level reputation (0-100) toward a health-based,
        intensity-aware target.

        The old version was an unbounded additive penalty walk dominated by raw
        negative-WOM *volume* with only a flat +0.10/step recovery and no
        intensity term.  It drove every dark-pattern scenario to the hard floor
        (2.0) regardless of intensity — collapsing the per-user revenue rate to
        an identical value and making Low/Medium/High economically
        indistinguishable, with an abrupt late "cliff".

        Reputation now relaxes toward a target each step:
          health  = w·mean_trust(all) + (1−w)·(1 − mean_negative_wom(active))
          target₀₁ = clamp(health − intensity_drag·intensity − churn_drag·churn)
          target   = FLOOR + (CAP − FLOOR)·target₀₁
          rep     += ADJUST_RATE·(target − rep)
        This is smooth, bounded, and monotonic in intensity, so reputation (and
        the revenue it gates) keeps discriminating Low/Medium/High.  Note: agent
        trust/harm/WOM/churn are unaffected — only the platform-level reputation
        and the economics it drives change.
        """
        users = self.user_agents
        mean_trust_all = (
            sum(a.trust for a in users) / len(users) if users else 0.0
        )
        active = [a for a in users if a.active]
        mean_neg_wom = (
            sum(a.negative_wom for a in active) / len(active) if active else 0.0
        )

        w = REPUTATION_HEALTH_TRUST_WEIGHT
        health = w * mean_trust_all + (1.0 - w) * (1.0 - mean_neg_wom)

        intensity = self.platform.dark_pattern_intensity
        target_01 = clamp(
            health
            - REPUTATION_INTENSITY_DRAG * intensity
            - REPUTATION_CHURN_DRAG * self.cumulative_churn
        )
        target = REPUTATION_FLOOR + (REPUTATION_NATURAL_CAP - REPUTATION_FLOOR) * target_01

        self.platform_reputation += REPUTATION_ADJUST_RATE * (
            target - self.platform_reputation
        )
        self.platform_reputation = max(
            REPUTATION_FLOOR, min(REPUTATION_NATURAL_CAP, self.platform_reputation)
        )

    def _update_tipping_points(self) -> None:
        """Check and update tipping-point status using streak counting."""
        active = [a for a in self.user_agents if a.active]
        mean_trust_value = (
            sum(a.trust for a in active) / len(active) if active else 0.0
        )
        mean_wom_value = (
            sum(a.negative_wom for a in active) / len(active) if active else 0.0
        )

        revenue_gap_share = 0.0
        if self.platform.short_term_revenue > 0:
            revenue_gap_share = (
                self.platform.short_term_revenue - self.platform.long_term_revenue
            ) / self.platform.short_term_revenue

        current_step = int(self.steps)
        conditions = {
            "trust_collapse": mean_trust_value <= 0.50,
            "social_contagion": mean_wom_value >= 0.22,
            "churn_cascade": self.cumulative_churn >= 0.35,
            "extractive_divergence": (
                revenue_gap_share >= 0.20 and self.cumulative_churn >= 0.15
            ),
        }

        for name, condition in conditions.items():
            self._tipping_streaks[name] = (
                self._tipping_streaks[name] + 1 if condition else 0
            )
            if (
                not self.tipping_points[name]["triggered"]
                and self._tipping_streaks[name] >= self.tipping_point_persistence
            ):
                self.tipping_points[name]["triggered"] = True
                self.tipping_points[name]["step"] = current_step

    # ------------------------------------------------------------------
    # FastAPI-facing API methods
    # ------------------------------------------------------------------

    def get_latest_metrics(self) -> dict:
        """Get the latest row from the datacollector as a dict."""
        df = self.datacollector.get_model_vars_dataframe()
        if df.empty:
            return {}
        latest = df.iloc[-1].to_dict()
        return {k: float(v) if hasattr(v, "item") else v for k, v in latest.items()}

    def get_timeseries(self) -> list[dict]:
        """Full timeseries from the datacollector."""
        df = self.datacollector.get_model_vars_dataframe().reset_index(names="step")
        records = df.to_dict(orient="records")
        normalized = []
        for row in records:
            normalized.append(
                {k: (float(v) if hasattr(v, "item") else v) for k, v in row.items()}
            )
        return normalized

    def get_network_snapshot(self) -> dict:
        """Network snapshot: platform node + all user nodes + edges."""
        selected_nodes = list(self.graph.nodes())
        nodes: list[dict] = []
        edges: list[dict] = []

        # Platform node
        nodes.append(
            {
                "nodeId": "platform",
                "id": -1,
                "nodeType": "platform",
                "label": "Platform",
                "trust": round(self.platform.reputation, 4),
                "perceived_fairness": round(self.platform.reputation, 4),
                "harm": 0.0,
                "negative_wom": 0.0,
                "active": True,
                "last_exposure": round(self.platform.dark_pattern_intensity, 4),
                "last_churn_probability": 0.0,
                "reputation": round(self.platform.reputation, 4),
                "dark_pattern_intensity": round(
                    self.platform.dark_pattern_intensity, 4
                ),
                "customer_support_quality": round(
                    self.platform.customer_support_quality, 4
                ),
            }
        )

        # User nodes + platform-to-user edges
        for node_id in selected_nodes:
            agent = self.graph.nodes[node_id]["agent"]
            nodes.append(
                {"nodeId": int(node_id), "nodeType": "user", **agent.to_snapshot()}
            )
            edges.append({"source": "platform", "target": int(node_id)})

        # User-to-user edges
        for src, dst in self.graph.edges():
            edges.append({"source": int(src), "target": int(dst)})

        return {"nodes": nodes, "edges": edges}

    def get_tipping_points(self) -> dict:
        """Return tipping-point status dict."""
        return {
            name: {
                "label": point["label"],
                "description": point["description"],
                "triggered": bool(point["triggered"]),
                "step": point["step"],
            }
            for name, point in self.tipping_points.items()
        }

    def get_recent_events(self) -> dict:
        """Return recent events for frontend animation."""
        return {
            "step": int(self.steps),
            "direct_exposures": list(self.recent_events["direct_exposures"]),
            "social_edges": list(self.recent_events["social_edges"]),
            "churned_nodes": list(self.recent_events["churned_nodes"]),
        }
