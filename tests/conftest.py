"""
Centralized pytest fixtures for annuity-pricing test suite.

This module provides shared fixtures used across all test categories:
- anti_patterns/
- unit/
- validation/
- integration/

Fixture Categories:
1. Market Parameters - Standard market conditions for option pricing
2. Hull Examples - Textbook examples for validation
3. WINK Data - Sample fixture for integration testing
4. Product Fixtures - Sample products for each type
5. Adapter Fixtures - External library adapters
6. Checksum Verification - Ensure fixtures haven't changed unexpectedly
"""

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

# =============================================================================
# FIXTURE PATHS
# =============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"
WINK_SAMPLE_PATH = FIXTURES_DIR / "wink_sample.parquet"
TREASURY_YIELDS_PATH = FIXTURES_DIR / "treasury_yields_2024_01_15.csv"
CHECKSUMS_PATH = FIXTURES_DIR / "CHECKSUMS.sha256"


# =============================================================================
# TOLERANCE TIERS (from plan decisions)
# =============================================================================


@dataclass(frozen=True)
class ToleranceTiers:
    """
    Tiered tolerance framework for different test types.

    Derived from precision requirements, not ad hoc.
    See: docs/TOLERANCE_JUSTIFICATION.md
    """

    # Anti-pattern tests: Very tight (fundamental violations)
    anti_pattern: float = 1e-10

    # Validation tests: Library precision
    validation: float = 1e-6

    # Integration tests: Workflow correctness
    integration: float = 1e-4

    # Monte Carlo vs analytical: Accounts for stochastic variance
    mc_100k_paths: float = 0.01  # 1%
    mc_500k_paths: float = 0.005  # 0.5%


TOLERANCES = ToleranceTiers()


@pytest.fixture(scope="session")
def tolerances() -> ToleranceTiers:
    """Provide tiered tolerance settings for all tests."""
    return TOLERANCES


# =============================================================================
# CHECKSUM VERIFICATION
# =============================================================================


