"""
Figure generation scripts for annuity-pricing paper.

Each module generates a deterministic figure with fixed seeds for reproducibility.

Usage:
    python -m scripts.figures.plot_rila_fia_payoffs
    python -m scripts.figures.plot_mc_convergence
    ... and so on

All figures are saved to paper/figures/ with underlying CSV data in paper/figures/data/
"""

__all__ = [
    "plot_rila_fia_payoffs",
    "plot_mc_convergence",
    "plot_bs_parity",
    "plot_glwb_fee_surface",
    "plot_vm21_cte_sensitivity",
]
