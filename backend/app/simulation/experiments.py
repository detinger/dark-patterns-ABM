"""
Batch experiments for the Dark Patterns ABM.

Usage:
    python -m app.simulation.experiments                  # run all
    python -m app.simulation.experiments --experiment 1   # specific
    python -m app.simulation.experiments --experiment 2 --agents 300 --steps 52
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.simulation.config import (
    SCENARIOS,
    DEFAULT_MAX_STEPS,
    DEFAULT_NUM_AGENTS,
)
from app.simulation.model import DarkPatternTrustModel
from app.simulation.analysis import (
    detect_tipping_point,
    compute_summary_statistics,
    compare_scenarios,
    compare_platforms,
)
from app.simulation.run import make_timestamped_dir, plot_results

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_REPLICATIONS = 5

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_model(
    scenario_name: str,
    num_agents: int,
    max_steps: int,
    seed: int | None = None,
    *,
    network_type: str | None = None,
    dark_pattern_intensity: float | None = None,
) -> tuple[DarkPatternTrustModel, pd.DataFrame]:
    """Create and run a DarkPatternTrustModel from a named scenario.

    Optional overrides for *network_type* and *dark_pattern_intensity* are
    applied on top of the scenario defaults.
    """
    scenario = SCENARIOS[scenario_name]
    intensity = (
        dark_pattern_intensity
        if dark_pattern_intensity is not None
        else scenario["dark_pattern_intensity"]
    )
    kwargs: dict = dict(
        num_users=num_agents,
        seed=seed,
        max_steps=max_steps,
        dark_pattern_intensity=intensity,
        pattern_forced_trial=scenario["patterns"]["forced_trial"],
        pattern_hard_cancel=scenario["patterns"]["hard_cancel"],
        pattern_drip_pricing=scenario["patterns"]["drip_pricing"],
        adaptive_platform=scenario["adaptive_platform"],
        customer_support_quality=scenario["customer_support_quality"],
    )
    if network_type is not None:
        kwargs["network_type"] = network_type
    if "social_influence_strength" in scenario:
        kwargs["social_influence_strength"] = scenario["social_influence_strength"]
    if "retention_bonus" in scenario:
        kwargs["retention_bonus"] = scenario["retention_bonus"]

    model = DarkPatternTrustModel(**kwargs)
    for _ in range(max_steps):
        model.step()
    data = model.datacollector.get_model_vars_dataframe()
    return model, data


def _make_output_dir(base: str, experiment_label: str) -> str:
    """Create <base>/<experiment_label> directory and return its path."""
    path = os.path.join(base, experiment_label)
    os.makedirs(path, exist_ok=True)
    return path


# ============================================================================
# Experiment 1 — Intensity sweep
# ============================================================================

def experiment_intensity_sweep(
    num_agents: int = DEFAULT_NUM_AGENTS,
    max_steps: int = DEFAULT_MAX_STEPS,
    output_dir: str = "results",
) -> pd.DataFrame:
    """Sweep dark_pattern_intensity 0.0..0.8 (step 0.1), all patterns on.

    5 replications per intensity level.  Returns a DataFrame of summary
    statistics with columns: intensity, replication, plus all summary fields.
    """
    out = _make_output_dir(output_dir, "intensity_sweep")
    rows: list[dict] = []
    intensities = [round(i * 0.1, 1) for i in range(9)]  # 0.0 .. 0.8

    # Use medium_intensity as the base scenario (all patterns on)
    base_scenario = "medium_intensity"

    for intensity in intensities:
        for rep in range(NUM_REPLICATIONS):
            seed = rep * 1000 + int(intensity * 100)
            print(f"  Intensity {intensity:.1f}  rep {rep + 1}/{NUM_REPLICATIONS}")
            _, data = _run_model(
                base_scenario, num_agents, max_steps, seed=seed,
                dark_pattern_intensity=intensity,
            )
            summary = compute_summary_statistics(data)
            tp = detect_tipping_point(data)
            summary["intensity"] = intensity
            summary["replication"] = rep
            summary["tipping_point_step"] = tp["tipping_point_step"]
            summary["trigger_rule"] = tp["trigger_rule"]
            rows.append(summary)

    df = pd.DataFrame(rows)
    csv_path = os.path.join(out, "intensity_sweep.csv")
    df.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")
    return df


# ============================================================================
# Experiment 2 — Scenario comparison
# ============================================================================

def experiment_scenario_comparison(
    num_agents: int = DEFAULT_NUM_AGENTS,
    max_steps: int = DEFAULT_MAX_STEPS,
    output_dir: str = "results",
) -> pd.DataFrame:
    """Run all 10 SCENARIOS, 5 replications each.

    Generates per-scenario plots and a comparison bar chart.  Returns the
    comparison DataFrame.
    """
    out = _make_output_dir(output_dir, "scenario_comparison")
    rows: list[dict] = []
    scenario_dfs: dict[str, pd.DataFrame] = {}

    for scenario_name in SCENARIOS:
        last_data = None
        for rep in range(NUM_REPLICATIONS):
            seed = rep * 1000
            print(f"  Scenario '{scenario_name}'  rep {rep + 1}/{NUM_REPLICATIONS}")
            _, data = _run_model(scenario_name, num_agents, max_steps, seed=seed)
            summary = compute_summary_statistics(data)
            tp = detect_tipping_point(data)
            summary["scenario"] = scenario_name
            summary["replication"] = rep
            summary["tipping_point_step"] = tp["tipping_point_step"]
            summary["trigger_rule"] = tp["trigger_rule"]
            rows.append(summary)
            last_data = data

        # Save a plot for the last replication of each scenario
        if last_data is not None:
            tp = detect_tipping_point(last_data)
            plot_results(last_data, scenario_name, tp["tipping_point_step"], out)
            scenario_dfs[scenario_name] = last_data

    df = pd.DataFrame(rows)
    csv_path = os.path.join(out, "scenario_comparison.csv")
    df.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")

    # Comparison bar charts
    _plot_scenario_bars(df, out)

    # Also save the compare_scenarios table
    if scenario_dfs:
        comp = compare_scenarios(scenario_dfs)
        comp.to_csv(os.path.join(out, "scenario_comparison_table.csv"))

    return df


def _plot_scenario_bars(df: pd.DataFrame, output_dir: str) -> None:
    """Create comparison bar charts from the scenario comparison results."""
    metrics = [
        ("final_avg_trust_active", "Final Avg Trust (Active)"),
        ("total_churn", "Total Churn"),
        ("final_reputation", "Final Reputation"),
        ("final_net_value", "Net Value"),
    ]

    grouped = df.groupby("scenario")
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle("Scenario Comparison (mean over replications)", fontsize=14,
                 fontweight="bold")

    for ax, (metric, title) in zip(axes.flat, metrics):
        means = grouped[metric].mean()
        stds = grouped[metric].std()
        means.plot.bar(ax=ax, yerr=stds, capsize=3, color="steelblue", alpha=0.8)
        ax.set_title(title)
        ax.set_ylabel(metric)
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(output_dir, "scenario_comparison_bars.png"), dpi=150)
    plt.close(fig)


# ============================================================================
# Experiment 3 — Market comparison (dark vs. clean)
# ============================================================================

def experiment_market_comparison(
    num_agents: int = DEFAULT_NUM_AGENTS,
    max_steps: int = DEFAULT_MAX_STEPS,
    output_dir: str = "results",
) -> pd.DataFrame:
    """Dark platform (mixed_exploitative) vs clean (clean_competitor).

    Same seed per replication pair, 5 replications.  Generates side-by-side
    trust/reputation/economics plots.
    """
    out = _make_output_dir(output_dir, "market_comparison")
    rows: list[dict] = []

    for rep in range(NUM_REPLICATIONS):
        seed = rep * 1000
        print(f"  Market comparison  rep {rep + 1}/{NUM_REPLICATIONS}")

        _, dark_data = _run_model("mixed_exploitative", num_agents, max_steps, seed=seed)
        _, clean_data = _run_model("clean_competitor", num_agents, max_steps, seed=seed)

        comp = compare_platforms(dark_data, clean_data)

        dark_row = comp["dark_summary"].copy()
        dark_row["platform"] = "dark"
        dark_row["replication"] = rep
        dark_row["crossover_step"] = comp["crossover_step"]
        rows.append(dark_row)

        clean_row = comp["clean_summary"].copy()
        clean_row["platform"] = "clean"
        clean_row["replication"] = rep
        clean_row["crossover_step"] = comp["crossover_step"]
        rows.append(clean_row)

    # Save CSV
    df = pd.DataFrame(rows)
    csv_path = os.path.join(out, "market_comparison.csv")
    df.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")

    # Side-by-side plots for last replication
    _plot_market_comparison(dark_data, clean_data, out)
    return df


def _plot_market_comparison(
    dark_data: pd.DataFrame, clean_data: pd.DataFrame, output_dir: str
) -> None:
    """Side-by-side trust, reputation, and economics for dark vs clean."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Market Comparison: Dark vs Clean", fontsize=14, fontweight="bold")

    # Trust
    ax = axes[0]
    ax.plot(dark_data.index, dark_data["mean_trust"], label="Dark", color="red",
            linewidth=2)
    ax.plot(clean_data.index, clean_data["mean_trust"], label="Clean", color="green",
            linewidth=2)
    ax.set_title("Mean Trust (Active)")
    ax.set_xlabel("Step")
    ax.set_ylabel("Trust")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Reputation
    ax = axes[1]
    ax.plot(dark_data.index, dark_data["platform_reputation"], label="Dark",
            color="red", linewidth=2)
    ax.plot(clean_data.index, clean_data["platform_reputation"], label="Clean",
            color="green", linewidth=2)
    ax.set_title("Platform Reputation")
    ax.set_xlabel("Step")
    ax.set_ylabel("Reputation")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Net value
    ax = axes[2]
    ax.plot(dark_data.index, dark_data["net_value"], label="Dark", color="red",
            linewidth=2)
    ax.plot(clean_data.index, clean_data["net_value"], label="Clean", color="green",
            linewidth=2)
    ax.set_title("Cumulative Net Value")
    ax.set_xlabel("Step")
    ax.set_ylabel("Net value")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(os.path.join(output_dir, "market_comparison.png"), dpi=150)
    plt.close(fig)


