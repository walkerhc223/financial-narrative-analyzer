"""
Interpretation engine for the Financial Narrative Analyzer.

This module is responsible for converting computed financial metrics
into structured financial signals before narrative generation.
"""


def interpret_metrics(
    metrics,
    management_notes=None,
    materiality_threshold_pct=0.05,
    materiality_threshold_abs=10_000,
):
    """Interpret computed financial metrics into structured signals."""
    interpretation = {
        "favorable_signals": [],
        "unfavorable_signals": [],
        "supporting_signals": [],
        "material_signals": [],
        "causal_pattern": None,
        "primary_headline_signal": None,
        "management_context_usage": None,
    }

    apply_directional_rules(metrics, interpretation)
    apply_relative_growth_rules(metrics, interpretation)
    apply_materiality_rules(
        metrics,
        interpretation,
        materiality_threshold_pct,
        materiality_threshold_abs,
    )
    apply_causal_pattern_rules(metrics, interpretation)
    determine_primary_headline_signal(metrics, interpretation)
    apply_management_context(interpretation, management_notes)

    return interpretation


def apply_directional_rules(metrics, interpretation):
    """Classify basic directional changes as favorable or unfavorable."""
    if metrics["revenue_change_abs"] > 0:
        interpretation["favorable_signals"].append("Revenue increased")
    elif metrics["revenue_change_abs"] < 0:
        interpretation["unfavorable_signals"].append("Revenue decreased")

    if metrics["gross_profit_change_abs"] > 0:
        interpretation["favorable_signals"].append("Gross profit increased")
    elif metrics["gross_profit_change_abs"] < 0:
        interpretation["unfavorable_signals"].append("Gross profit decreased")

    if metrics["operating_expense_change_abs"] > 0:
        interpretation["unfavorable_signals"].append("Operating expenses increased")
    elif metrics["operating_expense_change_abs"] < 0:
        interpretation["favorable_signals"].append("Operating expenses decreased")

    if metrics["operating_income_change_abs"] > 0:
        interpretation["favorable_signals"].append("Operating income increased")
    elif metrics["operating_income_change_abs"] < 0:
        interpretation["unfavorable_signals"].append("Operating income decreased")

    gross_margin_change = metrics.get("gross_margin_change")
    if gross_margin_change is not None:
        if gross_margin_change > 0:
            interpretation["favorable_signals"].append("Gross margin expanded")
        elif gross_margin_change < 0:
            interpretation["unfavorable_signals"].append("Gross margin compressed")

    operating_margin_change = metrics.get("operating_margin_change")
    if operating_margin_change is not None:
        if operating_margin_change > 0:
            interpretation["favorable_signals"].append("Operating margin expanded")
        elif operating_margin_change < 0:
            interpretation["unfavorable_signals"].append("Operating margin compressed")


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


def apply_materiality_rules(
    metrics,
    interpretation,
    materiality_threshold_pct,
    materiality_threshold_abs,
):
    """Identify which signals are material enough to emphasize."""
    metric_definitions = [
        (
            "Revenue",
            metrics.get("revenue_change_abs"),
            metrics.get("revenue_change_pct"),
        ),
        (
            "Gross profit",
            metrics.get("gross_profit_change_abs"),
            metrics.get("gross_profit_change_pct"),
        ),
        (
            "Operating expense",
            metrics.get("operating_expense_change_abs"),
            metrics.get("operating_expense_change_pct"),
        ),
        (
            "Operating income",
            metrics.get("operating_income_change_abs"),
            metrics.get("operating_income_change_pct"),
        ),
    ]

    for metric_name, abs_change, pct_change in metric_definitions:
        if is_material(
            abs_change,
            pct_change,
            materiality_threshold_pct,
            materiality_threshold_abs,
        ):
            interpretation["material_signals"].append(metric_name)


def is_material(abs_change, pct_change, threshold_pct, threshold_abs):
    """Return True if a change is materially significant."""
    if abs_change is not None and abs(abs_change) >= threshold_abs:
        return True

    if pct_change is not None and abs(pct_change) >= threshold_pct:
        return True

    return False


def apply_causal_pattern_rules(metrics, interpretation):
    """Detect high-level business performance patterns."""
    revenue_change_abs = metrics.get("revenue_change_abs")
    operating_income_change_abs = metrics.get("operating_income_change_abs")
    gross_margin_change = metrics.get("gross_margin_change")
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

    if gross_margin_change is not None and gross_margin_change < 0:
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