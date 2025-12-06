"""
Competitive analysis modules for annuity products.

Provides positioning, spread analysis, and rankings.
"""

from annuity_pricing.competitive.positioning import (
    DistributionStats,
    PositionResult,
    PositioningAnalyzer,
)
from annuity_pricing.competitive.rankings import (
    CompanyRanking,
    ProductRanking,
    RankingAnalyzer,
)
from annuity_pricing.competitive.spreads import (
    SpreadDistribution,
    SpreadResult,
    SpreadAnalyzer,
    build_treasury_curve,
)

__all__ = [
    # Positioning
    "DistributionStats",
    "PositionResult",
    "PositioningAnalyzer",
    # Rankings
    "CompanyRanking",
    "ProductRanking",
    "RankingAnalyzer",
    # Spreads
    "SpreadDistribution",
    "SpreadResult",
    "SpreadAnalyzer",
    "build_treasury_curve",
]
