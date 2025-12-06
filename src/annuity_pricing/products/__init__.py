"""
Product pricers for MYGA, FIA, and RILA annuities.

Provides:
- MYGAPricer: Fixed rate MYGA pricing
- FIAPricer: Index-linked FIA pricing with crediting methods
- RILAPricer: RILA pricing with buffer/floor protection
- ProductRegistry: Unified dispatch for all product types

See: CONSTITUTION.md Section 4
"""

from annuity_pricing.products.base import (
    BasePricer,
    CompetitivePosition,
    PricingResult,
)
from annuity_pricing.products.myga import MYGAPricer
from annuity_pricing.products.fia import (
    FIAPricer,
    FIAPricingResult,
    MarketParams as FIAMarketParams,
)
from annuity_pricing.products.rila import (
    RILAPricer,
    RILAPricingResult,
    MarketParams as RILAMarketParams,
)
from annuity_pricing.products.registry import (
    ProductRegistry,
    MarketEnvironment,
    create_default_registry,
    price_product,
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
