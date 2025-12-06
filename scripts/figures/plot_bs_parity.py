"""
Generate Black-Scholes parity validation plot.

Compares our BS implementation against financepy for prices and Greeks.

Outputs:
    - paper/figures/bs_financepy_parity.pdf
    - paper/figures/data/bs_parity.csv
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from annuity_pricing.options.pricing.black_scholes import black_scholes_greeks
from annuity_pricing.options.payoffs.base import OptionType
from annuity_pricing.adapters.financepy_adapter import FinancepyAdapter


def main():
    """Generate and save BS parity validation plot."""

    # Create output directories
    paper_dir = Path(__file__).parent.parent.parent / "paper"
    figures_dir = paper_dir / "figures"
    data_dir = figures_dir / "data"

    figures_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Test parameters
    spot = 100.0
    strike = 100.0
    rate = 0.05
    dividend = 0.02
    volatility = 0.20
    time_to_expiry = 1.0

    # Compute using our implementation
    our_result = black_scholes_greeks(
        spot=spot,
        strike=strike,
        rate=rate,
        dividend=dividend,
        volatility=volatility,
        time_to_expiry=time_to_expiry,
        option_type=OptionType.CALL
    )

    # Compute using FinancePy
    try:
        adapter = FinancepyAdapter()
        fp_raw = adapter.price_call_with_greeks(
            spot=spot,
            strike=strike,
            rate=rate,
            dividend=dividend,
            volatility=volatility,
            time_to_expiry=time_to_expiry
        )
        # Scale to match our units: vega per 1% vol, theta per day, rho per 1% rate
        fp_result = {
            "price": fp_raw["price"],
            "delta": fp_raw["delta"],
            "gamma": fp_raw["gamma"],
            "vega": fp_raw["vega"] / 100.0,
            "theta": fp_raw["theta"] / 365.0,
            "rho": fp_raw["rho"] / 100.0,
        }
        has_financepy = True
    except ImportError:
        print("⚠ FinancePy not installed; skipping cross-validation")
        has_financepy = False
        fp_result = None

    # Create comparison data
    data = {
        "Metric": ["Price", "Delta", "Gamma", "Vega (per 1%)", "Theta (per day)", "Rho (per 1%)"],
        "Our Implementation": [
            our_result.price,
            our_result.delta,
            our_result.gamma,
            our_result.vega,
            our_result.theta,
            our_result.rho
        ]
    }

    if has_financepy and fp_result:
        data["FinancePy"] = [
            fp_result["price"],
            fp_result["delta"],
            fp_result["gamma"],
            fp_result["vega"],
            fp_result["theta"],
            fp_result["rho"]
        ]
        data["Difference (%)"] = [
            abs(data["Our Implementation"][i] - data["FinancePy"][i]) / abs(data["FinancePy"][i]) * 100
            for i in range(len(data["Metric"]))
        ]
    else:
        data["FinancePy"] = [np.nan] * len(data["Metric"])
        data["Difference (%)"] = [np.nan] * len(data["Metric"])

    df = pd.DataFrame(data)
    csv_path = data_dir / "bs_parity.csv"
    df.to_csv(csv_path, index=False)
    print(f"✓ Saved BS parity data to {csv_path}")

    # Print comparison table
    print("\n" + "="*70)
    print("Black-Scholes Parity Validation")
    print("="*70)
    print(df.to_string(index=False))
    print("="*70 + "\n")

    if not has_financepy or fp_result is None:
        print("✓ Created data file (FinancePy cross-validation skipped)")
        return

    # Create figure with Greeks comparison
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    metrics = ["Price ($)", "Delta", "Gamma", "Vega (per 1%)", "Theta (per day)", "Rho (per 1%)"]
    our_values = data["Our Implementation"]
    fp_values = data["FinancePy"]
    differences = data["Difference (%)"]

    for idx, (metric, our_val, fp_val, diff) in enumerate(
        zip(metrics, our_values, fp_values, differences)
    ):
        ax = axes[idx]

        # Bar chart comparing implementations
        x_pos = np.arange(2)
        values = [our_val, fp_val]
        colors = ['#1f77b4', '#ff7f0e']

        bars = ax.bar(x_pos, values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

        # Add value labels on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.4f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(['annuity-pricing', 'FinancePy'], fontsize=10)
        ax.set_ylabel(metric, fontsize=11, fontweight='bold')
        ax.set_title(f"{metric}\nDifference: {diff:.3f}%", fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        # Add tolerance band
        tolerance = 0.01  # 1% tolerance
        if abs(diff) < tolerance:
            ax.text(0.5, 0.95, '✓ Within tolerance',
                   transform=ax.transAxes,
                   ha='center', va='top',
                   fontsize=10, fontweight='bold', color='green',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7))
        else:
            ax.text(0.5, 0.95, f'⚠ Outside {tolerance*100:.1f}% tolerance',
                   transform=ax.transAxes,
                   ha='center', va='top',
                   fontsize=10, fontweight='bold', color='red',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.7))

    fig.suptitle(
        f'Black-Scholes Validation: annuity-pricing vs FinancePy\n'
        f'S={spot}, K={strike}, r={rate:.2%}, q={dividend:.2%}, σ={volatility:.1%}, T={time_to_expiry}yr',
        fontsize=14, fontweight='bold', y=1.00
    )

    fig.tight_layout()
    pdf_path = figures_dir / "bs_financepy_parity.pdf"
    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved BS parity plot to {pdf_path}")

    plt.close(fig)


if __name__ == "__main__":
    main()
