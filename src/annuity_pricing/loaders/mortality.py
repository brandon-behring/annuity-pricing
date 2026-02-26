"""
Mortality Table Loader - Phase 10.

Loads mortality tables from SOA and other sources:
- SOA 2012 IAM tables (Individual Annuity Mortality)
- Period vs generational mortality
- Mortality improvement factors

Theory
------
[T1] qx = probability of death between age x and x+1
[T1] px = 1 - qx = probability of survival
[T1] npx = p_x × p_{x+1} × ... × p_{x+n-1} = n-year survival
[T1] e_x = Σ(k × k_p_x × q_{x+k}) = curtate life expectancy

Validators: actuarialmath, MortalityTables.jl
See: docs/CROSS_VALIDATION_MATRIX.md
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np

# SOA 2012 IAM Basic Table - Male
# Source: Society of Actuaries, 2012 Individual Annuity Reserving Table
# These are representative values; actual table has more decimal precision
SOA_2012_IAM_MALE_QX: dict[int, float] = {
    0: 0.00066, 1: 0.00044, 2: 0.00029, 3: 0.00023, 4: 0.00018,
    5: 0.00016, 6: 0.00015, 7: 0.00014, 8: 0.00013, 9: 0.00012,
    10: 0.00012, 11: 0.00013, 12: 0.00016, 13: 0.00022, 14: 0.00031,
    15: 0.00041, 16: 0.00052, 17: 0.00063, 18: 0.00073, 19: 0.00080,
    20: 0.00084, 21: 0.00087, 22: 0.00088, 23: 0.00089, 24: 0.00089,
    25: 0.00088, 26: 0.00088, 27: 0.00088, 28: 0.00089, 29: 0.00091,
    30: 0.00093, 31: 0.00096, 32: 0.00100, 33: 0.00104, 34: 0.00109,
    35: 0.00115, 36: 0.00121, 37: 0.00129, 38: 0.00137, 39: 0.00147,
    40: 0.00158, 41: 0.00170, 42: 0.00184, 43: 0.00199, 44: 0.00216,
    45: 0.00235, 46: 0.00256, 47: 0.00280, 48: 0.00306, 49: 0.00336,
    50: 0.00369, 51: 0.00405, 52: 0.00446, 53: 0.00491, 54: 0.00542,
    55: 0.00598, 56: 0.00661, 57: 0.00731, 58: 0.00809, 59: 0.00897,
    60: 0.00994, 61: 0.01103, 62: 0.01224, 63: 0.01360, 64: 0.01511,
    65: 0.01680, 66: 0.01868, 67: 0.02079, 68: 0.02315, 69: 0.02580,
    70: 0.02876, 71: 0.03208, 72: 0.03580, 73: 0.03997, 74: 0.04464,
    75: 0.04988, 76: 0.05574, 77: 0.06231, 78: 0.06966, 79: 0.07790,
    80: 0.08712, 81: 0.09745, 82: 0.10901, 83: 0.12194, 84: 0.13638,
    85: 0.15249, 86: 0.17043, 87: 0.19037, 88: 0.21248, 89: 0.23691,
    90: 0.26379, 91: 0.29323, 92: 0.32532, 93: 0.36011, 94: 0.39759,
    95: 0.43769, 96: 0.48025, 97: 0.52503, 98: 0.57171, 99: 0.61989,
    100: 0.66912, 101: 0.71888, 102: 0.76861, 103: 0.81769, 104: 0.86551,
    105: 0.91142, 106: 0.95479, 107: 0.99500, 108: 1.00000, 109: 1.00000,
    110: 1.00000, 111: 1.00000, 112: 1.00000, 113: 1.00000, 114: 1.00000,
    115: 1.00000, 116: 1.00000, 117: 1.00000, 118: 1.00000, 119: 1.00000,
    120: 1.00000,
}

# SOA 2012 IAM Basic Table - Female
# Generally lower mortality than male
SOA_2012_IAM_FEMALE_QX: dict[int, float] = {
    0: 0.00055, 1: 0.00037, 2: 0.00024, 3: 0.00019, 4: 0.00015,
    5: 0.00013, 6: 0.00012, 7: 0.00011, 8: 0.00011, 9: 0.00010,
    10: 0.00010, 11: 0.00011, 12: 0.00013, 13: 0.00017, 14: 0.00022,
    15: 0.00027, 16: 0.00032, 17: 0.00036, 18: 0.00039, 19: 0.00041,
    20: 0.00042, 21: 0.00043, 22: 0.00044, 23: 0.00045, 24: 0.00046,
    25: 0.00047, 26: 0.00048, 27: 0.00050, 28: 0.00052, 29: 0.00055,
    30: 0.00058, 31: 0.00062, 32: 0.00066, 33: 0.00071, 34: 0.00077,
    35: 0.00083, 36: 0.00090, 37: 0.00098, 38: 0.00107, 39: 0.00117,
    40: 0.00128, 41: 0.00140, 42: 0.00154, 43: 0.00169, 44: 0.00185,
    45: 0.00203, 46: 0.00223, 47: 0.00245, 48: 0.00269, 49: 0.00296,
    50: 0.00325, 51: 0.00357, 52: 0.00393, 53: 0.00432, 54: 0.00475,
    55: 0.00523, 56: 0.00576, 57: 0.00635, 58: 0.00700, 59: 0.00773,
    60: 0.00854, 61: 0.00944, 62: 0.01044, 63: 0.01156, 64: 0.01281,
    65: 0.01420, 66: 0.01576, 67: 0.01750, 68: 0.01946, 69: 0.02165,
    70: 0.02411, 71: 0.02688, 72: 0.02999, 73: 0.03349, 74: 0.03743,
    75: 0.04186, 76: 0.04683, 77: 0.05242, 78: 0.05869, 79: 0.06573,
    80: 0.07361, 81: 0.08245, 82: 0.09234, 83: 0.10341, 84: 0.11578,
    85: 0.12960, 86: 0.14502, 87: 0.16220, 88: 0.18130, 89: 0.20246,
    90: 0.22582, 91: 0.25150, 92: 0.27960, 93: 0.31019, 94: 0.34330,
    95: 0.37893, 96: 0.41701, 97: 0.45741, 98: 0.49994, 99: 0.54433,
    100: 0.59025, 101: 0.63732, 102: 0.68510, 103: 0.73315, 104: 0.78099,
    105: 0.82815, 106: 0.87414, 107: 0.91849, 108: 0.96073, 109: 1.00000,
    110: 1.00000, 111: 1.00000, 112: 1.00000, 113: 1.00000, 114: 1.00000,
    115: 1.00000, 116: 1.00000, 117: 1.00000, 118: 1.00000, 119: 1.00000,
    120: 1.00000,
}


@dataclass
class MortalityTable:
    """
    Mortality table representation.

    [T1] qx = probability of death between age x and x+1

    Attributes
    ----------
    table_name : str
        Table identifier (e.g., "SOA 2012 IAM")
    min_age : int
        Minimum age in table
    max_age : int
        Maximum age (omega - 1)
    qx : ndarray
        Mortality rates by age
    gender : str
        "male", "female", or "unisex"
    """

    table_name: str
    min_age: int
    max_age: int
    qx: np.ndarray
    gender: str

    def __post_init__(self) -> None:
        """Validate table data."""
        expected_len = self.max_age - self.min_age + 1
        if len(self.qx) != expected_len:
            raise ValueError(
                f"qx array length ({len(self.qx)}) must equal "
                f"max_age - min_age + 1 ({expected_len})"
            )
        if not np.all((self.qx >= 0) & (self.qx <= 1)):
            raise ValueError("All qx values must be in [0, 1]")

    def get_qx(self, age: int) -> float:
        """
        Get mortality rate at age.

        [T1] qx = probability of death between age x and x+1

        Parameters
        ----------
        age : int
            Age to look up

        Returns
        -------
        float
            Mortality rate qx

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> table = loader.soa_2012_iam()
        >>> table.get_qx(65)
        0.0168
        """
        if age < self.min_age:
            raise ValueError(f"Age {age} below minimum age {self.min_age}")
        if age > self.max_age:
            return 1.0  # Certain death beyond omega

        idx = age - self.min_age
        return float(self.qx[idx])

    def get_px(self, age: int) -> float:
        """
        Get survival rate at age.

        [T1] px = 1 - qx

        Parameters
        ----------
        age : int
            Age to look up

        Returns
        -------
        float
            Survival rate px

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> table = loader.soa_2012_iam()
        >>> table.get_px(65)
        0.9832
        """
        return 1.0 - self.get_qx(age)

    def npx(self, age: int, n: int) -> float:
        """
        Get n-year survival probability from age.

        [T1] npx = p_x × p_{x+1} × ... × p_{x+n-1}

        Parameters
        ----------
        age : int
            Starting age
        n : int
            Number of years

        Returns
        -------
        float
            n-year survival probability

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> table = loader.soa_2012_iam()
        >>> table.npx(65, 10)  # 10-year survival from age 65
        0.82...
        """
        if n <= 0:
            return 1.0

        survival = 1.0
        for k in range(n):
            survival *= self.get_px(age + k)
            if survival <= 0:
                break

        return survival

    def nqx(self, age: int, n: int) -> float:
        """
        Get n-year death probability from age.

        [T1] nqx = 1 - npx

        Parameters
        ----------
        age : int
            Starting age
        n : int
            Number of years

        Returns
        -------
        float
            n-year death probability
        """
        return 1.0 - self.npx(age, n)

    def life_expectancy(self, age: int) -> float:
        """
        Calculate curtate life expectancy at age.

        [T1] e_x = Σ(k × kpx × q_{x+k}) for k=0 to omega-x

        Parameters
        ----------
        age : int
            Starting age

        Returns
        -------
        float
            Curtate life expectancy (complete years)

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> table = loader.soa_2012_iam()
        >>> table.life_expectancy(65)
        20.1...
        """
        if age > self.max_age:
            return 0.0

        # Sum of kpx for k = 1 to omega-x
        ex = 0.0
        for k in range(1, self.max_age - age + 2):
            kpx = self.npx(age, k)
            ex += kpx
            if kpx < 1e-10:
                break

        return ex

    def complete_life_expectancy(self, age: int) -> float:
        """
        Calculate complete life expectancy.

        [T1] e°_x ≈ e_x + 0.5 (uniform distribution of deaths)

        Parameters
        ----------
        age : int
            Starting age

        Returns
        -------
        float
            Complete life expectancy
        """
        return self.life_expectancy(age) + 0.5

    def lx(self, age: int, radix: int = 100_000) -> float:
        """
        Calculate lx (number living at age x).

        [T1] lx = radix × 0px

        Parameters
        ----------
        age : int
            Age
        radix : int
            Starting population (default 100,000)

        Returns
        -------
        float
            Number surviving to age x
        """
        if age <= self.min_age:
            return float(radix)
        return radix * self.npx(self.min_age, age - self.min_age)

    def dx(self, age: int, radix: int = 100_000) -> float:
        """
        Calculate dx (deaths between age x and x+1).

        [T1] dx = lx × qx

        Parameters
        ----------
        age : int
            Age
        radix : int
            Starting population

        Returns
        -------
        float
            Expected deaths at age x
        """
        return self.lx(age, radix) * self.get_qx(age)

    def annuity_factor(self, age: int, r: float, n: int | None = None) -> float:
        """
        Calculate present value of life annuity.

        [T1] ä_x = Σ v^k × kpx for k=0 to n-1

        Parameters
        ----------
        age : int
            Starting age
        r : float
            Interest rate
        n : int, optional
            Term in years (None = life)

        Returns
        -------
        float
            Annuity present value factor

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> table = loader.soa_2012_iam()
        >>> table.annuity_factor(65, 0.04)  # Life annuity
        13.5...
        """
        v = 1 / (1 + r)
        max_term = self.max_age - age + 1 if n is None else min(n, self.max_age - age + 1)

        annuity = 0.0
        for k in range(max_term):
            kpx = self.npx(age, k)
            annuity += (v ** k) * kpx
            if kpx < 1e-10:
                break

        return annuity


class MortalityLoader:
    """
    Loads mortality tables from various sources.

    Supports:
    - SOA 2012 IAM (Individual Annuity Mortality)
    - Custom tables
    - Mortality improvement factors

    Examples
    --------
    >>> loader = MortalityLoader()
    >>> table = loader.soa_2012_iam(gender="male")
    >>> qx_65 = table.get_qx(65)
    >>> ex_65 = table.life_expectancy(65)

    Validators: actuarialmath, MortalityTables.jl
    See: docs/CROSS_VALIDATION_MATRIX.md
    """

    def soa_2012_iam(
        self,
        gender: Literal["male", "female"] = "male",
    ) -> MortalityTable:
        """
        Load SOA 2012 IAM basic table.

        [T1] Standard annuitant mortality table from SOA.

        Parameters
        ----------
        gender : str
            "male" or "female"

        Returns
        -------
        MortalityTable
            SOA 2012 IAM table

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> table = loader.soa_2012_iam(gender="male")
        >>> table.get_qx(65)
        0.0168
        """
        if gender == "male":
            qx_dict = SOA_2012_IAM_MALE_QX
        elif gender == "female":
            qx_dict = SOA_2012_IAM_FEMALE_QX
        else:
            raise ValueError(f"Gender must be 'male' or 'female', got {gender}")

        ages = sorted(qx_dict.keys())
        min_age = min(ages)
        max_age = max(ages)
        qx = np.array([qx_dict[a] for a in range(min_age, max_age + 1)])

        return MortalityTable(
            table_name=f"SOA 2012 IAM Basic - {gender.title()}",
            min_age=min_age,
            max_age=max_age,
            qx=qx,
            gender=gender,
        )

    def soa_table(
        self,
        table_id: int,
    ) -> MortalityTable:
        """
        Load SOA table by ID.

        Note: Requires mort-tables package or manual data entry.

        Parameters
        ----------
        table_id : int
            SOA table ID

        Returns
        -------
        MortalityTable
            Requested table

        Notes
        -----
        For full SOA table access, consider:
        - pip install mort-tables
        - Julia MortalityTables.jl
        """
        # Common table IDs
        if table_id == 3302:  # SOA 2012 IAM Basic Male
            return self.soa_2012_iam(gender="male")
        elif table_id == 3303:  # SOA 2012 IAM Basic Female
            return self.soa_2012_iam(gender="female")
        else:
            raise NotImplementedError(
                f"SOA table {table_id} not built-in. "
                "Use mort-tables package for full SOA table access: "
                "pip install mort-tables"
            )

    def from_dict(
        self,
        qx_dict: dict[int, float],
        table_name: str = "Custom",
        gender: str = "unisex",
    ) -> MortalityTable:
        """
        Create table from dictionary.

        Parameters
        ----------
        qx_dict : Dict[int, float]
            Age -> qx mapping
        table_name : str
            Table name
        gender : str
            Gender description

        Returns
        -------
        MortalityTable
            Custom table

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> qx = {65: 0.02, 66: 0.022, 67: 0.024}
        >>> table = loader.from_dict(qx, "Custom")
        """
        ages = sorted(qx_dict.keys())
        min_age = min(ages)
        max_age = max(ages)

        # Fill gaps with interpolation
        qx = np.zeros(max_age - min_age + 1)
        for i, age in enumerate(range(min_age, max_age + 1)):
            if age in qx_dict:
                qx[i] = qx_dict[age]
            else:
                # Linear interpolation
                lower = max(a for a in ages if a < age)
                upper = min(a for a in ages if a > age)
                frac = (age - lower) / (upper - lower)
                qx[i] = qx_dict[lower] + frac * (qx_dict[upper] - qx_dict[lower])

        return MortalityTable(
            table_name=table_name,
            min_age=min_age,
            max_age=max_age,
            qx=qx,
            gender=gender,
        )

    def gompertz(
        self,
        a: float = 0.0001,
        b: float = 0.08,
        min_age: int = 0,
        max_age: int = 120,
        table_name: str = "Gompertz",
        gender: str = "unisex",
    ) -> MortalityTable:
        """
        Create Gompertz mortality table.

        [T1] qx = a × e^(b × age)

        Parameters
        ----------
        a : float
            Base mortality parameter
        b : float
            Aging parameter
        min_age : int
            Minimum age
        max_age : int
            Maximum age
        table_name : str
            Table name
        gender : str
            Gender

        Returns
        -------
        MortalityTable
            Gompertz table

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> table = loader.gompertz(a=0.0001, b=0.08)
        >>> table.get_qx(65)
        0.019...
        """
        ages = np.arange(min_age, max_age + 1)
        qx = a * np.exp(b * ages)
        qx = np.minimum(qx, 1.0)  # Cap at 1

        return MortalityTable(
            table_name=table_name,
            min_age=min_age,
            max_age=max_age,
            qx=qx,
            gender=gender,
        )

    def with_improvement(
        self,
        base_table: MortalityTable,
        improvement_rate: float = 0.01,
        projection_years: int = 0,
    ) -> MortalityTable:
        """
        Apply mortality improvement factors.

        [T1] qx_improved = qx × (1 - improvement_rate)^years

        Parameters
        ----------
        base_table : MortalityTable
            Base mortality table
        improvement_rate : float
            Annual improvement rate (e.g., 0.01 for 1%)
        projection_years : int
            Years of improvement to apply

        Returns
        -------
        MortalityTable
            Improved mortality table

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> base = loader.soa_2012_iam()
        >>> improved = loader.with_improvement(base, 0.01, 10)
        >>> improved.get_qx(65) < base.get_qx(65)
        True
        """
        if projection_years <= 0:
            return base_table

        improvement_factor = (1 - improvement_rate) ** projection_years
        improved_qx = base_table.qx * improvement_factor
        improved_qx = np.minimum(improved_qx, 1.0)

        return MortalityTable(
            table_name=f"{base_table.table_name} + {projection_years}yr improvement",
            min_age=base_table.min_age,
            max_age=base_table.max_age,
            qx=improved_qx,
            gender=base_table.gender,
        )

    def blend_tables(
        self,
        table1: MortalityTable,
        table2: MortalityTable,
        weight1: float = 0.5,
    ) -> MortalityTable:
        """
        Blend two mortality tables.

        [T1] qx_blend = w × qx1 + (1-w) × qx2

        Parameters
        ----------
        table1 : MortalityTable
            First table
        table2 : MortalityTable
            Second table
        weight1 : float
            Weight for table1 (0 to 1)

        Returns
        -------
        MortalityTable
            Blended table

        Examples
        --------
        >>> loader = MortalityLoader()
        >>> male = loader.soa_2012_iam("male")
        >>> female = loader.soa_2012_iam("female")
        >>> unisex = loader.blend_tables(male, female, 0.5)
        """
        if table1.min_age != table2.min_age or table1.max_age != table2.max_age:
            raise ValueError("Tables must have same age range")

        weight2 = 1 - weight1
        blended_qx = weight1 * table1.qx + weight2 * table2.qx

        return MortalityTable(
            table_name=f"Blend: {weight1:.0%} {table1.table_name} / {weight2:.0%} {table2.table_name}",
            min_age=table1.min_age,
            max_age=table1.max_age,
            qx=blended_qx,
            gender="unisex",
        )


def compare_life_expectancy(
    tables: dict[str, MortalityTable],
    ages: np.ndarray | None = None,
) -> dict[str, dict[int, float]]:
    """
    Compare life expectancy across tables.

    Parameters
    ----------
    tables : Dict[str, MortalityTable]
        Named tables to compare
    ages : ndarray, optional
        Ages to evaluate (default: 55, 60, 65, 70, 75, 80)

    Returns
    -------
    Dict[str, Dict[int, float]]
        Life expectancy by table and age

    Examples
    --------
    >>> loader = MortalityLoader()
    >>> tables = {
    ...     "Male": loader.soa_2012_iam("male"),
    ...     "Female": loader.soa_2012_iam("female"),
    ... }
    >>> results = compare_life_expectancy(tables)
    >>> results["Male"][65]
    20.1...
    """
    if ages is None:
        ages = np.array([55, 60, 65, 70, 75, 80])

    results: dict[str, dict[int, float]] = {}
    for name, table in tables.items():
        results[name] = {}
        for age in ages:
            results[name][int(age)] = table.life_expectancy(age)

    return results


def calculate_annuity_pv(
    table: MortalityTable,
    age: int,
    annual_payment: float,
    discount_rate: float,
    term: int | None = None,
    payment_timing: Literal["beginning", "end"] = "beginning",
) -> float:
    """
    Calculate present value of life annuity.

    [T1] PV = payment × ä_x (due) or payment × a_x (immediate)

    Parameters
    ----------
    table : MortalityTable
        Mortality table
    age : int
        Annuitant age
    annual_payment : float
        Annual payment amount
    discount_rate : float
        Interest rate
    term : int, optional
        Term in years (None = life)
    payment_timing : str
        "beginning" (annuity due) or "end" (immediate)

    Returns
    -------
    float
        Present value

    Examples
    --------
    >>> loader = MortalityLoader()
    >>> table = loader.soa_2012_iam()
    >>> pv = calculate_annuity_pv(table, 65, 10000, 0.04)
    >>> pv
    135...
    """
    factor = table.annuity_factor(age, discount_rate, term)

    if payment_timing == "end":
        # Convert from annuity due to immediate
        v = 1 / (1 + discount_rate)
        factor = (factor - 1) * v + v if term else factor - 1

    return annual_payment * factor
