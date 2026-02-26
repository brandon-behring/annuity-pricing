"""
Validation Gates - HALT/PASS framework for pricing validation.

Implements a multi-stage validation system that checks pricing results
for sanity before allowing them to be used. Gates can HALT (reject with
diagnostics) or PASS (allow to proceed).

See: METHODOLOGY.md Section 5
See: docs/knowledge/domain/mgsv_mva.md for regulatory bounds
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

from annuity_pricing.products.base import PricingResult
from annuity_pricing.products.fia import FIAPricingResult
from annuity_pricing.products.rila import RILAPricingResult


class GateStatus(Enum):
    """Status of a validation gate."""
    PASS = "pass"
    HALT = "halt"
    WARN = "warn"


@dataclass(frozen=True)
class GateResult:
    """
    Result of a validation gate check.

    Attributes
    ----------
    status : GateStatus
        PASS, HALT, or WARN
    gate_name : str
        Name of the gate that was checked
    message : str
        Explanation of the result
    value : Any, optional
        The value that was checked
    threshold : Any, optional
        The threshold that was applied
    """

    status: GateStatus
    gate_name: str
    message: str
    value: Any | None = None
    threshold: Any | None = None

    @property
    def passed(self) -> bool:
        """Check if gate passed (PASS or WARN)."""
        return self.status != GateStatus.HALT


@dataclass(frozen=True)
class ValidationReport:
    """
    Complete validation report from all gates.

    Attributes
    ----------
    results : tuple[GateResult, ...]
        Results from all gates
    overall_status : GateStatus
        Worst status across all gates
    """

    results: tuple[GateResult, ...]

    @property
    def overall_status(self) -> GateStatus:
        """Get worst status across all gates."""
        if any(r.status == GateStatus.HALT for r in self.results):
            return GateStatus.HALT
        elif any(r.status == GateStatus.WARN for r in self.results):
            return GateStatus.WARN
        return GateStatus.PASS

    @property
    def passed(self) -> bool:
        """Check if all gates passed (no HALTs)."""
        return self.overall_status != GateStatus.HALT

    @property
    def halted_gates(self) -> list[GateResult]:
        """Get all gates that halted."""
        return [r for r in self.results if r.status == GateStatus.HALT]

    @property
    def warned_gates(self) -> list[GateResult]:
        """Get all gates that warned."""
        return [r for r in self.results if r.status == GateStatus.WARN]

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            "overall_status": self.overall_status.value,
            "passed": self.passed,
            "n_halted": len(self.halted_gates),
            "n_warned": len(self.warned_gates),
            "results": [
                {
                    "gate": r.gate_name,
                    "status": r.status.value,
                    "message": r.message,
                    "value": r.value,
                    "threshold": r.threshold,
                }
                for r in self.results
            ],
        }


# =============================================================================
# Gate Implementations
# =============================================================================

class ValidationGate:
    """
    Base class for validation gates.

    Subclasses implement check() to validate pricing results.
    """

    name: str = "base_gate"

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        """
        Check the pricing result.

        Parameters
        ----------
        result : PricingResult
            Pricing result to validate
        **context : Any
            Additional context (product, market params, etc.)

        Returns
        -------
        GateResult
            Validation result
        """
        raise NotImplementedError


class PresentValueBoundsGate(ValidationGate):
    """
    Check that present value is within reasonable bounds.

    [T1] PV should be positive and not unreasonably large.

    Note: As of 2025-12-05, PV clipping was removed from FIA/RILA pricers.
    This gate now catches negative PV that may arise from extreme market
    conditions or model errors. Negative PV indicates:
    - Bug in pricing logic
    - Market params outside reasonable bounds
    - Product with extreme terms (very high floor, very low cap)

    Previously: RILA pricer silently clipped PV to max(0.0, PV)
    Now: Negative PV surfaced here for explicit handling
    """

    name = "present_value_bounds"

    def __init__(
        self,
        min_pv: float = 0.0,
        max_pv_multiple: float = 3.0,
    ):
        """
        Parameters
        ----------
        min_pv : float
            Minimum allowed PV
        max_pv_multiple : float
            Maximum PV as multiple of premium (default 3x)
            [F.4] Reduced from 10x to catch unreasonable valuations earlier
        """
        self.min_pv = min_pv
        self.max_pv_multiple = max_pv_multiple

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        premium = context.get("premium", 100.0)
        max_pv = premium * self.max_pv_multiple

        if result.present_value < self.min_pv:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"PV {result.present_value:.4f} below minimum {self.min_pv}",
                value=result.present_value,
                threshold=self.min_pv,
            )

        if result.present_value > max_pv:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"PV {result.present_value:.4f} exceeds {self.max_pv_multiple}x premium",
                value=result.present_value,
                threshold=max_pv,
            )

        return GateResult(
            status=GateStatus.PASS,
            gate_name=self.name,
            message=f"PV {result.present_value:.4f} within bounds",
            value=result.present_value,
        )


class DurationBoundsGate(ValidationGate):
    """
    Check that duration is within reasonable bounds.

    [T1] Duration should be positive and not exceed term.
    """

    name = "duration_bounds"

    def __init__(
        self,
        max_duration: float = 30.0,
    ):
        """
        Parameters
        ----------
        max_duration : float
            Maximum allowed duration in years
        """
        self.max_duration = max_duration

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        if result.duration is None:
            return GateResult(
                status=GateStatus.PASS,
                gate_name=self.name,
                message="Duration not calculated",
            )

        if result.duration < 0:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"Duration {result.duration:.4f} is negative",
                value=result.duration,
                threshold=0.0,
            )

        if result.duration > self.max_duration:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"Duration {result.duration:.4f} exceeds maximum {self.max_duration}",
                value=result.duration,
                threshold=self.max_duration,
            )

        return GateResult(
            status=GateStatus.PASS,
            gate_name=self.name,
            message=f"Duration {result.duration:.4f} within bounds",
            value=result.duration,
        )


class FIAOptionBudgetGate(ValidationGate):
    """
    Check FIA embedded option value against option budget.

    [T1] Option value should not exceed budget significantly.
    [F.4] Changed from WARN to HALT when budget exceeded by > tolerance.
    """

    name = "fia_option_budget"

    def __init__(
        self,
        tolerance: float = 0.10,  # 10% tolerance [F.4: tightened from 50%]
    ):
        """
        Parameters
        ----------
        tolerance : float
            Allowed excess over budget (0.10 = 10%)
            [F.4] Reduced from 50% to fail fast on budget violations
        """
        self.tolerance = tolerance

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        if not isinstance(result, FIAPricingResult):
            return GateResult(
                status=GateStatus.PASS,
                gate_name=self.name,
                message="Not a FIA result, skipping",
            )

        if result.option_budget <= 0:
            return GateResult(
                status=GateStatus.HALT,  # [F.4] Changed from WARN
                gate_name=self.name,
                message="Option budget is zero or negative",
                value=result.option_budget,
            )

        ratio = result.embedded_option_value / result.option_budget

        if ratio > 1 + self.tolerance:
            return GateResult(
                status=GateStatus.HALT,  # [F.4] Changed from WARN
                gate_name=self.name,
                message=f"Embedded option value {result.embedded_option_value:.4f} "
                        f"exceeds budget {result.option_budget:.4f} by {(ratio-1)*100:.1f}%",
                value=ratio,
                threshold=1 + self.tolerance,
            )

        return GateResult(
            status=GateStatus.PASS,
            gate_name=self.name,
            message=f"Option value within budget (ratio: {ratio:.2f})",
            value=ratio,
        )


class FIAExpectedCreditGate(ValidationGate):
    """
    Check FIA expected credit is non-negative and bounded.

    [T1] FIA has 0% floor, so expected credit >= 0.
    [T1] Expected credit should not exceed cap rate significantly.
    """

    name = "fia_expected_credit"

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        if not isinstance(result, FIAPricingResult):
            return GateResult(
                status=GateStatus.PASS,
                gate_name=self.name,
                message="Not a FIA result, skipping",
            )

        if result.expected_credit < -0.001:  # Small tolerance for numerical error
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"Expected credit {result.expected_credit:.4f} is negative "
                        "(violates 0% floor)",
                value=result.expected_credit,
                threshold=0.0,
            )

        # Get cap from context if available
        cap_rate = context.get("cap_rate")
        if cap_rate is not None and result.expected_credit > cap_rate + 0.02:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"Expected credit {result.expected_credit:.4f} exceeds "
                        f"cap rate {cap_rate:.4f}",
                value=result.expected_credit,
                threshold=cap_rate,
            )

        return GateResult(
            status=GateStatus.PASS,
            gate_name=self.name,
            message=f"Expected credit {result.expected_credit:.4f} within bounds",
            value=result.expected_credit,
        )


class RILAMaxLossGate(ValidationGate):
    """
    Check RILA max loss is consistent with protection type.

    [T1] Buffer: max_loss = 1 - buffer_rate (unlimited beyond buffer)
    [T1] Floor: max_loss = floor_rate (capped loss)
    """

    name = "rila_max_loss"

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        if not isinstance(result, RILAPricingResult):
            return GateResult(
                status=GateStatus.PASS,
                gate_name=self.name,
                message="Not a RILA result, skipping",
            )

        if result.max_loss < 0:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"Max loss {result.max_loss:.4f} is negative",
                value=result.max_loss,
                threshold=0.0,
            )

        if result.max_loss > 1.0:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"Max loss {result.max_loss:.4f} exceeds 100%",
                value=result.max_loss,
                threshold=1.0,
            )

        # Verify consistency with protection type
        buffer_rate = context.get("buffer_rate")
        if buffer_rate is not None:
            if result.protection_type == "buffer":
                expected_max_loss = 1.0 - buffer_rate
                if abs(result.max_loss - expected_max_loss) > 0.01:
                    return GateResult(
                        status=GateStatus.WARN,
                        gate_name=self.name,
                        message=f"Buffer max loss {result.max_loss:.4f} doesn't match "
                                f"expected {expected_max_loss:.4f}",
                        value=result.max_loss,
                        threshold=expected_max_loss,
                    )
            elif result.protection_type == "floor":
                if abs(result.max_loss - buffer_rate) > 0.01:
                    return GateResult(
                        status=GateStatus.WARN,
                        gate_name=self.name,
                        message=f"Floor max loss {result.max_loss:.4f} doesn't match "
                                f"floor rate {buffer_rate:.4f}",
                        value=result.max_loss,
                        threshold=buffer_rate,
                    )

        return GateResult(
            status=GateStatus.PASS,
            gate_name=self.name,
            message=f"Max loss {result.max_loss:.4f} is valid",
            value=result.max_loss,
        )


class RILAProtectionValueGate(ValidationGate):
    """
    Check RILA protection value is positive and bounded.

    [T1] Protection should have positive value.
    [T1] Protection value shouldn't exceed premium significantly.
    """

    name = "rila_protection_value"

    def __init__(
        self,
        max_protection_pct: float = 0.50,  # 50% of premium
    ):
        """
        Parameters
        ----------
        max_protection_pct : float
            Maximum protection value as percentage of premium
        """
        self.max_protection_pct = max_protection_pct

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        if not isinstance(result, RILAPricingResult):
            return GateResult(
                status=GateStatus.PASS,
                gate_name=self.name,
                message="Not a RILA result, skipping",
            )

        if result.protection_value < 0:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"Protection value {result.protection_value:.4f} is negative",
                value=result.protection_value,
                threshold=0.0,
            )

        premium = context.get("premium", 100.0)
        max_protection = premium * self.max_protection_pct

        if result.protection_value > max_protection:
            return GateResult(
                status=GateStatus.WARN,
                gate_name=self.name,
                message=f"Protection value {result.protection_value:.4f} exceeds "
                        f"{self.max_protection_pct*100:.0f}% of premium",
                value=result.protection_value,
                threshold=max_protection,
            )

        return GateResult(
            status=GateStatus.PASS,
            gate_name=self.name,
            message=f"Protection value {result.protection_value:.4f} is valid",
            value=result.protection_value,
        )


class ArbitrageBoundsGate(ValidationGate):
    """
    Check for no-arbitrage violations.

    [T1] Option value <= underlying value (no free money)
    [T1] Protection value <= max potential loss
    """

    name = "arbitrage_bounds"

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        premium = context.get("premium", 100.0)

        if isinstance(result, FIAPricingResult):
            # Check option value doesn't exceed premium
            if result.embedded_option_value > premium:
                return GateResult(
                    status=GateStatus.HALT,
                    gate_name=self.name,
                    message=f"Option value {result.embedded_option_value:.4f} exceeds "
                            f"premium {premium:.4f} (arbitrage violation)",
                    value=result.embedded_option_value,
                    threshold=premium,
                )

        elif isinstance(result, RILAPricingResult):
            # Check protection value doesn't exceed max potential loss
            max_loss_value = premium * result.max_loss if result.max_loss else premium
            if result.protection_value > max_loss_value:
                return GateResult(
                    status=GateStatus.HALT,
                    gate_name=self.name,
                    message=f"Protection value {result.protection_value:.4f} exceeds "
                            f"max loss value {max_loss_value:.4f}",
                    value=result.protection_value,
                    threshold=max_loss_value,
                )

        return GateResult(
            status=GateStatus.PASS,
            gate_name=self.name,
            message="No arbitrage violations detected",
        )


class ProductParameterSanityGate(ValidationGate):
    """
    Check product parameters are within reasonable bounds.

    [F.4] Sanity checks to catch data errors or misentered products.
    These are conservative bounds based on market observations:
    - cap_rate: 0-30% (highest observed caps ~25%)
    - participation_rate: 0-300% (leveraged products exist but rare)
    - buffer_rate: 0-30% (buffers >25% uncommon)
    - spread_rate: 0-10% (spreads >5% uncommon)
    """

    name = "product_parameter_sanity"

    # Sanity bounds [F.4]
    MAX_CAP_RATE = 0.30  # 30%
    MAX_PARTICIPATION_RATE = 3.00  # 300%
    MAX_BUFFER_RATE = 0.30  # 30%
    MAX_SPREAD_RATE = 0.10  # 10%

    def check(self, result: PricingResult, **context: Any) -> GateResult:
        """
        Check product parameters from context.

        Context should include product parameters:
        - cap_rate, participation_rate, buffer_rate, spread_rate
        """
        issues = []

        # Check cap rate
        cap_rate = context.get("cap_rate")
        if cap_rate is not None:
            if cap_rate < 0:
                issues.append(f"cap_rate {cap_rate:.4f} is negative")
            elif cap_rate > self.MAX_CAP_RATE:
                issues.append(
                    f"cap_rate {cap_rate:.4f} exceeds maximum {self.MAX_CAP_RATE:.0%}"
                )

        # Check participation rate
        participation_rate = context.get("participation_rate")
        if participation_rate is not None:
            if participation_rate <= 0:
                issues.append(f"participation_rate {participation_rate:.4f} must be > 0")
            elif participation_rate > self.MAX_PARTICIPATION_RATE:
                issues.append(
                    f"participation_rate {participation_rate:.4f} exceeds maximum "
                    f"{self.MAX_PARTICIPATION_RATE:.0%}"
                )

        # Check buffer rate (used for both buffer and floor protection levels)
        buffer_rate = context.get("buffer_rate")
        if buffer_rate is not None:
            if buffer_rate < 0:
                issues.append(f"buffer_rate {buffer_rate:.4f} is negative")
            elif buffer_rate > self.MAX_BUFFER_RATE:
                issues.append(
                    f"buffer_rate {buffer_rate:.4f} exceeds maximum {self.MAX_BUFFER_RATE:.0%}"
                )

        # Check spread rate
        spread_rate = context.get("spread_rate")
        if spread_rate is not None:
            if spread_rate < 0:
                issues.append(f"spread_rate {spread_rate:.4f} is negative")
            elif spread_rate > self.MAX_SPREAD_RATE:
                issues.append(
                    f"spread_rate {spread_rate:.4f} exceeds maximum {self.MAX_SPREAD_RATE:.0%}"
                )

        if issues:
            return GateResult(
                status=GateStatus.HALT,
                gate_name=self.name,
                message=f"Parameter sanity check failed: {'; '.join(issues)}",
                value=issues,
            )

        return GateResult(
            status=GateStatus.PASS,
            gate_name=self.name,
            message="Product parameters within sanity bounds",
        )


# =============================================================================
# Validation Engine
# =============================================================================

class ValidationEngine:
    """
    Engine for running validation gates on pricing results.

    Combines multiple gates and produces a validation report.

    Parameters
    ----------
    gates : list[ValidationGate], optional
        Custom gates to use. If None, uses default gates.

    Examples
    --------
    >>> engine = ValidationEngine()
    >>> report = engine.validate(pricing_result, premium=100.0)
    >>> if report.passed:
    ...     print("Validation passed")
    >>> else:
    ...     for gate in report.halted_gates:
    ...         print(f"HALT: {gate.message}")
    """

    def __init__(
        self,
        gates: list[ValidationGate] | None = None,
    ):
        if gates is None:
            gates = self._default_gates()
        self.gates = gates

    def _default_gates(self) -> list[ValidationGate]:
        """Create default set of validation gates."""
        return [
            PresentValueBoundsGate(),
            DurationBoundsGate(),
            FIAOptionBudgetGate(),
            FIAExpectedCreditGate(),
            RILAMaxLossGate(),
            RILAProtectionValueGate(),
            ArbitrageBoundsGate(),
            ProductParameterSanityGate(),  # [F.4] Added sanity bounds checking
        ]

    def validate(
        self,
        result: PricingResult,
        **context: Any,
    ) -> ValidationReport:
        """
        Run all validation gates on a pricing result.

        Parameters
        ----------
        result : PricingResult
            Pricing result to validate
        **context : Any
            Additional context for validation

        Returns
        -------
        ValidationReport
            Complete validation report
        """
        results = []
        for gate in self.gates:
            gate_result = gate.check(result, **context)
            results.append(gate_result)

        return ValidationReport(results=tuple(results))

    def validate_and_raise(
        self,
        result: PricingResult,
        **context: Any,
    ) -> PricingResult:
        """
        Validate and raise exception on HALT.

        Parameters
        ----------
        result : PricingResult
            Pricing result to validate
        **context : Any
            Additional context

        Returns
        -------
        PricingResult
            The same result if validation passes

        Raises
        ------
        ValueError
            If any gate HALTs
        """
        report = self.validate(result, **context)

        if not report.passed:
            halt_messages = [g.message for g in report.halted_gates]
            raise ValueError(
                "CRITICAL: Validation failed. HALTs:\n" +
                "\n".join(f"  - {m}" for m in halt_messages)
            )

        return result


# =============================================================================
# Convenience Functions
# =============================================================================

def validate_pricing_result(
    result: PricingResult,
    **context: Any,
) -> ValidationReport:
    """
    Quick validation of a pricing result.

    Parameters
    ----------
    result : PricingResult
        Pricing result to validate
    **context : Any
        Additional context (premium, cap_rate, buffer_rate, etc.)

    Returns
    -------
    ValidationReport
        Validation report

    Examples
    --------
    >>> report = validate_pricing_result(result, premium=100.0)
    >>> if not report.passed:
    ...     print("Validation failed!")
    """
    engine = ValidationEngine()
    return engine.validate(result, **context)


def ensure_valid(
    result: PricingResult,
    **context: Any,
) -> PricingResult:
    """
    Validate and raise if invalid.

    Parameters
    ----------
    result : PricingResult
        Pricing result to validate
    **context : Any
        Additional context

    Returns
    -------
    PricingResult
        The same result if valid

    Raises
    ------
    ValueError
        If validation fails

    Examples
    --------
    >>> valid_result = ensure_valid(result, premium=100.0)
    """
    engine = ValidationEngine()
    return engine.validate_and_raise(result, **context)
