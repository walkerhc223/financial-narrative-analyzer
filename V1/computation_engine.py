"""
Computation engine for the Financial Narrative Analyzer.

This module is responsible for transforming raw financial inputs
into computed financial metrics.
"""


def safe_divide(numerator, denominator):
    """Safely divide two numbers. Return None if denominator is zero."""
    if denominator == 0:
        return None
    return numerator / denominator


def compute_metrics(data):
    """Compute core financial metrics from raw input data."""
    metrics = {}

    # Absolute changes
    metrics["revenue_change_abs"] = (
        data["revenue_current"] - data["revenue_prior"]
    )
    metrics["gross_profit_change_abs"] = (
        data["gross_profit_current"] - data["gross_profit_prior"]
    )
    metrics["operating_expense_change_abs"] = (
        data["operating_expense_current"] - data["operating_expense_prior"]
    )
    metrics["operating_income_change_abs"] = (
        data["operating_income_current"] - data["operating_income_prior"]
    )

    # Percentage changes
    metrics["revenue_change_pct"] = safe_divide(
        metrics["revenue_change_abs"],
        data["revenue_prior"],
    )
    metrics["gross_profit_change_pct"] = safe_divide(
        metrics["gross_profit_change_abs"],
        data["gross_profit_prior"],
    )
    metrics["operating_expense_change_pct"] = safe_divide(
        metrics["operating_expense_change_abs"],
        data["operating_expense_prior"],
    )
    metrics["operating_income_change_pct"] = safe_divide(
        metrics["operating_income_change_abs"],
        data["operating_income_prior"],
    )

    # Margins
    metrics["gross_margin_current"] = safe_divide(
        data["gross_profit_current"],
        data["revenue_current"],
    )
    metrics["gross_margin_prior"] = safe_divide(
        data["gross_profit_prior"],
        data["revenue_prior"],
    )
    metrics["gross_margin_change"] = (
        None
        if metrics["gross_margin_current"] is None
        or metrics["gross_margin_prior"] is None
        else metrics["gross_margin_current"] - metrics["gross_margin_prior"]
    )

    metrics["operating_margin_current"] = safe_divide(
        data["operating_income_current"],
        data["revenue_current"],
    )
    metrics["operating_margin_prior"] = safe_divide(
        data["operating_income_prior"],
        data["revenue_prior"],
    )
    metrics["operating_margin_change"] = (
        None
        if metrics["operating_margin_current"] is None
        or metrics["operating_margin_prior"] is None
        else metrics["operating_margin_current"] - metrics["operating_margin_prior"]
    )

    # Expense ratio
    metrics["operating_expense_ratio_current"] = safe_divide(
        data["operating_expense_current"],
        data["revenue_current"],
    )
    metrics["operating_expense_ratio_prior"] = safe_divide(
        data["operating_expense_prior"],
        data["revenue_prior"],
    )
    metrics["operating_expense_ratio_change"] = (
        None
        if metrics["operating_expense_ratio_current"] is None
        or metrics["operating_expense_ratio_prior"] is None
        else metrics["operating_expense_ratio_current"]
        - metrics["operating_expense_ratio_prior"]
    )

    # Growth-gap signals
    metrics["revenue_vs_opex_growth_gap"] = (
        None
        if metrics["revenue_change_pct"] is None
        or metrics["operating_expense_change_pct"] is None
        else metrics["revenue_change_pct"] - metrics["operating_expense_change_pct"]
    )

    metrics["revenue_vs_operating_income_growth_gap"] = (
        None
        if metrics["revenue_change_pct"] is None
        or metrics["operating_income_change_pct"] is None
        else metrics["revenue_change_pct"] - metrics["operating_income_change_pct"]
    )

    metrics["gross_profit_vs_revenue_growth_gap"] = (
        None
        if metrics["gross_profit_change_pct"] is None
        or metrics["revenue_change_pct"] is None
        else metrics["gross_profit_change_pct"] - metrics["revenue_change_pct"]
    )

    return metrics