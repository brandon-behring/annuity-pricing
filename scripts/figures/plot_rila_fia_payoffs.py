"""
Generate RILA and FIA payoff diagrams.

Outputs:
    - paper/figures/payoff_buffer_floor_cap.pdf
    - paper/figures/data/payoff_scenarios.csv
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from annuity_pricing.options.payoffs.rila import BufferPayoff, FloorPayoff
from annuity_pricing.options.payoffs.fia import CappedCallPayoff


def main():
    """Generate and save payoff diagrams."""

    # Create output directories
    paper_dir = Path(__file__).parent.parent.parent / "paper"
    figures_dir = paper_dir / "figures"
    data_dir = figures_dir / "data"

    figures_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Define index return scenarios (percentage returns)
    index_returns = np.linspace(-0.30, 0.30, 101)

    # Define payoff scenarios
    scenarios = {
        "Buffer 10%": {
            "payoff": BufferPayoff(buffer_rate=0.10, cap_rate=0.12),
            "description": "RILA with 10% buffer, 12% cap"
        },
        "Floor -10%": {
            "payoff": FloorPayoff(floor_rate=-0.10, cap_rate=0.12),
            "description": "RILA with -10% floor, 12% cap"
        },
        "FIA Capped": {
            "payoff": CappedCallPayoff(cap_rate=0.08, floor_rate=0.0),
            "description": "FIA with 8% cap, 0% floor"
        },
    }

    # Calculate payoffs
    results = {"Index Return (%)": index_returns * 100}

    for name, config in scenarios.items():
        payoff = config["payoff"]
        credited_returns = np.array([
            payoff.calculate(r).credited_return
            for r in index_returns
        ])
        results[name] = credited_returns * 100

    # Create DataFrame and save CSV
    df = pd.DataFrame(results)
    csv_path = data_dir / "payoff_scenarios.csv"
    df.to_csv(csv_path, index=False)
    print(f"✓ Saved payoff data to {csv_path}")

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot breakeven line
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.3, label='Breakeven')
    ax.axvline(x=0, color='black', linestyle='--', linewidth=0.8, alpha=0.3)

    # Plot payoff lines
    colors = {'Buffer 10%': '#1f77b4', 'Floor -10%': '#ff7f0e', 'FIA Capped': '#2ca02c'}
    linestyles = {'Buffer 10%': '-', 'Floor -10%': '-', 'FIA Capped': '-'}
    linewidths = {'Buffer 10%': 2.5, 'Floor -10%': 2.5, 'FIA Capped': 2.5}

    for name in scenarios.keys():
        ax.plot(
            results["Index Return (%)"],
            results[name],
            label=f"{name} – {scenarios[name]['description']}",
            color=colors[name],
            linestyle=linestyles[name],
            linewidth=linewidths[name],
            alpha=0.8
        )

    # Annotations for key points
    # Buffer: point at -15% index return
    buffer_payoff = BufferPayoff(buffer_rate=0.10, cap_rate=0.12)
    buffer_value = buffer_payoff.calculate(-0.15).credited_return * 100
    ax.plot(-15, buffer_value, 'o', color='#1f77b4', markersize=8)
    ax.annotate(
        f'Buffer absorbs\nfirst 10% loss',
        xy=(-15, buffer_value),
        xytext=(-18, buffer_value - 3),
        fontsize=9,
        ha='right',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#1f77b4', alpha=0.2),
        arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=1)
    )

    # Cap: point at +30% index return
    cap_payoff = CappedCallPayoff(cap_rate=0.08, floor_rate=0.0)
    cap_value = cap_payoff.calculate(0.30).credited_return * 100
    ax.plot(30, cap_value, 'o', color='#2ca02c', markersize=8)
    ax.annotate(
        f'Return capped\nat 8%',
        xy=(30, cap_value),
        xytext=(24, cap_value + 2),
        fontsize=9,
        ha='right',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#2ca02c', alpha=0.2),
        arrowprops=dict(arrowstyle='->', color='#2ca02c', lw=1)
    )

    ax.set_xlabel('Index Return (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Credited Return to Annuitant (%)', fontsize=12, fontweight='bold')
    ax.set_title('RILA and FIA Payoff Diagrams\nBuffer, Floor, and Cap Mechanics',
                 fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.legend(loc='upper left', fontsize=10, framealpha=0.95)
    ax.set_xlim(-35, 35)
    ax.set_ylim(-15, 12)

    # Save figure
    pdf_path = figures_dir / "payoff_buffer_floor_cap.pdf"
    fig.tight_layout()
    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved payoff diagram to {pdf_path}")

    plt.close(fig)


if __name__ == "__main__":
    main()
