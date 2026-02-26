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
- METHODOLOGY.md for methodology

Version: 1.0.0
"""

__version__ = "1.0.0"

# =============================================================================
# Products - Primary API
# =============================================================================
# =============================================================================
# Configuration
# =============================================================================
from annuity_pricing.config.settings import SETTINGS

# Product dataclasses from schemas
from annuity_pricing.data.schemas import FIAProduct, GLWBProduct, MYGAProduct, RILAProduct
from annuity_pricing.loaders.mortality import MortalityLoader, MortalityTable

# =============================================================================
# Loaders
# =============================================================================
from annuity_pricing.loaders.yield_curve import YieldCurve, YieldCurveLoader

# =============================================================================
# Options Pricing
# =============================================================================
from annuity_pricing.options.pricing import (
    BSResult,
    # Heston
    HestonParams,
    # SABR
    SABRParams,
    black_scholes_call,
    black_scholes_greeks,
    black_scholes_put,
    heston_price,
    sabr_implied_volatility,
)

# Volatility models
from annuity_pricing.options.volatility_models import (
    HestonVolatility,
    SABRVolatility,
    VolatilityModelType,
)

# =============================================================================
# Market Parameters
# =============================================================================
from annuity_pricing.products.fia import FIAPricer, FIAPricingResult, MarketParams
from annuity_pricing.products.glwb import GLWBPricer, GLWBPricingResult
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.products.rila import RILAPricer, RILAPricingResult

# =============================================================================
# Regulatory (Prototypes)
# =============================================================================
from annuity_pricing.regulatory.vm21 import VM21Calculator
from annuity_pricing.regulatory.vm22 import VM22Calculator
from annuity_pricing.stress_testing.reverse import ReverseStressTester

# =============================================================================
# Stress Testing
# =============================================================================
from annuity_pricing.stress_testing.runner import StressTestConfig, StressTestRunner
from annuity_pricing.stress_testing.sensitivity import SensitivityAnalyzer

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
    "GLWBPricer",
    "GLWBPricingResult",
    "GLWBProduct",
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
