"""
Product dataclass schemas for MYGA, FIA, and RILA.

Immutable dataclasses representing annuity products for pricing.
See: wink-research-archive/product-guides/ANNUITY_PRODUCT_GUIDE.md
"""

from dataclasses import dataclass
from datetime import date

# =============================================================================
# Base Product
# =============================================================================


@dataclass(frozen=True)
class BaseProduct:
    """
    Base immutable product representation.

    Common fields across all annuity types.
    """

    # Identification
    company_name: str
    product_name: str
    product_group: str  # MYGA, FIA, RILA, FA, IVA

    # Status
    status: str  # current, historic, nlam, new
    effective_date: date | None = None

    # Surrender schedule
    surrender_charge_duration: int | None = None  # Years
    mva: bool | None = None  # Market Value Adjustment applies


# =============================================================================
# MYGA Product
# =============================================================================


@dataclass(frozen=True)
class MYGAProduct(BaseProduct):
    """
    Multi-Year Guaranteed Annuity product. [T1]

    Key characteristic: Fixed rate locked for entire term.

    Attributes
    ----------
    fixed_rate : float
        Guaranteed interest rate (decimal, e.g., 0.045 = 4.5%)
    guarantee_duration : int
        Years the rate is guaranteed
    effective_yield : float, optional
        Calculated effective annual yield
    premium_band : str, optional
        Premium tier for rate lookup

    Examples
    --------
    >>> myga = MYGAProduct(
    ...     company_name="Example Life",
    ...     product_name="5-Year MYGA",
    ...     product_group="MYGA",
    ...     status="current",
    ...     fixed_rate=0.045,
    ...     guarantee_duration=5
    ... )
    >>> myga.fixed_rate
    0.045
    """

    # MYGA-specific fields
    fixed_rate: float = 0.0  # Guaranteed rate (decimal)
    guarantee_duration: int = 0  # Years
    effective_yield: float | None = None
    premium_band: str | None = None

    def __post_init__(self) -> None:
        """Validate MYGA fields."""
        if self.product_group != "MYGA":
            raise ValueError(
                f"CRITICAL: MYGAProduct requires product_group='MYGA', got '{self.product_group}'"
            )
        if self.fixed_rate < 0:
            raise ValueError(f"CRITICAL: fixed_rate must be >= 0, got {self.fixed_rate}")
        if self.guarantee_duration < 0:
            raise ValueError(
                f"CRITICAL: guarantee_duration must be >= 0, got {self.guarantee_duration}"
            )

    @classmethod
    def demo(cls) -> "MYGAProduct":
        """
        Create example MYGA for quick testing.

        Returns a 5-year MYGA at 4.5% — a typical product structure.

        Example
        -------
        >>> myga = MYGAProduct.demo()
        >>> print(f"Rate: {myga.fixed_rate:.1%}, Term: {myga.guarantee_duration}yr")
        Rate: 4.5%, Term: 5yr
        """
        return cls(
            company_name="Example Life",
            product_name="5-Year MYGA Demo",
            product_group="MYGA",
            status="current",
            fixed_rate=0.045,
            guarantee_duration=5,
        )


# =============================================================================
# FIA Product
# =============================================================================


