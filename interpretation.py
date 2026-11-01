"""
Interpretation engine for the Financial Narrative Analyzer.

This module is responsible for converting computed financial metrics
into structured financial signals before narrative generation.
"""

import decision_engine


def interpret_metrics(
    metrics,
    management_notes=None,
    materiality_results=None,
    variance_results=None,
    registry=None,
):
    """Interpret computed financial metrics into structured signals."""
    interpretation = {
        "favorable_signals": [],
        "unfavorable_signals": [],
        "supporting_signals": [],
        "material_signals": [],
        "sign_flip_signals": [],
        "line_verdicts": {},
        "registry_classifications": {},
        "flagged_accounts": [],
        "causal_pattern": None,
        "primary_headline_signal": None,
        "management_context_usage": None,
    }

    interpretation["line_verdicts"] = build_line_verdicts(
        metrics, registry, materiality_results, variance_results
    )
    apply_directional_rules(interpretation)
    apply_relative_growth_rules(metrics, interpretation)
    apply_materiality_rules(interpretation, materiality_results)
    apply_registry_classifications(variance_results, interpretation)
    apply_causal_pattern_rules(metrics, interpretation)
    determine_primary_headline_signal(metrics, interpretation)
    apply_management_context(interpretation, management_notes)

    return interpretation


# Wiring from each reported line to its metric keys and signal strings. Verdicts are NOT
# decided here: favorable_when comes from the registry. `prefix` is None for ratio lines,
# which use `current`/`prior`/`change` metric keys directly. `signals` is (up, down).
_LINES = [
    {"name": "Revenue", "prefix": "revenue", "signals": ("Revenue increased", "Revenue decreased")},
    {"name": "COGS", "prefix": "cogs", "signals": None},
    {
        "name": "SG&A",
        "prefix": "operating_expense",
        "share_metric": "operating_expense_ratio_change",
        "signals": ("Operating expenses increased", "Operating expenses decreased"),
    },
    {"name": "Gross profit", "prefix": "gross_profit", "signals": ("Gross profit increased", "Gross profit decreased")},
    {
        "name": "Operating income",
        "prefix": "operating_income",
        "signals": ("Operating income increased", "Operating income decreased"),
    },
    {
        "name": "Gross margin",
        "ratio": "gross_margin",
        "signals": ("Gross margin expanded", "Gross margin compressed"),
    },
    {
        "name": "Operating margin",
        "ratio": "operating_margin",
        "signals": ("Operating margin expanded", "Operating margin compressed"),
    },
]

# The order signal strings have always been emitted in.
_SIGNAL_ORDER = [
    "Revenue",
    "Gross profit",
    "SG&A",
    "Operating income",
    "Gross margin",
    "Operating margin",
]


def _default_registry():
    return {"accounts": decision_engine.SEMANTIC_REGISTRY, "derived_lines": decision_engine.DERIVED_LINES}


def _direction(change):
    if change is None:
        return None
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return "flat"


def build_line_verdicts(metrics, registry=None, materiality_results=None, variance_results=None):
    """Build one complete record per reported line; every verdict comes from the registry."""
    registry = registry or _default_registry()
    materiality_results = materiality_results or {}
    classifications = {r.account: r.classification for r in (variance_results or [])}

    records = {}
    for line in _LINES:
        name = line["name"]
        rule = registry["accounts"].get(name) or registry["derived_lines"][name]

        if "ratio" in line:
            ratio = line["ratio"]
            current = metrics.get(f"{ratio}_current")
            prior = metrics.get(f"{ratio}_prior")
            dollar_change = metrics.get(f"{ratio}_change")
            pct_change = None
        else:
            prefix = line["prefix"]
            current = metrics.get(f"{prefix}_current")
            prior = metrics.get(f"{prefix}_prior")
            dollar_change = metrics.get(f"{prefix}_change_abs")
            pct_change = metrics.get(f"{prefix}_change_pct")

        if rule.favorable_when == "lower_share_of_revenue":
            if "share_metric" not in line:
                raise ValueError(f"'{name}': no share-of-revenue metric for favorable_when 'lower_share_of_revenue'")
            verdict_change = metrics.get(line["share_metric"])
        else:
            verdict_change = dollar_change

        materiality = materiality_results.get(name)
        records[name] = {
            "current": current,
            "prior": prior,
            "dollar_change": dollar_change,
            "pct_change": pct_change,
            "direction": _direction(dollar_change),
            "favorable_when": rule.favorable_when,
            "verdict": decision_engine.directional_verdict(rule.favorable_when, verdict_change),
            "classification": classifications.get(name),
            "material": materiality["material"] if materiality else None,
            "sign_flip": materiality["sign_flip"] if materiality else None,
            "interpretation_hint": rule.interpretation_hint,
        }
    return records


def apply_directional_rules(interpretation):
    """Derive the favorable/unfavorable signal lists from line_verdicts."""
    line_verdicts = interpretation["line_verdicts"]

    signals = {line["name"]: line["signals"] for line in _LINES}
    for name in _SIGNAL_ORDER:
        record = line_verdicts[name]
        if record["direction"] not in ("up", "down"):
            continue
        up, down = signals[name]
        text = up if record["direction"] == "up" else down
        if record["verdict"] == "favorable":
            interpretation["favorable_signals"].append(text)
        elif record["verdict"] == "unfavorable":
            interpretation["unfavorable_signals"].append(text)


