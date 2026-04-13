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
    CHURN_REPUTATION_WEIGHT,
    WOM_REPUTATION_WEIGHT,
    POSITIVE_WOM_REPUTATION_WEIGHT,
    REPUTATION_RECOVERY_RATE,
    REPUTATION_NATURAL_CAP,
    TIPPING_POINT_PERSISTENCE,
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
    ):
        super().__init__(rng=seed)

        # ── Store parameters ──────────────────────────────────────────
        self.max_steps = max_steps
        self.network_type = network_type
        self.avg_degree = avg_degree
        self.rewire_prob = rewire_prob
        self.social_influence_strength = social_influence_strength
        self.review_visibility = review_visibility
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
        self.platform_reputation: float = self.random.uniform(*DEFAULT_REPUTATION_RANGE)
        self._step_revenue: float = 0.0
        self._step_costs: float = 0.0
        self._step_profit: float = 0.0
        self._cumulative_revenue: float = 0.0
        self._cumulative_costs: float = 0.0
        self._net_value: float = 0.0

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
                "description": "Mean trust stays at or below 0.50 for three consecutive steps.",
                "triggered": False,
                "step": None,
            },
            "social_contagion": {
                "label": "Social Contagion",
                "description": "Negative WOM stays at or above 0.22 for three consecutive steps.",
                "triggered": False,
                "step": None,
            },
            "churn_cascade": {
                "label": "Churn Cascade",
                "description": "Cumulative churn stays at or above 0.35 for three consecutive steps.",
                "triggered": False,
                "step": None,
            },
            "extractive_divergence": {
                "label": "Extractive Divergence",
                "description": "Revenue gap exceeds 20% of short-term revenue while cumulative churn stays at or above 0.15 for three consecutive steps.",
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

    def _draw_beta(self, mean: float, sd: float) -> float:
        """Draw from a Beta distribution given mean and sd. Kept for backward compat."""
        epsilon = 1e-6
        bounded_mean = min(max(mean, epsilon), 1.0 - epsilon)
        requested_variance = max(sd, epsilon) ** 2
        max_variance = bounded_mean * (1.0 - bounded_mean)
        bounded_variance = min(requested_variance, max_variance * (1.0 - epsilon))
        concentration = (bounded_mean * (1.0 - bounded_mean) / bounded_variance) - 1.0
        alpha = bounded_mean * concentration
        beta = (1.0 - bounded_mean) * concentration
        return clamp(self.random.betavariate(alpha, beta))

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
            user.last_exposure = 0.0

            # Decay
            user.warning_awareness = max(
                0.0, user.warning_awareness * (1 - NEGATIVE_WOM_DECAY_RATE)
            )
            user.positive_sentiment = max(
                0.0, user.positive_sentiment * (1 - POSITIVE_WOM_DECAY_RATE)
            )

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

            if user.last_exposure > 0 and user.network_id is not None:
                direct_exposures.append(user.network_id)

        # ── 2. Social signal propagation (negative WOM) ───────────────
        social_edges: list[dict] = []
        for user in self.user_agents:
            if not user.active:
                continue
            user.decide_word_of_mouth()
            if user.negative_wom > 0 and user._step_detected_patterns:
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

        # ── 4. Positive WOM ───────────────────────────────────────────
        # Snapshot positive_wom_sent before the loop so we can track delta
        pos_wom_snapshot: dict[int, int] = {}
        for user in self.user_agents:
            if user.active:
                pos_wom_snapshot[user.unique_id] = user.positive_wom_sent

        for user in self.user_agents:
            if not user.active:
                continue
            if not user._step_detected_patterns and user.trust >= SATISFIED_TRUST_THRESHOLD:
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
        """Compute cumulative churn, churn rate, platform reputation, revenue."""
        active = [a for a in self.user_agents if a.active]
        churned = [a for a in self.user_agents if not a.active]
        prev_cumulative = self.cumulative_churn
        self.cumulative_churn = len(churned) / len(self.user_agents) if self.user_agents else 0.0
        self.churn_rate = max(0.0, self.cumulative_churn - prev_cumulative)

        mean_tr = sum(a.trust for a in active) / len(active) if active else 0.0
        mean_wom = sum(a.negative_wom for a in active) / len(active) if active else 0.0
        self.platform.reputation = clamp(0.7 * mean_tr + 0.3 * (1.0 - mean_wom))

        # Short/long-term revenue (mentor's formula)
        short_gain = 0.0
        for a in active:
            short_gain += 1.0
            short_gain += 0.8 * a.last_exposure
        self.platform.short_term_revenue += short_gain
        self.platform.long_term_revenue = self.platform.short_term_revenue * (
            1.0 - self.cumulative_churn
        )

    def _update_economics(self) -> None:
        """Compute step-level and cumulative economics."""
        active_count = sum(1 for a in self.user_agents if a.active)

        step_base_revenue = active_count * BASE_REVENUE_PER_USER
        step_dp_revenue = sum(
            dp.intensity * dp.short_term_gain_weight * active_count
            for dp in self.dark_patterns.values()
        )
        step_churn_cost = self._step_churns * CHURN_REPLACEMENT_COST
        step_support_cost = (
            active_count * SUPPORT_COST_RATE * self.platform.customer_support_quality
        )
        step_wom_damage = self._step_negative_wom * REPUTATION_DAMAGE_COST

        self._step_revenue = step_base_revenue + step_dp_revenue
        self._step_costs = step_churn_cost + step_support_cost + step_wom_damage
        self._step_profit = self._step_revenue - self._step_costs
        self._cumulative_revenue += self._step_revenue
        self._cumulative_costs += self._step_costs
        self._net_value = self._cumulative_revenue - self._cumulative_costs

    def _update_reputation(self) -> None:
        """Update the model-level platform reputation score (0-100 scale)."""
        n = max(len(self.user_agents), 1)
        churn_penalty = (self._step_churns / n) * CHURN_REPUTATION_WEIGHT * 100
        wom_penalty = (self._step_negative_wom / n) * WOM_REPUTATION_WEIGHT * 100
        pos_wom_boost = (self._step_positive_wom / n) * POSITIVE_WOM_REPUTATION_WEIGHT * 100

        self.platform_reputation = max(
            0.0,
            min(
                REPUTATION_NATURAL_CAP,
                self.platform_reputation
                - churn_penalty
                - wom_penalty
                + pos_wom_boost
                + REPUTATION_RECOVERY_RATE,
            ),
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