@dataclass(frozen=True)
class FIAProduct(BaseProduct):
    """
    Fixed Indexed Annuity product. [T1]

    Key characteristic: Index-linked returns with 0% floor.

    Attributes
    ----------
    cap_rate : float, optional
        Maximum return cap (decimal)
    participation_rate : float, optional
        Percentage of index gain credited (decimal)
    spread_rate : float, optional
        Fee subtracted from index return (decimal)
    performance_triggered_rate : float, optional
        Fixed rate if index positive (decimal)
    index_used : str, optional
        Index name (e.g., "S&P 500")
    indexing_method : str, optional
        Crediting method (e.g., "Annual Point to Point")
    index_crediting_frequency : str, optional
        How often credited (e.g., "Annual")

    Examples
    --------
    >>> fia = FIAProduct(
    ...     company_name="Example Life",
    ...     product_name="S&P 500 Cap",
    ...     product_group="FIA",
    ...     status="current",
    ...     cap_rate=0.08,
    ...     index_used="S&P 500"
    ... )
    >>> fia.cap_rate
    0.08
    """

    # FIA-specific fields
    cap_rate: float | None = None
    participation_rate: float | None = None
    spread_rate: float | None = None
    performance_triggered_rate: float | None = None
    index_used: str | None = None
    indexing_method: str | None = None
    index_crediting_frequency: str | None = None
    term_years: int | None = None  # Investment term in years

    def __post_init__(self) -> None:
        """Validate FIA fields."""
        if self.product_group != "FIA":
            raise ValueError(
                f"CRITICAL: FIAProduct requires product_group='FIA', got '{self.product_group}'"
            )
        # Cap rate validation
        if self.cap_rate is not None and self.cap_rate < 0:
            raise ValueError(f"CRITICAL: cap_rate must be >= 0, got {self.cap_rate}")
        # Participation rate validation (can exceed 1.0)
        if self.participation_rate is not None and self.participation_rate < 0:
            raise ValueError(
                f"CRITICAL: participation_rate must be >= 0, got {self.participation_rate}"
            )

    @classmethod
    def demo(cls) -> "FIAProduct":
        """
        Create example FIA for quick testing.

        Returns an S&P 500 point-to-point FIA with 10% cap — a typical structure.

        Example
        -------
        >>> fia = FIAProduct.demo()
        >>> print(f"Cap: {fia.cap_rate:.1%}, Index: {fia.index_used}")
        Cap: 10.0%, Index: S&P 500
        """
        return cls(
            company_name="Example Life",
            product_name="S&P 500 Cap Demo",
            product_group="FIA",
            status="current",
            index_used="S&P 500",
            indexing_method="Annual Point to Point",
            cap_rate=0.10,
            term_years=6,
        )


# =============================================================================
# RILA Product
# =============================================================================


@dataclass(frozen=True)
class RILAProduct(BaseProduct):
    """
    Registered Index-Linked Annuity product. [T1]

    Key characteristic: Partial downside protection via buffer or floor.

    Attributes
    ----------
    buffer_rate : float, optional
        Buffer/floor level (decimal, e.g., 0.10 = 10%)
    buffer_modifier : str, optional
        Type: "Losses Covered Up To" (buffer) or "Losses Covered After" (floor)
    cap_rate : float, optional
        Maximum return cap (decimal)
    participation_rate : float, optional
        Percentage of index gain credited (decimal)
    index_used : str, optional
        Index name
    indexing_method : str, optional
        Crediting method
    term_years : int, optional
        Investment term in years

    Examples
    --------
    >>> rila = RILAProduct(
    ...     company_name="Example Life",
    ...     product_name="10% Buffer S&P",
    ...     product_group="RILA",
    ...     status="current",
    ...     buffer_rate=0.10,
    ...     buffer_modifier="Losses Covered Up To",
    ...     cap_rate=0.15
    ... )
    >>> rila.is_buffer()
    True
    """

    # RILA-specific fields
    buffer_rate: float | None = None
    buffer_modifier: str | None = None  # Determines buffer vs floor
    cap_rate: float | None = None
    participation_rate: float | None = None
    index_used: str | None = None
    indexing_method: str | None = None
    term_years: int | None = None

    def __post_init__(self) -> None:
        """Validate RILA fields."""
        if self.product_group != "RILA":
            raise ValueError(
                f"CRITICAL: RILAProduct requires product_group='RILA', got '{self.product_group}'"
            )
        if self.buffer_rate is not None and self.buffer_rate < 0:
            raise ValueError(f"CRITICAL: buffer_rate must be >= 0, got {self.buffer_rate}")

        # [F.2] Validate buffer_modifier for protection type classification
        if self.buffer_modifier is None:
            raise ValueError(
                "CRITICAL: buffer_modifier required for RILA product. "
                "Must contain 'Up To' (buffer) or 'After' (floor)."
            )
        normalized = self.buffer_modifier.lower().strip()
        if "up to" not in normalized and "after" not in normalized:
            raise ValueError(
                f"CRITICAL: buffer_modifier must contain 'Up To' (buffer) or 'After' (floor), "
                f"got '{self.buffer_modifier}'"
            )

    def is_buffer(self) -> bool:
        """
        Check if this product uses buffer protection. [T1]

        Buffer: Insurer absorbs FIRST X% of losses.

        Returns
        -------
        bool
            True if buffer protection, False if floor or unknown
        """
        if self.buffer_modifier is None:
            return False
        return "up to" in self.buffer_modifier.lower()

    def is_floor(self) -> bool:
        """
        Check if this product uses floor protection. [T1]

        Floor: Client absorbs UP TO X% of losses, insurer covers excess.

        Returns
        -------
        bool
            True if floor protection, False if buffer or unknown
        """
        if self.buffer_modifier is None:
            return False
        return "after" in self.buffer_modifier.lower()

    @classmethod
    def demo(cls) -> "RILAProduct":
        """
        Create example RILA for quick testing.

        Returns an S&P 500 RILA with 10% buffer and 15% cap — a typical structure.

        Example
        -------
        >>> rila = RILAProduct.demo()
        >>> print(f"Buffer: {rila.buffer_rate:.0%}, Cap: {rila.cap_rate:.0%}")
        Buffer: 10%, Cap: 15%
        >>> rila.is_buffer()
        True
        """
        return cls(
            company_name="Example Life",
            product_name="10% Buffer S&P Demo",
            product_group="RILA",
            status="current",
            index_used="S&P 500",
            indexing_method="Annual Point to Point",
            buffer_rate=0.10,
            buffer_modifier="Losses Covered Up To",
            cap_rate=0.15,
            term_years=6,
        )


