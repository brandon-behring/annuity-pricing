"""
Product pricers for MYGA, FIA, and RILA annuities.

Provides:
- MYGAPricer: Fixed rate MYGA pricing
- FIAPricer: Index-linked FIA pricing with crediting methods
- RILAPricer: RILA pricing with buffer/floor protection
- ProductRegistry: Unified dispatch for all product types

See: METHODOLOGY.md Section 4
"""

from annuity_pricing.products.base import (
    BasePricer,
    CompetitivePosition,
    PricingResult,
)
from annuity_pricing.products.fia import (
    FIAPricer,
    FIAPricingResult,
)
from annuity_pricing.products.fia import (
    MarketParams as FIAMarketParams,
)
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.products.registry import (
    MarketEnvironment,
    ProductRegistry,
    create_default_registry,
    price_product,
)
from annuity_pricing.products.rila import (
    MarketParams as RILAMarketParams,
)
from annuity_pricing.products.rila import (
    RILAPricer,
    RILAPricingResult,
)

__all__ = [
    # Base
    "BasePricer",
    "CompetitivePosition",
    "PricingResult",
    # MYGA
    "MYGAPricer",
    # FIA
    "FIAPricer",
    "FIAPricingResult",
    "FIAMarketParams",
    # RILA
    "RILAPricer",
    "RILAPricingResult",
    "RILAMarketParams",
    # Registry
    "ProductRegistry",
    "MarketEnvironment",
    "create_default_registry",
    "price_product",
]
