"""
Generate Monte Carlo convergence plot.

Demonstrates convergence of Monte Carlo pricing to Black-Scholes analytical
price as path count increases.

Outputs:
    - paper/figures/mc_convergence.pdf
    - paper/figures/data/mc_convergence.csv
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from annuity_pricing.options.pricing.black_scholes import black_scholes_call
from annuity_pricing.options.simulation.monte_carlo import MonteCarloEngine
from annuity_pricing.options.simulation.gbm import GBMParams


def main():
    """Generate and save MC convergence plot."""

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
    seed = 1234

    # Analytical Black-Scholes price
    bs_price = black_scholes_call(
        spot=spot,
        strike=strike,
        rate=rate,
        dividend=dividend,
        volatility=volatility,
        time_to_expiry=time_to_expiry
    )

    # Monte Carlo with varying path counts
    path_counts = [100, 500, 1000, 5000, 10000, 50000, 100000]
    mc_prices = []
    mc_errors = []

    engine = MonteCarloEngine(n_paths=1, seed=seed)  # Will override n_paths per iteration
    params = GBMParams(
        spot=spot,
        rate=rate,
        dividend=dividend,
        volatility=volatility,
        time_to_expiry=time_to_expiry
    )

    for n_paths in path_counts:
        engine = MonteCarloEngine(n_paths=n_paths, seed=seed)
        result = engine.price_european_call(params, strike=strike)

        mc_prices.append(result.price)
        # Relative error in percentage
        rel_error = abs(result.price - bs_price) / bs_price * 100
        mc_errors.append(rel_error)

        print(f"N={n_paths:6d}: MC=${result.price:.4f} | BS=${bs_price:.4f} | Error={rel_error:.3f}%")

    # Create DataFrame and save CSV
    df = pd.DataFrame({
        "Path Count": path_counts,
        "MC Price": mc_prices,
        "BS Price": [bs_price] * len(path_counts),
        "Relative Error (%)": mc_errors
    })

    csv_path = data_dir / "mc_convergence.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n✓ Saved MC convergence data to {csv_path}")

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Subplot 1: MC price vs path count
    ax1.semilogx(path_counts, mc_prices, 'o-', linewidth=2, markersize=8,
                 label='Monte Carlo Price', color='#1f77b4')
    ax1.axhline(y=bs_price, color='#ff7f0e', linestyle='--', linewidth=2,
                label=f'Black-Scholes Price = ${bs_price:.4f}')
    ax1.fill_between(path_counts, bs_price * 0.99, bs_price * 1.01,
                     alpha=0.2, color='#ff7f0e', label='±1% tolerance')
    ax1.set_xlabel('Number of Paths', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Call Price ($)', fontsize=11, fontweight='bold')
    ax1.set_title('Monte Carlo Price Convergence\nEuropean Call: S=K=100, T=1yr, σ=20%',
                  fontsize=12, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3, which='both')

    # Subplot 2: Relative error vs path count
    ax2.loglog(path_counts, mc_errors, 'o-', linewidth=2, markersize=8,
               color='#d62728', label='Relative Error')

    # Theoretical O(N^-0.5) convergence line
    theory_line = np.array(mc_errors[0]) * np.sqrt(path_counts[0] / np.array(path_counts))
    ax2.loglog(path_counts, theory_line, '--', linewidth=2, color='#2ca02c',
               label=r'Theoretical: $O(N^{-1/2})$')

    ax2.set_xlabel('Number of Paths (log scale)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Relative Error (%, log scale)', fontsize=11, fontweight='bold')
    ax2.set_title('Convergence Rate Analysis\nMonte Carlo Error Decay',
                  fontsize=12, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3, which='both')

    # Save figure
    pdf_path = figures_dir / "mc_convergence.pdf"
    fig.tight_layout()
    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved MC convergence plot to {pdf_path}")

    plt.close(fig)


if __name__ == "__main__":
    main()