# =============================================================================
# Factory Functions
# =============================================================================


def create_myga_from_row(row: dict) -> MYGAProduct:
    """
    Create MYGAProduct from WINK DataFrame row.

    Parameters
    ----------
    row : dict
        Dictionary from DataFrame row (e.g., df.iloc[0].to_dict())

    Returns
    -------
    MYGAProduct
        Immutable MYGA product
    """
    return MYGAProduct(
        company_name=row.get("companyName", "Unknown"),
        product_name=row.get("productName", "Unknown"),
        product_group="MYGA",
        status=row.get("status", "unknown"),
        effective_date=row.get("effectiveDate"),
        surrender_charge_duration=row.get("surrChargeDuration"),
        mva=row.get("mva") == "Y" if row.get("mva") else None,
        fixed_rate=row.get("fixedRate", 0.0) or 0.0,
        guarantee_duration=int(row.get("guaranteeDuration", 0) or 0),
        effective_yield=row.get("effectiveYield"),
        premium_band=row.get("premiumBand"),
    )


def create_fia_from_row(row: dict) -> FIAProduct:
    """
    Create FIAProduct from WINK DataFrame row.

    Parameters
    ----------
    row : dict
        Dictionary from DataFrame row

    Returns
    -------
    FIAProduct
        Immutable FIA product
    """
    # Extract term_years from WINK data
    term_years = None
    if "termYears" in row and row["termYears"] is not None:
        try:
            term_years = int(row["termYears"])
        except (ValueError, TypeError):
            pass  # Keep as None if conversion fails

    return FIAProduct(
        company_name=row.get("companyName", "Unknown"),
        product_name=row.get("productName", "Unknown"),
        product_group="FIA",
        status=row.get("status", "unknown"),
        effective_date=row.get("effectiveDate"),
        surrender_charge_duration=row.get("surrChargeDuration"),
        mva=row.get("mva") == "Y" if row.get("mva") else None,
        cap_rate=row.get("capRate"),
        participation_rate=row.get("participationRate"),
        spread_rate=row.get("spreadRate"),
        performance_triggered_rate=row.get("performanceTriggeredRate"),
        index_used=row.get("indexUsed"),
        indexing_method=row.get("indexingMethod"),
        index_crediting_frequency=row.get("indexCreditingFrequency"),
        term_years=term_years,
    )


