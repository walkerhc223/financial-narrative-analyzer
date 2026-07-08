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
    min_abs_threshold: float
    pct_threshold: float
    flag_proximity: float
    category: Category
    interpretation_hint: str


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


def _passes_explain_threshold(abs_change: float, abs_pct: float, rule: AccountRule) -> bool:
    return abs_change >= rule.min_abs_threshold and abs_pct >= rule.pct_threshold


def _passes_flag_proximity(abs_change: float, abs_pct: float, rule: AccountRule) -> bool:
    return (
        abs_change >= rule.min_abs_threshold * rule.flag_proximity
        or abs_pct >= rule.pct_threshold * rule.flag_proximity
    )


def _classify(current: float, prior: float, dollar_change: float, pct_change: float | None, rule: AccountRule) -> Classification:
    if prior == 0:
        return "EXPLAIN" if current != 0 else "IGNORE"

    abs_change = abs(dollar_change)
    abs_pct = abs(pct_change)

    if _passes_explain_threshold(abs_change, abs_pct, rule):
        return "EXPLAIN"

    if _passes_flag_proximity(abs_change, abs_pct, rule):
        return "FLAG"

    return "IGNORE"


def analyze_variance(account: str, current: float, prior: float) -> VarianceResult:
    rule = SEMANTIC_REGISTRY.get(account)
    if rule is None:
        raise ValueError(f"No semantic rule found for account: '{account}'")

    dollar_change = current - prior
    pct_change = dollar_change / prior if prior != 0 else None

    classification = _classify(current, prior, dollar_change, pct_change, rule)

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

    if errors:
        raise ValueError("Invalid input to analyze_all:\n" + "\n".join(f"  - {e}" for e in errors))

    return [
        analyze_variance(account, periods["current"], periods["prior"])
        for account, periods in financials.items()
    ]