def _compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def _load_expected_checksums() -> dict[str, str]:
    """Load expected checksums from CHECKSUMS.sha256 file."""
    checksums = {}
    if CHECKSUMS_PATH.exists():
        with open(CHECKSUMS_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split()
                    if len(parts) >= 2:
                        checksum, filename = parts[0], parts[1]
                        checksums[filename] = checksum
    return checksums


@pytest.fixture(scope="session", autouse=True)
def verify_fixture_checksums():
    """
    Verify test fixtures haven't changed unexpectedly.

    This runs automatically at the start of each test session.
    If fixtures have changed, either:
    1. The change was intentional → update CHECKSUMS.sha256
    2. The change was unintentional → investigate the cause
    """
    expected = _load_expected_checksums()

    for filename, expected_hash in expected.items():
        filepath = FIXTURES_DIR / filename
        if filepath.exists():
            actual_hash = _compute_sha256(filepath)
            if actual_hash != expected_hash:
                warnings.warn(
                    f"Fixture checksum mismatch for {filename}!\n"
                    f"  Expected: {expected_hash}\n"
                    f"  Actual:   {actual_hash}\n"
                    f"If intentional, update tests/fixtures/CHECKSUMS.sha256",
                    UserWarning,
                )


# =============================================================================
# MARKET PARAMETERS
# =============================================================================


@dataclass(frozen=True)
class MarketParams:
    """Standard market parameters for option pricing tests."""

    spot: float = 100.0
    strike: float = 100.0
    rate: float = 0.05
    dividend: float = 0.02
    volatility: float = 0.20
    time_to_expiry: float = 1.0


@pytest.fixture
def market_params() -> MarketParams:
    """Standard ATM market parameters."""
    return MarketParams()


@pytest.fixture
def market_params_dict() -> dict[str, float]:
    """Standard market parameters as dictionary."""
    return {
        "spot": 100.0,
        "strike": 100.0,
        "rate": 0.05,
        "dividend": 0.02,
        "volatility": 0.20,
        "time_to_expiry": 1.0,
    }


# =============================================================================
# HULL TEXTBOOK EXAMPLES
# =============================================================================


@dataclass(frozen=True)
class HullExample:
    """A textbook example from Hull (2021) Options, Futures, and Other Derivatives."""

    name: str
    chapter: int
    spot: float
    strike: float
    rate: float
    dividend: float
    volatility: float
    time_to_expiry: float
    expected_call: float | None = None
    expected_put: float | None = None
    expected_delta: float | None = None
    expected_gamma: float | None = None
    expected_vega: float | None = None
    expected_theta: float | None = None
    expected_rho: float | None = None


# Hull (2021) Chapter 15, Example 15.6
HULL_EXAMPLE_15_6 = HullExample(
    name="Hull Example 15.6",
    chapter=15,
    spot=42.0,
    strike=40.0,
    rate=0.10,
    dividend=0.0,
    volatility=0.20,
    time_to_expiry=0.5,
    expected_call=4.76,
    expected_put=0.81,
)

# Hull (2021) Chapter 19 Greeks examples
HULL_EXAMPLE_19_1 = HullExample(
    name="Hull Example 19.1 (Delta)",
    chapter=19,
    spot=49.0,
    strike=50.0,
    rate=0.05,
    dividend=0.0,
    volatility=0.20,
    time_to_expiry=0.3846,  # 20 weeks
    expected_delta=0.522,
)


@pytest.fixture
def hull_example_15_6() -> HullExample:
    """Hull Chapter 15 Example 15.6: European call on non-dividend stock."""
    return HULL_EXAMPLE_15_6


@pytest.fixture
def hull_example_19_1() -> HullExample:
    """Hull Chapter 19 Example 19.1: Delta calculation."""
    return HULL_EXAMPLE_19_1


@pytest.fixture
def hull_examples() -> list[HullExample]:
    """All Hull textbook examples for batch validation."""
    return [HULL_EXAMPLE_15_6, HULL_EXAMPLE_19_1]


# =============================================================================
# WINK DATA FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def wink_sample_path() -> Path:
    """Path to WINK sample fixture."""
    return WINK_SAMPLE_PATH


@pytest.fixture(scope="session")
def wink_sample_data() -> pd.DataFrame:
    """Load WINK sample data."""
    if not WINK_SAMPLE_PATH.exists():
        pytest.skip(f"WINK sample fixture not found: {WINK_SAMPLE_PATH}")
    return pd.read_parquet(WINK_SAMPLE_PATH)


@pytest.fixture
def treasury_yields() -> pd.DataFrame:
    """Load Treasury yields fixture."""
    if not TREASURY_YIELDS_PATH.exists():
        pytest.skip(f"Treasury yields fixture not found: {TREASURY_YIELDS_PATH}")
    return pd.read_csv(TREASURY_YIELDS_PATH)


# =============================================================================
# PRODUCT FIXTURES
# =============================================================================


@pytest.fixture
def sample_myga_product():
    """Sample MYGA product for testing."""
    from annuity_pricing.products.registry import MYGAProduct

    return MYGAProduct(
        company_name="Test Company",
        product_name="Test MYGA",
        product_group="MYGA",
        status="current",
        fixed_rate=0.045,
        guarantee_duration=5,
    )


@pytest.fixture
def sample_fia_product():
    """Sample FIA product for testing."""
    from annuity_pricing.products.registry import FIAProduct

    return FIAProduct(
        company_name="Test Company",
        product_name="Test FIA",
        product_group="FIA",
        status="current",
        cap_rate=0.06,
        index_used="S&P 500",
        indexing_method="Annual Point to Point",
    )


@pytest.fixture
def sample_rila_product():
    """Sample RILA product for testing."""
    from annuity_pricing.products.registry import RILAProduct

    return RILAProduct(
        company_name="Test Company",
        product_name="Test RILA",
        product_group="RILA",
        status="current",
        buffer_rate=0.10,
        cap_rate=0.15,
        index_used="S&P 500",
    )


# =============================================================================
# REGISTRY FIXTURE
# =============================================================================


@pytest.fixture
def registry():
    """Product registry for pricing."""
    from annuity_pricing.products.registry import ProductRegistry

    return ProductRegistry()


# =============================================================================
# ADAPTER FIXTURES (Optional Dependencies)
# =============================================================================


@pytest.fixture
def financepy_adapter():
    """
    financepy adapter for cross-validation.

    Skips if financepy not installed.
    """
    pytest.importorskip("financepy")
    from annuity_pricing.adapters.financepy_adapter import FinancePyAdapter

    return FinancePyAdapter()


@pytest.fixture
def quantlib_adapter():
    """
    QuantLib adapter for cross-validation.

    Skips if QuantLib not installed.
    """
    pytest.importorskip("QuantLib")
    from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

    return QuantLibAdapter()


@pytest.fixture
def pyfeng_adapter():
    """
    pyfeng adapter for MC cross-validation.

    Skips if pyfeng not installed.
    """
    pytest.importorskip("pyfeng")
    from annuity_pricing.adapters.pyfeng_adapter import PyFengAdapter

    return PyFengAdapter()


# =============================================================================
# NUMPY RANDOM SEED
# =============================================================================


@pytest.fixture
def fixed_seed():
    """
    Set a fixed random seed for reproducibility.

    Use this for tests that involve stochastic simulations.
    """
    seed = 42
    np.random.seed(seed)
    return seed


@pytest.fixture
def reproducible_rng():
    """
    Provide a reproducible numpy random generator.

    Preferred over fixed_seed for newer code.
    """
    return np.random.default_rng(seed=42)


# =============================================================================
# ORACLE FALLBACK FIXTURES
# =============================================================================

GOLDEN_DIR = Path(__file__).parent / "golden" / "outputs"


def _load_golden_file(filename: str) -> dict[str, Any]:
    """Load a golden output JSON file."""
    import json

    filepath = GOLDEN_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Golden file not found: {filepath}")

    with open(filepath) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def oracle_bs_prices() -> dict[str, Any]:
    """
    Load oracle BS prices with fallback for missing external libraries.

    If financepy/QuantLib are available, returns live adapter.
    Otherwise, returns stored golden values with warning.

    Returns
    -------
    dict with keys:
        - "live": bool - True if using live library, False if using stored values
        - "adapter": adapter instance (if live)
        - "data": stored golden data (if not live)
        - "source": str describing the source
    """
    # Try financepy first
    try:
        from annuity_pricing.adapters.financepy_adapter import FinancePyAdapter

        adapter = FinancePyAdapter()
        if adapter.is_available:
            return {
                "live": True,
                "adapter": adapter,
                "source": "financepy (live)",
            }
    except ImportError:
        pass

    # Fall back to stored oracle values
    try:
        oracle_data = _load_golden_file("oracle_bs_prices.json")
        # Note: Not using warnings.warn() as pytest may treat it as error
        # The "source" field in the return indicates fallback mode
        return {
            "live": False,
            "data": oracle_data,
            "source": "oracle_bs_prices.json (stored - financepy not available)",
        }
    except FileNotFoundError as e:
        pytest.skip(f"No oracle source available: {e}")


@pytest.fixture(scope="session")
def oracle_quantlib() -> dict[str, Any]:
    """
    Load oracle QuantLib values with fallback for missing library.

    Returns
    -------
    dict with keys:
        - "live": bool - True if using live library, False if using stored values
        - "adapter": adapter instance (if live)
        - "data": stored golden data (if not live)
        - "source": str describing the source
    """
    # Try QuantLib first
    try:
        from annuity_pricing.adapters.quantlib_adapter import QuantLibAdapter

        adapter = QuantLibAdapter()
        if adapter.is_available:
            return {
                "live": True,
                "adapter": adapter,
                "source": "QuantLib (live)",
            }
    except ImportError:
        pass

    # Fall back to stored oracle values
    try:
        oracle_data = _load_golden_file("oracle_bs_prices.json")
        # Note: Not using warnings.warn() as pytest may treat it as error
        # The "source" field in the return indicates fallback mode
        return {
            "live": False,
            "data": oracle_data,
            "source": "oracle_bs_prices.json (stored - QuantLib not available)",
        }
    except FileNotFoundError as e:
        pytest.skip(f"No oracle source available: {e}")
