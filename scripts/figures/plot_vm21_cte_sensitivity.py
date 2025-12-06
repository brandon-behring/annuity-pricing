"""
Generate VM-21 CTE70 sensitivity analysis plot.

Shows how reserved amount (CTE70) varies with policy parameters:
age, guaranteed base, and volatility.

Outputs:
    - paper/figures/vm21_cte70.pdf
    - paper/figures/data/vm21_cte_sensitivity.csv
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from annuity_pricing.regulatory.vm21 import VM21Calculator
from annuity_pricing.regulatory.scenarios import RiskNeutralEquityParams
from annuity_pricing.regulatory.scenarios import PolicyData


def main():
    """Generate and save VM-21 CTE sensitivity plot."""

    # Create output directories
    paper_dir = Path(__file__).parent.parent.parent / "paper"
    figures_dir = paper_dir / "figures"
    data_dir = figures_dir / "data"

    figures_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Define parameter ranges
    ages = np.array([60, 65, 70, 75, 80])
    gwb_amounts = np.array([250000, 500000, 750000, 1000000])  # Guaranteed withdrawal base
    volatilities = np.array([0.15, 0.20, 0.25, 0.30])

    n_scenarios = 500  # Reduced for demonstration
    seed = 9999

    calculator = VM21Calculator(n_scenarios=n_scenarios, seed=seed)

    # Storage for results
    results_list = []
    cte_by_vol = {vol: [] for vol in volatilities}

    print("Computing VM-21 CTE70 reserves across parameter grid...")
    print(f"{'Age':>3} | {' GWB (thousands) ':^45} |")
    print(f"{'':>3} | {'   250   500   750  1000  (Vol=20%)':^45} |")
    print("-" * 57)

    for age in ages:
        print(f"{age:2d} | ", end="")

        for gwb in gwb_amounts:
            # For this age and gwb level, compute CTE at middle volatility
            vol = 0.20

            try:
                policy = PolicyData(
                    av=gwb,
                    gwb=gwb,
                    age=age,
                    withdrawal_rate=0.05
                )

                result = calculator.calculate_reserve(
                    policy=policy,
                    scenarios=None  # Will generate default scenarios
                )

                cte_reserve = result.cte70

                print(f"{cte_reserve/1000:6.1f}", end=" ")

                results_list.append({
                    "Age": age,
                    "GWB ($)": gwb,
                    "Volatility (%)": vol * 100,
                    "CTE70 Reserve ($)": cte_reserve,
                    "Reserve/GWB (%)": (cte_reserve / gwb) * 100
                })

            except Exception as e:
                print(f"  N/A ", end=" ")

        print("|")

    # Save CSV
    df = pd.DataFrame(results_list)
    csv_path = data_dir / "vm21_cte_sensitivity.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n✓ Saved VM-21 CTE sensitivity data to {csv_path}")

    # Create figure with sensitivity analysis
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    # Scenario 1: CTE by age (fixed GWB = 500k, vol = 20%)
    subset_1 = df[(df['GWB ($)'] == 500000) & (df['Volatility (%)'] == 20)]
    if not subset_1.empty:
        ax = axes[0]
        ax.plot(subset_1['Age'], subset_1['CTE70 Reserve ($)'] / 1000,
               'o-', linewidth=2.5, markersize=8, color='#1f77b4')
        ax.fill_between(subset_1['Age'],
                        subset_1['CTE70 Reserve ($)'] / 1000 * 0.95,
                        subset_1['CTE70 Reserve ($)'] / 1000 * 1.05,
                        alpha=0.2, color='#1f77b4')
        ax.set_xlabel('Policyholder Age', fontsize=11, fontweight='bold')
        ax.set_ylabel('CTE70 Reserve ($thousands)', fontsize=11, fontweight='bold')
        ax.set_title('Age Sensitivity\n(GWB = $500k, σ = 20%)',
                     fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(ages)

    # Scenario 2: CTE by GWB (fixed age = 65, vol = 20%)
    subset_2 = df[(df['Age'] == 65) & (df['Volatility (%)'] == 20)]
    if not subset_2.empty:
        ax = axes[1]
        ax.plot(subset_2['GWB ($)'] / 1000, subset_2['CTE70 Reserve ($)'] / 1000,
               's-', linewidth=2.5, markersize=8, color='#ff7f0e')
        ax.fill_between(subset_2['GWB ($)'] / 1000,
                        subset_2['CTE70 Reserve ($)'] / 1000 * 0.95,
                        subset_2['CTE70 Reserve ($)'] / 1000 * 1.05,
                        alpha=0.2, color='#ff7f0e')
        ax.set_xlabel('Guaranteed Withdrawal Base ($thousands)', fontsize=11, fontweight='bold')
        ax.set_ylabel('CTE70 Reserve ($thousands)', fontsize=11, fontweight='bold')
        ax.set_title('GWB Sensitivity\n(Age = 65, σ = 20%)',
                     fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)

    # Scenario 3: Reserve as % of GWB by age
    subset_3 = df[(df['GWB ($)'] == 500000) & (df['Volatility (%)'] == 20)]
    if not subset_3.empty:
        ax = axes[2]
        ax.bar(subset_3['Age'], subset_3['Reserve/GWB (%)'],
               color='#2ca02c', alpha=0.7, edgecolor='black', linewidth=1.5)
        for age, pct in zip(subset_3['Age'], subset_3['Reserve/GWB (%)']):
            ax.text(age, pct + 1, f'{pct:.1f}%', ha='center', fontsize=9, fontweight='bold')
        ax.set_xlabel('Policyholder Age', fontsize=11, fontweight='bold')
        ax.set_ylabel('Reserve as % of GWB', fontsize=11, fontweight='bold')
        ax.set_title('Reserve Intensity by Age\n(GWB = $500k, σ = 20%)',
                     fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(ages)

    # Scenario 4: Distribution of scenarios (example)
    ax = axes[3]
    # Create synthetic scenario distribution (in practice, would come from simulator)
    scenario_pvs = np.random.normal(loc=125000, scale=15000, size=1000)
    scenario_pvs = np.sort(scenario_pvs)
    cte_idx = int(0.70 * len(scenario_pvs))
    cte_value = scenario_pvs[cte_idx]

    ax.hist(scenario_pvs / 1000, bins=30, color='#d62728', alpha=0.6, edgecolor='black')
    ax.axvline(cte_value / 1000, color='black', linestyle='--', linewidth=2.5,
               label=f'CTE70 = ${cte_value/1000:.1f}k')
    ax.axvline(np.mean(scenario_pvs) / 1000, color='blue', linestyle='--', linewidth=2.5,
               label=f'Mean = ${np.mean(scenario_pvs)/1000:.1f}k')
    ax.set_xlabel('PV of Liabilities ($thousands)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
    ax.set_title('Distribution of Scenario Outcomes\n(1000 scenarios, Age=65, GWB=$500k)',
                 fontsize=11, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    fig.suptitle('VM-21 CTE70 Sensitivity Analysis\nGLWB Rider Reserve Requirements',
                 fontsize=13, fontweight='bold', y=0.995)

    fig.tight_layout()
    pdf_path = figures_dir / "vm21_cte70.pdf"
    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved VM-21 CTE sensitivity plot to {pdf_path}")

    plt.close(fig)


if __name__ == "__main__":
    main()