# ============================================================================
# Experiment 4 — Network topology comparison
# ============================================================================

def experiment_network_topology(
    num_agents: int = DEFAULT_NUM_AGENTS,
    max_steps: int = DEFAULT_MAX_STEPS,
    output_dir: str = "results",
) -> pd.DataFrame:
    """Run mixed_exploitative on small_world, scale_free, random.

    5 replications per topology.  Compare WOM spread and tipping points.
    """
    out = _make_output_dir(output_dir, "network_topology")
    rows: list[dict] = []
    topologies = ["small_world", "scale_free", "random"]

    for topo in topologies:
        for rep in range(NUM_REPLICATIONS):
            seed = rep * 1000
            print(f"  Topology '{topo}'  rep {rep + 1}/{NUM_REPLICATIONS}")
            _, data = _run_model(
                "mixed_exploitative", num_agents, max_steps, seed=seed,
                network_type=topo,
            )
            summary = compute_summary_statistics(data)
            tp = detect_tipping_point(data)
            summary["network_type"] = topo
            summary["replication"] = rep
            summary["tipping_point_step"] = tp["tipping_point_step"]
            summary["trigger_rule"] = tp["trigger_rule"]
            rows.append(summary)

    df = pd.DataFrame(rows)
    csv_path = os.path.join(out, "network_topology.csv")
    df.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")

    # Comparison plot
    _plot_topology_comparison(df, out)
    return df


