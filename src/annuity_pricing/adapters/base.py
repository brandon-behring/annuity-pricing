"""
Base adapter interface for validation against external libraries.

All adapters should inherit from BaseAdapter and implement the required methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of validating our implementation against an external library.

    Attributes
    ----------
    our_value : float
        Value computed by our implementation
    external_value : float
        Value computed by external library
    difference : float
        Absolute difference (our_value - external_value)
    passed : bool
        Whether difference is within tolerance
    tolerance : float
        Tolerance threshold used
    validator_name : str
        Name of the external library used
    test_case : str, optional
        Description of the test case
    """

    our_value: float
    external_value: float
    difference: float
    passed: bool
    tolerance: float
    validator_name: str
    test_case: Optional[str] = None

    @property
    def pct_difference(self) -> float:
        """Percentage difference relative to external value."""
        if self.external_value == 0:
            return float("inf") if self.our_value != 0 else 0.0
        return abs(self.difference / self.external_value) * 100


class BaseAdapter(ABC):
    """
    Abstract base class for external validation adapters.

    Subclasses must implement:
    - name property
    - is_available property
    - _install_hint property
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the external library."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the external library is installed and importable."""
        ...

    @property
    @abstractmethod
    def _install_hint(self) -> str:
        """Install command hint (e.g., 'pip install financepy')."""
        ...

    def require_available(self) -> None:
        """
        Raise ImportError with install hint if library not available.

        Raises
        ------
        ImportError
            If the external library is not installed
        """
        if not self.is_available:
            raise ImportError(
                f"{self.name} not installed. "
                f"Install with: {self._install_hint}"
            )

    def validate(
        self,
        our_value: float,
        external_value: float,
        tolerance: float = 0.01,
        test_case: Optional[str] = None,
    ) -> ValidationResult:
        """
        Create a ValidationResult comparing our value to external.

        Parameters
        ----------
        our_value : float
            Value from our implementation
        external_value : float
            Value from external library
        tolerance : float
            Maximum allowed difference
        test_case : str, optional
            Description of test case

        Returns
        -------
        ValidationResult
            Comparison result with pass/fail status
        """
        difference = our_value - external_value
        passed = abs(difference) <= tolerance

        return ValidationResult(
            our_value=our_value,
            external_value=external_value,
            difference=difference,
            passed=passed,
            tolerance=tolerance,
            validator_name=self.name,
            test_case=test_case,
        )