def apply_relative_growth_rules(metrics, interpretation):
    """Interpret important relationships between growth rates."""
    revenue_change_pct = metrics.get("revenue_change_pct")
    operating_expense_change_pct = metrics.get("operating_expense_change_pct")
    gross_profit_change_pct = metrics.get("gross_profit_change_pct")
    operating_income_change_pct = metrics.get("operating_income_change_pct")

    if (
        revenue_change_pct is not None
        and operating_expense_change_pct is not None
    ):
        if revenue_change_pct > operating_expense_change_pct:
            interpretation["supporting_signals"].append(
                "Positive operating leverage"
            )
        elif operating_expense_change_pct > revenue_change_pct:
            interpretation["supporting_signals"].append(
                "Cost pressure from expense growth outpacing revenue"
            )

    if gross_profit_change_pct is not None and revenue_change_pct is not None:
        if gross_profit_change_pct < revenue_change_pct:
            interpretation["supporting_signals"].append(
                "Gross profit growth lagged revenue growth"
            )
        elif gross_profit_change_pct > revenue_change_pct:
            interpretation["supporting_signals"].append(
                "Gross profit growth outpaced revenue growth"
            )

    if operating_income_change_pct is not None and revenue_change_pct is not None:
        if operating_income_change_pct < revenue_change_pct:
            interpretation["supporting_signals"].append(
                "Weak profitability conversion"
            )
        elif operating_income_change_pct > revenue_change_pct:
            interpretation["supporting_signals"].append(
                "Improving operational efficiency"
            )


def apply_materiality_rules(interpretation, materiality_results):
    """Identify which signals are material, using the decision engine's v2 rule."""
    if not materiality_results:
        return

    # Maps account names to the signal names used in the narrative.
    # Accounts not listed here (e.g. COGS) are skipped.
    account_to_signal = {
        "Revenue": "Revenue",
        "Gross profit": "Gross profit",
        "SG&A": "Operating expense",
        "Operating income": "Operating income",
    }

    for account, result in materiality_results.items():
        signal = account_to_signal.get(account)
        if signal is None:
            continue

        if result["material"]:
            interpretation["material_signals"].append(signal)
        # Sign flips are recorded for the narrative layer, whether or not the line is material.
        if result["sign_flip"]:
            interpretation["sign_flip_signals"].append(signal)


def apply_registry_classifications(variance_results, interpretation):
    """Record registry-driven per-account classifications from the decision engine."""
    if not variance_results:
        return

    for result in variance_results:
        interpretation["registry_classifications"][result.account] = result.classification
        if result.classification == "FLAG":
            interpretation["flagged_accounts"].append(result.account)


def apply_causal_pattern_rules(metrics, interpretation):
    """Detect high-level business performance patterns."""
    revenue_change_abs = metrics.get("revenue_change_abs")
    operating_income_change_abs = metrics.get("operating_income_change_abs")
    operating_expense_change_pct = metrics.get("operating_expense_change_pct")
    revenue_change_pct = metrics.get("revenue_change_pct")

    if revenue_change_abs is None or operating_income_change_abs is None:
        interpretation["causal_pattern"] = "Insufficient data to determine pattern"
        return

    if revenue_change_abs > 0 and operating_income_change_abs > 0:
        interpretation["causal_pattern"] = "Growth with improved profitability"
    elif revenue_change_abs > 0 and operating_income_change_abs < 0:
        interpretation["causal_pattern"] = "Growth offset by cost pressure"
    elif revenue_change_abs < 0 and operating_income_change_abs < 0:
        interpretation["causal_pattern"] = "Broad performance deterioration"
    elif revenue_change_abs < 0 and operating_income_change_abs > 0:
        interpretation["causal_pattern"] = "Lower revenue with improved cost discipline"
    else:
        interpretation["causal_pattern"] = "Mixed performance pattern"

    if interpretation["line_verdicts"]["Gross margin"]["verdict"] == "unfavorable":
        interpretation["causal_pattern"] += " with gross margin pressure"

    if (
        revenue_change_pct is not None
        and operating_expense_change_pct is not None
        and operating_expense_change_pct > revenue_change_pct
    ):
        interpretation["causal_pattern"] += " and expense growth outpacing revenue"


def determine_primary_headline_signal(metrics, interpretation):
    """Choose the main headline signal for the period."""
    material_signals = interpretation["material_signals"]

    if "Operating income" in material_signals:
        if metrics["operating_income_change_abs"] > 0:
            interpretation["primary_headline_signal"] = (
                "Profitability improved during the period"
            )
            return
        if metrics["operating_income_change_abs"] < 0:
            interpretation["primary_headline_signal"] = (
                "Profitability weakened during the period"
            )
            return

    if "Revenue" in material_signals:
        if metrics["revenue_change_abs"] > 0:
            interpretation["primary_headline_signal"] = (
                "Revenue growth was the main driver of performance"
            )
            return
        if metrics["revenue_change_abs"] < 0:
            interpretation["primary_headline_signal"] = (
                "Revenue decline was the main driver of performance"
            )
            return

    interpretation["primary_headline_signal"] = "Performance was mixed during the period"


def apply_management_context(interpretation, management_notes):
    """Attach management notes only as contextual support."""
    if management_notes:
        interpretation["management_context_usage"] = management_notes