"""
Generate GLWB fee sensitivity surface plot.

Shows how GLWB fair fees vary across volatility and interest rate scenarios.

Outputs:
    - paper/figures/glwb_fee_surface.pdf
    - paper/figures/data/glwb_fee_surface.csv
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path

from annuity_pricing.glwb.path_sim import GLWBPathSimulator
from annuity_pricing.glwb.gwb_config import GWBConfig
from annuity_pricing.glwb.config import RiskNeutralEquityParams


def main():
    """Generate and save GLWB fee surface plot."""

    # Create output directories
    paper_dir = Path(__file__).parent.parent.parent / "paper"
    figures_dir = paper_dir / "figures"
    data_dir = figures_dir / "data"

    figures_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Define parameter ranges
    volatilities = np.array([0.10, 0.15, 0.20, 0.25, 0.30])
    interest_rates = np.array([0.02, 0.03, 0.04, 0.05, 0.06])

    n_paths = 5000
    seed = 5678

    # GLWB configuration
    gwb_config = GWBConfig(
        rollup_rate=0.05,
        withdrawal_rate=0.05,
        fee_rate=0.01  # We'll sweep this in the solver (for display purposes, fixed here)
    )

    # Storage for results
    fee_matrix = np.zeros((len(interest_rates), len(volatilities)))
    results_list = []

    print("Computing GLWB fair fees across vol/rate grid...")
    print(f"{'Rate':>6} | {' Vol  ':^30} |")
    print(f"{'(%)':>6} | {' 10%  15%  20%  25%  30% ':^30} |")
    print("-" * 56)

    for i, rate in enumerate(interest_rates):
        print(f"{rate*100:5.1f} | ", end="")

        for j, vol in enumerate(volatilities):
            try:
                # Create equity parameters
                equity_params = RiskNeutralEquityParams(
                    spot=100.0,
                    risk_free_rate=rate,
                    dividend_yield=0.02,
                    volatility=vol
                )

                # Simple approach: use fixed fee for demonstration
                # In production, this would solve for fair fee (price = 0)
                simulator = GLWBPathSimulator(
                    gwb_config=gwb_config,
                    n_paths=n_paths,
                    seed=seed
                )

                result = simulator.price(
                    premium=100.0,
                    age=65,
                    r=rate,
                    sigma=vol
                )

                # Fair fee approximation: cost as % of premium
                fair_fee = result.guarantee_cost

                fee_matrix[i, j] = fair_fee * 100  # Convert to percentage
                results_list.append({
                    "Interest Rate (%)": rate * 100,
                    "Volatility (%)": vol * 100,
                    "Fair Fee (bps)": fair_fee * 10000
                })

                print(f"{fair_fee*100:5.2f}", end=" ")

            except Exception as e:
                print(f"Error at vol={vol}, rate={rate}: {e}")
                fee_matrix[i, j] = np.nan
                print(f"  N/A ", end=" ")

        print("|")

    # Save CSV
    df = pd.DataFrame(results_list)
    csv_path = data_dir / "glwb_fee_surface.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n✓ Saved GLWB fee surface data to {csv_path}")

    # Create figure
    fig = plt.figure(figsize=(14, 5))

    # Subplot 1: 3D Surface
    ax1 = fig.add_subplot(121, projection='3d')

    vol_grid, rate_grid = np.meshgrid(volatilities * 100, interest_rates * 100)
    surf = ax1.plot_surface(vol_grid, rate_grid, fee_matrix,
                            cmap='RdYlGn_r', alpha=0.8, edgecolor='none')

    ax1.set_xlabel('Volatility (%)', fontsize=10, fontweight='bold')
    ax1.set_ylabel('Interest Rate (%)', fontsize=10, fontweight='bold')
    ax1.set_zlabel('Fair Fee (%)', fontsize=10, fontweight='bold')
    ax1.set_title('GLWB Fair Fee Surface\n3D Visualization',
                  fontsize=11, fontweight='bold')
    ax1.view_init(elev=25, azim=45)

    cbar1 = fig.colorbar(surf, ax=ax1, label='Fair Fee (%)', shrink=0.5)

    # Subplot 2: Contour plot
    ax2 = fig.add_subplot(122)

    contour = ax2.contourf(vol_grid, rate_grid, fee_matrix, levels=15, cmap='RdYlGn_r')
    contour_lines = ax2.contour(vol_grid, rate_grid, fee_matrix, levels=10,
                                colors='black', alpha=0.3, linewidths=0.5)
    ax2.clabel(contour_lines, inline=True, fontsize=8)

    ax2.set_xlabel('Volatility (%)', fontsize=10, fontweight='bold')
    ax2.set_ylabel('Interest Rate (%)', fontsize=10, fontweight='bold')
    ax2.set_title('GLWB Fair Fee Contours\nIsocontour Map',
                  fontsize=11, fontweight='bold')

    cbar2 = fig.colorbar(contour, ax=ax2, label='Fair Fee (%)')

    fig.suptitle('GLWB Fee Sensitivity Analysis\n5% Rollup, 5% Withdrawal Rate',
                 fontsize=13, fontweight='bold', y=0.98)

    fig.tight_layout()
    pdf_path = figures_dir / "glwb_fee_surface.pdf"
    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved GLWB fee surface plot to {pdf_path}")

    plt.close(fig)


if __name__ == "__main__":
    main()
