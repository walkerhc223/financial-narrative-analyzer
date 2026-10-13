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


def _threshold_tests(
    current: float,
    prior: float,
    prior_total_revenue: float,
    scale: float,
    materiality: MaterialityRule = MATERIALITY_RULE,
) -> tuple[bool | None, bool]:
    """The one place the materiality thresholds are evaluated.

    Returns (pct_ok, dollar_ok), with both thresholds multiplied by `scale`
    (1 for materiality, flag_proximity for FLAG). pct_ok is None when the prior
    is zero, since there is no % change; each caller decides what that means.
    """
    # The dollar test is a share of revenue, so zero or negative revenue makes it meaningless.
    if prior_total_revenue <= 0:
        raise ValueError(
            f"Prior-period total revenue must be positive for materiality checks, got {prior_total_revenue}"
        )

    # Use absolute values for both tests, so a decrease counts the same as an increase.
    dollar_change = abs(current - prior)

    if prior == 0:
        pct_ok = None
    else:
        # Divide by abs(prior) so a negative prior doesn't flip the sign of the % test.
        pct_ok = dollar_change / abs(prior) >= materiality.pct_change * scale

    dollar_ok = dollar_change >= materiality.prior_revenue_share * prior_total_revenue * scale

    return pct_ok, dollar_ok


def _classify(current: float, prior: float, prior_total_revenue: float, rule: AccountRule) -> Classification:
    if check_materiality(current, prior, prior_total_revenue)["material"]:
        return "EXPLAIN"

    # FLAG needs either test at flag_proximity x its threshold. With a zero prior (pct_ok is None)
    # there is no % change, so the % test can't trigger a FLAG and only the dollar test can.
    pct_ok, dollar_ok = _threshold_tests(current, prior, prior_total_revenue, rule.flag_proximity)
    if pct_ok is True or dollar_ok:
        return "FLAG"

    return "IGNORE"


def analyze_variance(account: str, current: float, prior: float, prior_total_revenue: float) -> VarianceResult:
    rule = SEMANTIC_REGISTRY.get(account)
    if rule is None:
        raise ValueError(f"No semantic rule found for account: '{account}'")

    dollar_change = current - prior
    # abs(prior) keeps the sign of the % change aligned with the direction of the move.
    pct_change = dollar_change / abs(prior) if prior != 0 else None

    classification = _classify(current, prior, prior_total_revenue, rule)

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
    pct_ok, dollar_ok = _threshold_tests(current, prior, prior_total_revenue, scale=1, materiality=rule)

    # A prior of zero has no meaningful % change, so the % test passes automatically
    # and only the dollar test decides.
    pct_passes = pct_ok is None or pct_ok

    # Opposite signs (e.g. a loss turning into a profit). The narrative layer needs to know.
    sign_flip = (current > 0 and prior < 0) or (current < 0 and prior > 0)

    return {"material": pct_passes and dollar_ok, "sign_flip": sign_flip}


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

    revenue = financials.get("Revenue")
    if isinstance(revenue, dict) and isinstance(revenue.get("prior"), (int, float)) and revenue["prior"] <= 0:
        errors.append(f"'Revenue.prior': must be positive to measure materiality, got {revenue['prior']}")

    if errors:
        raise ValueError("Invalid input to analyze_all:\n" + "\n".join(f"  - {e}" for e in errors))

    prior_total_revenue = financials["Revenue"]["prior"]

    return [
        analyze_variance(account, periods["current"], periods["prior"], prior_total_revenue)
        for account, periods in financials.items()
    ]