def _plot_topology_comparison(df: pd.DataFrame, output_dir: str) -> None:
    """Bar charts comparing WOM spread and tipping points across topologies."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Network Topology Comparison", fontsize=14, fontweight="bold")
    grouped = df.groupby("network_type")

    # Negative WOM
    ax = axes[0]
    means = grouped["total_negative_wom"].mean()
    stds = grouped["total_negative_wom"].std()
    means.plot.bar(ax=ax, yerr=stds, capsize=3, color="salmon", alpha=0.8)
    ax.set_title("Total Negative WOM")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(True, alpha=0.3)

    # Tipping point step
    ax = axes[1]
    tp_df = df[df["tipping_point_step"].notna()]
    if not tp_df.empty:
        tp_grouped = tp_df.groupby("network_type")
        means = tp_grouped["tipping_point_step"].mean()
        stds = tp_grouped["tipping_point_step"].std()
        means.plot.bar(ax=ax, yerr=stds, capsize=3, color="goldenrod", alpha=0.8)
    ax.set_title("Mean Tipping Point Step")
    ax.set_ylabel("Step")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(True, alpha=0.3)

    # Final trust
    ax = axes[2]
    means = grouped["final_avg_trust_active"].mean()
    stds = grouped["final_avg_trust_active"].std()
    means.plot.bar(ax=ax, yerr=stds, capsize=3, color="steelblue", alpha=0.8)
    ax.set_title("Final Avg Trust (Active)")
    ax.set_ylabel("Trust")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(os.path.join(output_dir, "network_topology.png"), dpi=150)
    plt.close(fig)


# ============================================================================
# CLI entry point
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch experiments for the Dark Patterns ABM.",
    )
    parser.add_argument(
        "--experiment",
        type=int,
        default=0,
        choices=[0, 1, 2, 3, 4],
        help="Experiment to run: 0=all, 1=intensity sweep, 2=scenario comparison, "
             "3=market comparison, 4=network topology.",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=DEFAULT_NUM_AGENTS,
        help=f"Number of user agents (default: {DEFAULT_NUM_AGENTS}).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        help=f"Number of simulation steps (default: {DEFAULT_MAX_STEPS}).",
    )
    args = parser.parse_args()

    output_dir = make_timestamped_dir()
    print(f"Output directory: {output_dir}")

    experiments = {
        1: ("Intensity Sweep", experiment_intensity_sweep),
        2: ("Scenario Comparison", experiment_scenario_comparison),
        3: ("Market Comparison", experiment_market_comparison),
        4: ("Network Topology", experiment_network_topology),
    }

    to_run = experiments if args.experiment == 0 else {args.experiment: experiments[args.experiment]}

    for num, (label, func) in to_run.items():
        print(f"\n{'=' * 60}")
        print(f"  Experiment {num}: {label}")
        print(f"{'=' * 60}")
        func(num_agents=args.agents, max_steps=args.steps, output_dir=output_dir)

    print(f"\nAll experiments complete. Results in: {output_dir}")


if __name__ == "__main__":
    main()
