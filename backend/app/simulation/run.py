"""
Run a single scenario and produce visualization + console output.

Usage:
    python -m app.simulation.run                          # default: mixed_exploitative
    python -m app.simulation.run --scenario control       # specific scenario
    python -m app.simulation.run --steps 50               # custom step count
    python -m app.simulation.run --agents 200             # custom agent count
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.simulation.config import SCENARIOS, DEFAULT_MAX_STEPS, DEFAULT_NUM_AGENTS
from app.simulation.model import DarkPatternTrustModel
from app.simulation.analysis import detect_tipping_point, compute_summary_statistics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_timestamped_dir(base: str = "results") -> str:
    """Create and return a timestamped results subdirectory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(base, timestamp)
    os.makedirs(path, exist_ok=True)
    return path


def run_scenario(
    scenario_name: str,
    num_agents: int = DEFAULT_NUM_AGENTS,
    max_steps: int = DEFAULT_MAX_STEPS,
    seed: int | None = None,
):
    """Run a named scenario and return (model, datacollector DataFrame).

    Parameters
    ----------
    scenario_name : str
        Key into ``SCENARIOS`` dict from config.py.
    num_agents : int
        Number of user agents.
    max_steps : int
        Maximum simulation steps.
    seed : int | None
        Random seed for reproducibility.

    Returns
    -------
    tuple[DarkPatternTrustModel, pd.DataFrame]
    """
    scenario = SCENARIOS[scenario_name]
    model = DarkPatternTrustModel(
        num_users=num_agents,
        seed=seed,
        max_steps=max_steps,
        dark_pattern_intensity=scenario["dark_pattern_intensity"],
        pattern_forced_trial=scenario["patterns"]["forced_trial"],
        pattern_hard_cancel=scenario["patterns"]["hard_cancel"],
        pattern_drip_pricing=scenario["patterns"]["drip_pricing"],
        adaptive_platform=scenario["adaptive_platform"],
        customer_support_quality=scenario["customer_support_quality"],
    )
    for _ in range(max_steps):
        model.step()
    data = model.datacollector.get_model_vars_dataframe()
    return model, data


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_results(data, scenario_name: str, tipping_point_step, output_dir: str) -> str:
    """Create a 6-subplot figure and save as PNG.

    Subplots:
        1. Trust over time (active mean, all mean, per-type)
        2. Active users
        3. WOM (negative + positive per step)
        4. Cumulative churn by user type
        5. Platform reputation
        6. Per-step economics (revenue, costs, profit)

    Returns the path of the saved PNG.
    """
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    fig.suptitle(f"Scenario: {scenario_name}", fontsize=15, fontweight="bold")
    steps = data.index

    def _add_tipping_line(ax):
        if tipping_point_step is not None:
            ax.axvline(x=tipping_point_step, color="red", linestyle="--",
                       linewidth=1, alpha=0.7, label="Tipping point")

    # ── 1. Trust over time ────────────────────────────────────────────
    ax = axes[0, 0]
    ax.plot(steps, data["mean_trust"], label="Mean trust (active)", linewidth=2)
    ax.plot(steps, data["mean_trust_all"], label="Mean trust (all)", linewidth=1.5,
            linestyle="--")
    for utype, color in [("skeptic", "orange"), ("naive", "green"), ("activist", "purple")]:
        col = f"trust_{utype}"
        if col in data.columns:
            ax.plot(steps, data[col], label=f"Avg trust ({utype})",
                    linewidth=1, alpha=0.7, color=color)
    _add_tipping_line(ax)
    ax.set_title("Trust Over Time")
    ax.set_xlabel("Step")
    ax.set_ylabel("Trust")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # ── 2. Active users ───────────────────────────────────────────────
    ax = axes[0, 1]
    ax.plot(steps, data["active_users"], color="steelblue", linewidth=2)
    _add_tipping_line(ax)
    ax.set_title("Active Users Over Time")
    ax.set_xlabel("Step")
    ax.set_ylabel("Active users")
    ax.grid(True, alpha=0.3)

    # ── 3. WOM ────────────────────────────────────────────────────────
    ax = axes[1, 0]
    ax.bar(steps, data["step_negative_wom_count"], color="salmon", alpha=0.7,
           label="Negative WOM")
    ax.bar(steps, data["step_positive_wom_count"], color="mediumseagreen", alpha=0.7,
           label="Positive WOM")
    _add_tipping_line(ax)
    ax.set_title("Word-of-Mouth per Step")
    ax.set_xlabel("Step")
    ax.set_ylabel("WOM count")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 4. Cumulative churn by user type ──────────────────────────────
    ax = axes[1, 1]
    for utype, color in [("skeptic", "orange"), ("naive", "green"), ("activist", "purple")]:
        col = f"churned_{utype}"
        if col in data.columns:
            ax.plot(steps, data[col], label=f"Churn ({utype})",
                    linewidth=1.5, color=color)
    _add_tipping_line(ax)
    ax.set_title("Cumulative Churn by User Type")
    ax.set_xlabel("Step")
    ax.set_ylabel("Churned count")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── 5. Platform reputation ────────────────────────────────────────
    ax = axes[2, 0]
    ax.plot(steps, data["platform_reputation"], color="goldenrod", linewidth=2)
    _add_tipping_line(ax)
    ax.set_title("Platform Reputation")
    ax.set_xlabel("Step")
    ax.set_ylabel("Reputation (0-100)")
    ax.grid(True, alpha=0.3)

    # ── 6. Per-step economics ─────────────────────────────────────────
    ax = axes[2, 1]
    ax.plot(steps, data["step_revenue"], label="Revenue", color="green", linewidth=1.5)
    ax.plot(steps, data["step_costs"], label="Costs", color="red", linewidth=1.5)
    ax.plot(steps, data["step_profit"], label="Profit", color="blue", linewidth=2)
    _add_tipping_line(ax)
    ax.set_title("Per-Step Economics")
    ax.set_xlabel("Step")
    ax.set_ylabel("Value")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    png_path = os.path.join(output_dir, f"{scenario_name}.png")
    fig.savefig(png_path, dpi=150)
    plt.close(fig)
    return png_path


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def print_summary(data, scenario_name: str, tipping_result: dict) -> None:
    """Print a human-readable summary to stdout."""
    summary = compute_summary_statistics(data)

    print("\n" + "=" * 60)
    print(f"  Scenario: {scenario_name}")
    print("=" * 60)

    print(f"  Steps run:               {summary['steps_run']}")
    print(f"  Final active users:      {summary['final_active_users']}")
    print(f"  Final avg trust (active): {summary['final_avg_trust_active']:.4f}")
    print(f"  Final avg trust (all):    {summary['final_avg_trust_all']:.4f}")
    print(f"  Total churn:             {summary['total_churn']}")
    print(f"  Final churn rate:        {summary['final_churn_rate']:.4f}")
    print(f"  Total negative WOM:      {summary['total_negative_wom']}")
    print(f"  Total positive WOM:      {summary['total_positive_wom']}")
    print(f"  Final reputation:        {summary['final_reputation']:.2f}")
    print(f"  Net value:               {summary['final_net_value']:.2f}")
    print(f"  Cumulative revenue:      {summary['final_cumulative_revenue']:.2f}")
    print(f"  Cumulative costs:        {summary['final_cumulative_costs']:.2f}")

    tp_step = tipping_result["tipping_point_step"]
    if tp_step is not None:
        print(f"\n  Tipping point at step:   {tp_step}")
        print(f"  Trigger rule:            {tipping_result['trigger_rule']}")
        diag = tipping_result["diagnostics"]
        print(f"  Trust at tipping:        {diag['trust_at_tipping']:.4f}")
        print(f"  Active users at tipping: {diag['active_users_at_tipping']}")
    else:
        print("\n  No tipping point detected.")

    if tipping_result["all_triggers"]:
        print("\n  All triggered rules:")
        for t in tipping_result["all_triggers"]:
            print(f"    - {t['rule']} at step {t['step']}")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a single Dark-Matters ABM scenario.",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="mixed_exploitative",
        choices=list(SCENARIOS.keys()),
        help="Scenario preset name (default: mixed_exploitative).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        help=f"Number of simulation steps (default: {DEFAULT_MAX_STEPS}).",
    )
    parser.add_argument(
        "--agents",
        type=int,
        default=DEFAULT_NUM_AGENTS,
        help=f"Number of user agents (default: {DEFAULT_NUM_AGENTS}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: results/<timestamp>).",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or make_timestamped_dir()
    print(f"Output directory: {output_dir}")

    print(f"Running scenario '{args.scenario}' with {args.agents} agents "
          f"for {args.steps} steps (seed={args.seed})...")
    model, data = run_scenario(args.scenario, args.agents, args.steps, args.seed)

    tipping_result = detect_tipping_point(data)
    tp_step = tipping_result["tipping_point_step"]

    png_path = plot_results(data, args.scenario, tp_step, output_dir)
    print(f"Plot saved to: {png_path}")

    csv_path = os.path.join(output_dir, f"{args.scenario}.csv")
    data.to_csv(csv_path)
    print(f"Data saved to: {csv_path}")

    print_summary(data, args.scenario, tipping_result)


if __name__ == "__main__":
    main()
