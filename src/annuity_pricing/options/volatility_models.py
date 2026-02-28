"""
Volatility model abstraction layer.

Provides unified interface for different volatility models:
- Black-Scholes: Constant volatility (default, backward compatible)
- Heston: Stochastic volatility with CIR variance process
- SABR: Stochastic Alpha Beta Rho model

[T1] Used by FIA/RILA pricers to dispatch to appropriate pricing method.

See: docs/knowledge/domain/option_pricing.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from annuity_pricing.options.pricing.heston import HestonParams
    from annuity_pricing.options.pricing.sabr import SABRParams


class VolatilityModelType(Enum):
    """Enumeration of supported volatility model types."""

    BLACK_SCHOLES = "black_scholes"
    HESTON = "heston"
    SABR = "sabr"


class VolatilityModel(ABC):
    """
    Abstract base class for volatility models.

    [T1] Provides type-safe dispatch mechanism for option pricing.
    Pricers use `get_model_type()` to route to appropriate implementation.
    """

    @abstractmethod
    def get_model_type(self) -> VolatilityModelType:
        """
        Return the volatility model type.

        Returns
        -------
        VolatilityModelType
            Type of volatility model (BS, Heston, or SABR)
        """
        pass

    @abstractmethod
    def get_initial_vol(self) -> float:
        """
        Return initial/reference volatility.

        [T1] Used for convergence checks and fallback calculations.
        For Heston, returns sqrt(v0). For SABR, returns alpha.

        Returns
        -------
        float
            Initial volatility (decimal, e.g., 0.20 for 20%)
        """
        pass


@dataclass(frozen=True)
class HestonVolatility(VolatilityModel):
    """
    Heston stochastic volatility model wrapper.

    [T1] Wraps HestonParams to implement VolatilityModel interface.
    Used for option pricing with stochastic volatility.

    Attributes
    ----------
    params : HestonParams
        Heston model parameters (v0, kappa, theta, sigma, rho)

    Examples
    --------
    >>> from annuity_pricing.options.pricing.heston import HestonParams
    >>> heston = HestonVolatility(HestonParams(v0=0.04, kappa=2.0, theta=0.04, sigma=0.3, rho=-0.7))
    >>> heston.get_model_type()
    VolatilityModelType.HESTON
    >>> heston.get_initial_vol()
    0.2  # sqrt(0.04)
    """

    params: "HestonParams"

    def get_model_type(self) -> VolatilityModelType:
        """Return HESTON model type."""
        return VolatilityModelType.HESTON

    def get_initial_vol(self) -> float:
        """Return sqrt(v0) as initial volatility."""
        import numpy as np

        return float(np.sqrt(self.params.v0))


@dataclass(frozen=True)
class SABRVolatility(VolatilityModel):
    """
    SABR stochastic volatility model wrapper.

    [T1] Wraps SABRParams to implement VolatilityModel interface.
    SABR produces implied vol → fed to Black-Scholes for pricing.

    Attributes
    ----------
    params : SABRParams
        SABR model parameters (alpha, beta, rho, nu)

    Examples
    --------
    >>> from annuity_pricing.options.pricing.sabr import SABRParams
    >>> sabr = SABRVolatility(SABRParams(alpha=0.2, beta=0.5, rho=-0.3, nu=0.4))
    >>> sabr.get_model_type()
    VolatilityModelType.SABR
    >>> sabr.get_initial_vol()
    0.2  # alpha
    """

    params: "SABRParams"

    def get_model_type(self) -> VolatilityModelType:
        """Return SABR model type."""
        return VolatilityModelType.SABR

    def get_initial_vol(self) -> float:
        """Return alpha as initial volatility."""
        return float(self.params.alpha)


# Type alias for any volatility model
VolModelType = HestonVolatility | SABRVolatility | None
