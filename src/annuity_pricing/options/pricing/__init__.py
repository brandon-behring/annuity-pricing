"""
Option pricing implementations.

Provides:
- Black-Scholes analytical pricing with Greeks
- Heston stochastic volatility:
  - COS method (RECOMMENDED): 0% error vs QuantLib
  - Monte Carlo: <1% error
  - FFT (experimental): ~22% bias
- SABR implied volatility

See: METHODOLOGY.md Section 3.1
"""

from annuity_pricing.options.pricing.black_scholes import (
    BSResult,
    black_scholes_call,
    black_scholes_greeks,
    black_scholes_price,
    black_scholes_put,
    implied_volatility,
    price_buffer_protection,
    price_capped_call,
    put_call_parity_check,
)
from annuity_pricing.options.pricing.heston import (
    HestonParams,
    heston_characteristic_function,
    heston_price,
    heston_price_call,
    heston_price_call_mc,
    heston_price_fft,
    heston_price_put,
    heston_price_put_mc,
)
from annuity_pricing.options.pricing.heston_cos import (
    COSParams,
    heston_price_call_cos,
    heston_price_cos,
    heston_price_put_cos,
)
from annuity_pricing.options.pricing.sabr import (
    SABRParams,
    calibrate_sabr,
    sabr_implied_volatility,
    sabr_price_call,
    sabr_price_put,
)

__all__ = [
    # Black-Scholes
    "BSResult",
    "black_scholes_call",
    "black_scholes_greeks",
    "black_scholes_price",
    "black_scholes_put",
    "implied_volatility",
    "price_buffer_protection",
    "price_capped_call",
    "put_call_parity_check",
    # Heston
    "HestonParams",
    "heston_characteristic_function",
    "heston_price",  # Unified interface (defaults to COS)
    "heston_price_call",
    "heston_price_call_mc",
    "heston_price_fft",
    "heston_price_put",
    "heston_price_put_mc",
    # Heston COS
    "COSParams",
    "heston_price_cos",
    "heston_price_call_cos",
    "heston_price_put_cos",
    # SABR
    "SABRParams",
    "calibrate_sabr",
    "sabr_implied_volatility",
    "sabr_price_call",
    "sabr_price_put",
]
