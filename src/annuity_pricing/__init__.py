"""
annuity-pricing: Actuarial pricing for FIA, RILA, MYGA, and GLWB products.

Quick Start
-----------
>>> from annuity_pricing import FIAPricer, RILAPricer, MYGAPricer, MarketParams
>>> market = MarketParams(spot=4500.0, risk_free_rate=0.045, volatility=0.18)
>>> pricer = FIAPricer(market_params=market)

See Also
--------
- docs/guides/getting_started.md for full examples
- CONSTITUTION.md for methodology

Version: 0.2.0
"""

__version__ = "0.2.0"

# =============================================================================
# Products - Primary API
# =============================================================================
from annuity_pricing.products.fia import FIAPricer, FIAPricingResult, FIAProduct
from annuity_pricing.products.rila import RILAPricer, RILAPricingResult, RILAProduct
from annuity_pricing.products.myga import MYGAPricer, MYGAProduct

# =============================================================================
# Market Parameters
# =============================================================================
from annuity_pricing.products.fia import MarketParams
from annuity_pricing.products.fia import (
    VolatilityModelType,
    HestonVolatility,
    SABRVolatility,
)

# =============================================================================
# Options Pricing
# =============================================================================
from annuity_pricing.options.pricing import (
    black_scholes_call,
    black_scholes_put,
    black_scholes_greeks,
    BSResult,
    # Heston
    HestonParams,
    heston_price,
    # SABR
    SABRParams,
    sabr_implied_volatility,
)

# =============================================================================
# Loaders
# =============================================================================
from annuity_pricing.loaders.yield_curve import YieldCurveLoader, YieldCurve
from annuity_pricing.loaders.mortality import MortalityLoader, MortalityTable

# =============================================================================
# Configuration
# =============================================================================
from annuity_pricing.config.settings import SETTINGS

# =============================================================================
# Regulatory (Prototypes)
# =============================================================================
from annuity_pricing.regulatory.vm21 import VM21Calculator
from annuity_pricing.regulatory.vm22 import VM22Calculator

# =============================================================================
# Stress Testing
# =============================================================================
from annuity_pricing.stress_testing.runner import StressTestRunner, StressTestConfig
from annuity_pricing.stress_testing.sensitivity import SensitivityAnalyzer
from annuity_pricing.stress_testing.reverse import ReverseStressTester

__all__ = [
    # Version
    "__version__",
    # Products
    "FIAPricer",
    "FIAPricingResult",
    "FIAProduct",
    "RILAPricer",
    "RILAPricingResult",
    "RILAProduct",
    "MYGAPricer",
    "MYGAProduct",
    # Market
    "MarketParams",
    "VolatilityModelType",
    "HestonVolatility",
    "SABRVolatility",
    # Options
    "black_scholes_call",
    "black_scholes_put",
    "black_scholes_greeks",
    "BSResult",
    "HestonParams",
    "heston_price",
    "SABRParams",
    "sabr_implied_volatility",
    # Loaders
    "YieldCurveLoader",
    "YieldCurve",
    "MortalityLoader",
    "MortalityTable",
    # Config
    "SETTINGS",
    # Regulatory
    "VM21Calculator",
    "VM22Calculator",
    # Stress Testing
    "StressTestRunner",
    "StressTestConfig",
    "SensitivityAnalyzer",
    "ReverseStressTester",
]
