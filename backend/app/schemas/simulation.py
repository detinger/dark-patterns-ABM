from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class SimulationCreateRequest(BaseModel):
    scenario: str | None = None  # If set, use named scenario from config.SCENARIOS
    num_users: int = Field(500, ge=50, le=5000)
    network_type: Literal["small_world", "scale_free", "random"] = "small_world"
    avg_degree: int = Field(8, ge=2, le=50)
    rewire_prob: float = Field(0.08, ge=0.0, le=1.0)
    max_steps: int = Field(104, ge=1, le=500)
    seed: int | None = 42
    dark_pattern_intensity: float = Field(0.40, ge=0.0, le=1.0)
    pattern_forced_trial: bool = True
    pattern_hard_cancel: bool = True
    pattern_drip_pricing: bool = True
    customer_support_quality: float = Field(0.30, ge=0.0, le=1.0)
    adaptive_platform: bool = False
    social_influence_strength: float = Field(0.18, ge=0.0, le=1.0)
    review_visibility: float = Field(0.35, ge=0.0, le=1.0)


class StepRequest(BaseModel):
    count: int = Field(1, ge=-500, le=500)


class SimulationSummary(BaseModel):
    simulation_id: str
    steps: int
    max_steps: int
    params: dict


class SimulationStateResponse(BaseModel):
    simulation_id: str
    steps: int
    max_steps: int
    params: dict
    metrics: dict
    network_snapshot: dict
    platform: dict
    tipping_points: dict
    recent_events: dict


class SimulationTimeseriesResponse(BaseModel):
    simulation_id: str
    series: list[dict]


class ApiMessage(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
