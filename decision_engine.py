from __future__ import annotations

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Classification = Literal["EXPLAIN", "FLAG", "IGNORE"]
FavorableWhen = Literal["increase", "decrease", "depends"]
Category = Literal["income", "expense", "opex"]

_REGISTRY_PATH = Path(__file__).parent / "semantic_registry.yaml"


@dataclass
class AccountRule:
    significant: bool
    favorable_when: FavorableWhen
    flag_proximity: float
    category: Category
    interpretation_hint: str


@dataclass
class MaterialityRule:
    pct_change: float            # e.g. 0.10 = 10% change vs prior
    prior_revenue_share: float   # e.g. 0.01 = 1% of prior-period total revenue


@dataclass
class VarianceResult:
    account: str
    current: float
    prior: float
    dollar_change: float
    pct_change: float | None
    classification: Classification
    favorable_when: FavorableWhen
    category: Category
    interpretation_hint: str
    significant: bool


def _load_registry(path: Path = _REGISTRY_PATH) -> dict[str, AccountRule]:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    return {
        name: AccountRule(**fields)
        for name, fields in raw["accounts"].items()
    }


SEMANTIC_REGISTRY: dict[str, AccountRule] = _load_registry()


def _load_materiality(path: Path = _REGISTRY_PATH) -> MaterialityRule:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    # Thresholds live in the YAML so they can change without touching code.
    return MaterialityRule(**raw["materiality"])


MATERIALITY_RULE: MaterialityRule = _load_materiality()


def _passes_flag_proximity(
    abs_change: float,
    abs_pct: float | None,
    prior_total_revenue: float,
    rule: AccountRule,
    materiality: MaterialityRule = MATERIALITY_RULE,
) -> bool:
    # Same thresholds as check_materiality(), scaled down by the account's flag_proximity.
    dollar_floor = materiality.prior_revenue_share * prior_total_revenue
    if abs_change >= dollar_floor * rule.flag_proximity:
        return True
    # A prior of zero has no % change, so only the dollar bar can flag it.
    return abs_pct is not None and abs_pct >= materiality.pct_change * rule.flag_proximity


def _classify(
    current: float,
    prior: float,
    dollar_change: float,
    pct_change: float | None,
    prior_total_revenue: float,
    rule: AccountRule,
) -> Classification:
    if check_materiality(current, prior, prior_total_revenue)["material"]:
        return "EXPLAIN"

    abs_pct = abs(pct_change) if pct_change is not None else None
    if _passes_flag_proximity(abs(dollar_change), abs_pct, prior_total_revenue, rule):
        return "FLAG"

    return "IGNORE"


def analyze_variance(account: str, current: float, prior: float, prior_total_revenue: float) -> VarianceResult:
    rule = SEMANTIC_REGISTRY.get(account)
    if rule is None:
        raise ValueError(f"No semantic rule found for account: '{account}'")

    dollar_change = current - prior
    pct_change = dollar_change / prior if prior != 0 else None

    classification = _classify(current, prior, dollar_change, pct_change, prior_total_revenue, rule)

    return VarianceResult(
        account=account,
        current=current,
        prior=prior,
        dollar_change=dollar_change,
        pct_change=pct_change,
        classification=classification,
        favorable_when=rule.favorable_when,
        category=rule.category,
        interpretation_hint=rule.interpretation_hint,
        significant=rule.significant,
    )


def check_materiality(
    current: float,
    prior: float,
    prior_total_revenue: float,
    rule: MaterialityRule = MATERIALITY_RULE,
) -> dict[str, bool]:
    """Apply the v2 P&L materiality rule to one line.

    Returns {"material": bool, "sign_flip": bool}.
    """
    # The dollar test is a share of revenue, so zero or negative revenue makes it meaningless.
    if prior_total_revenue <= 0:
        raise ValueError(
            f"Prior-period total revenue must be positive for materiality checks, got {prior_total_revenue}"
        )

    # Use absolute values for both tests, so a decrease counts the same as an increase.
    dollar_change = abs(current - prior)

    # A prior of zero has no meaningful % change, so the % test passes automatically
    # and only the dollar test decides.
    if prior == 0:
        pct_passes = True
    else:
        # Divide by abs(prior) so a negative prior doesn't flip the sign of the % test.
        pct_passes = dollar_change / abs(prior) >= rule.pct_change

    dollar_passes = dollar_change >= rule.prior_revenue_share * prior_total_revenue

    # Opposite signs (e.g. a loss turning into a profit). The narrative layer needs to know.
    sign_flip = (current > 0 and prior < 0) or (current < 0 and prior > 0)

    return {"material": pct_passes and dollar_passes, "sign_flip": sign_flip}


def analyze_all(financials: dict[str, dict[str, float]]) -> list[VarianceResult]:
    """
    financials: {"Revenue": {"current": 120000, "prior": 100000}, ...}
    """
    errors: list[str] = []
    for account, periods in financials.items():
        if account not in SEMANTIC_REGISTRY:
            errors.append(f"'{account}': no semantic rule found")
        if not isinstance(periods, dict):
            errors.append(f"'{account}': expected a dict with 'current' and 'prior', got {type(periods).__name__}")
            continue
        for key in ("current", "prior"):
            if key not in periods:
                errors.append(f"'{account}': missing required key '{key}'")
            elif not isinstance(periods[key], (int, float)):
                errors.append(f"'{account}.{key}': expected a number, got {type(periods[key]).__name__}")

    # Materiality is measured against prior-period total revenue, so Revenue must be present.
    if "Revenue" not in financials:
        errors.append("'Revenue': required to measure materiality against prior-period total revenue")

    if errors:
        raise ValueError("Invalid input to analyze_all:\n" + "\n".join(f"  - {e}" for e in errors))

    prior_total_revenue = financials["Revenue"]["prior"]

    return [
        analyze_variance(account, periods["current"], periods["prior"], prior_total_revenue)
        for account, periods in financials.items()
    ]