def create_rila_from_row(row: dict) -> RILAProduct:
    """
    Create RILAProduct from WINK DataFrame row.

    Parameters
    ----------
    row : dict
        Dictionary from DataFrame row

    Returns
    -------
    RILAProduct
        Immutable RILA product
    """
    # Extract term_years from WINK data
    term_years = None
    if "termYears" in row and row["termYears"] is not None:
        try:
            term_years = int(row["termYears"])
        except (ValueError, TypeError):
            pass  # Keep as None if conversion fails

    return RILAProduct(
        company_name=row.get("companyName", "Unknown"),
        product_name=row.get("productName", "Unknown"),
        product_group="RILA",
        status=row.get("status", "unknown"),
        effective_date=row.get("effectiveDate"),
        surrender_charge_duration=row.get("surrChargeDuration"),
        mva=row.get("mva") == "Y" if row.get("mva") else None,
        buffer_rate=row.get("bufferRate"),
        buffer_modifier=row.get("bufferModifier"),
        cap_rate=row.get("capRate"),
        participation_rate=row.get("participationRate"),
        index_used=row.get("indexUsed"),
        indexing_method=row.get("indexingMethod"),
        term_years=term_years,
    )


# =============================================================================
# GLWB Product
# =============================================================================


@dataclass(frozen=True)
class GLWBProduct(BaseProduct):
    """
    Guaranteed Lifetime Withdrawal Benefit product. [T1]

    GLWB provides guaranteed income for life regardless of account performance.
    Key characteristic: Withdrawals continue even if account value exhausted.

    Attributes
    ----------
    withdrawal_rate : float
        Annual withdrawal rate as % of benefit base (e.g., 0.05 = 5%)
    rollup_rate : float
        Annual rollup rate for benefit base growth (e.g., 0.06 = 6%)
    rollup_type : str
        'simple' or 'compound' rollup
    rollup_cap_years : int
        Maximum years rollup applies (typically 10)
    step_up_frequency : int
        How often ratchet occurs (years, typically 1)
    fee_rate : float
        Annual fee as % of account value (e.g., 0.01 = 1%)
    deferral_years : int
        Years before withdrawals begin

    Examples
    --------
    >>> glwb = GLWBProduct(
    ...     company_name="Example Life",
    ...     product_name="GLWB 5%",
    ...     product_group="GLWB",
    ...     status="current",
    ...     withdrawal_rate=0.05,
    ...     rollup_rate=0.06,
    ... )

    See: docs/knowledge/domain/glwb_mechanics.md
    See: docs/references/L3/bauer_kling_russ_2008.md
    """

    # GLWB-specific fields
    withdrawal_rate: float = 0.05  # Annual withdrawal as % of benefit base
    rollup_rate: float = 0.06  # Annual benefit base growth rate
    rollup_type: str = "compound"  # 'simple' or 'compound'
    rollup_cap_years: int = 10  # Max years rollup applies
    step_up_frequency: int = 1  # Ratchet frequency (years)
    fee_rate: float = 0.01  # Annual fee as % of AV
    deferral_years: int = 0  # Years before withdrawals begin

    def __post_init__(self) -> None:
        """Validate GLWB fields."""
        if self.product_group != "GLWB":
            raise ValueError(
                f"CRITICAL: GLWBProduct requires product_group='GLWB', got '{self.product_group}'"
            )
        if not 0 < self.withdrawal_rate <= 0.20:
            raise ValueError(
                f"CRITICAL: withdrawal_rate must be in (0, 0.20], got {self.withdrawal_rate}"
            )
        if self.rollup_rate < 0:
            raise ValueError(f"CRITICAL: rollup_rate must be >= 0, got {self.rollup_rate}")
        if self.rollup_type not in ("simple", "compound"):
            raise ValueError(
                f"CRITICAL: rollup_type must be 'simple' or 'compound', got '{self.rollup_type}'"
            )
        if self.fee_rate < 0:
            raise ValueError(f"CRITICAL: fee_rate must be >= 0, got {self.fee_rate}")

    @classmethod
    def demo(cls) -> "GLWBProduct":
        """
        Create example GLWB for quick testing.

        Returns a 5% withdrawal / 6% compound rollup GLWB — a typical structure.

        Example
        -------
        >>> glwb = GLWBProduct.demo()
        >>> print(f"Withdrawal: {glwb.withdrawal_rate:.0%}, Rollup: {glwb.rollup_rate:.0%}")
        Withdrawal: 5%, Rollup: 6%
        """
        return cls(
            company_name="Example Life",
            product_name="GLWB Demo",
            product_group="GLWB",
            status="current",
            withdrawal_rate=0.05,
            rollup_rate=0.06,
            rollup_type="compound",
            rollup_cap_years=10,
            fee_rate=0.01,
        )
