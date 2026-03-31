"""
Narrative generator for the Financial Narrative Analyzer.

This module is responsible for turning computed metrics and interpretation
results into a structured, management-ready narrative.
"""


def format_currency(value):
    """Format a number as whole-dollar currency."""
    if value is None:
        return "N/A"
    return f"${value:,.0f}"


def format_percent(value):
    """Format a decimal as a percentage with one decimal place."""
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def describe_direction(value, positive_word="increased", negative_word="decreased"):
    """Return directional wording based on sign."""
    if value is None:
        return "changed"
    if value > 0:
        return positive_word
    if value < 0:
        return negative_word
    return "was flat"


def clean_management_context(interpretation):
    """Return cleaner management context text if available."""
    context = interpretation.get("management_context_usage")
    if not context:
        return None

    prefix = "Management context provided: "
    if context.startswith(prefix):
        return context[len(prefix):]

    return context


def generate_executive_summary(data, metrics, interpretation):
    """Generate the executive summary section."""
    company_name = data["company_name"]
    reporting_period = data["reporting_period"]
    comparison_period = data["comparison_period"]

    revenue_direction = describe_direction(metrics.get("revenue_change_abs"))
    operating_income_direction = describe_direction(
        metrics.get("operating_income_change_abs")
    )
    causal_pattern = interpretation.get("causal_pattern", "mixed performance")
    headline = interpretation.get(
        "primary_headline_signal",
        "Performance was mixed during the period",
    )

    sentence_1 = (
        f"{company_name} reported {reporting_period} results versus "
        f"{comparison_period}, with revenue {revenue_direction} and operating "
        f"income {operating_income_direction}."
    )

    sentence_2 = f"The primary headline for the period was that {headline.lower()}."

    sentence_3 = f"Overall, results reflect {causal_pattern.lower()}."

    return f"{sentence_1} {sentence_2} {sentence_3}"


def generate_revenue_commentary(data, metrics, interpretation):
    """Generate revenue commentary."""
    revenue_change_abs = metrics.get("revenue_change_abs")
    revenue_change_pct = metrics.get("revenue_change_pct")
    direction = describe_direction(revenue_change_abs)

    if revenue_change_abs is None or revenue_change_pct is None:
        return "Revenue commentary could not be generated due to incomplete data."

    if revenue_change_abs > 0:
        driver_text = "providing a favorable top-line contribution to the period"
    elif revenue_change_abs < 0:
        driver_text = "creating pressure on overall performance"
    else:
        driver_text = "resulting in a neutral top-line impact"

    return (
        f"Revenue {direction} from {format_currency(data['revenue_prior'])} "
        f"to {format_currency(data['revenue_current'])}, a change of "
        f"{format_currency(abs(revenue_change_abs))} or "
        f"{format_percent(abs(revenue_change_pct))}. This {driver_text}."
    )


def generate_gross_profit_commentary(data, metrics, interpretation):
    """Generate gross profit commentary."""
    gross_profit_change_abs = metrics.get("gross_profit_change_abs")
    gross_profit_change_pct = metrics.get("gross_profit_change_pct")
    gross_margin_change = metrics.get("gross_margin_change")

    if gross_profit_change_abs is None or gross_profit_change_pct is None:
        return "Gross profit commentary could not be generated due to incomplete data."

    direction = describe_direction(gross_profit_change_abs)

    commentary = (
        f"Gross profit {direction} from "
        f"{format_currency(data['gross_profit_prior'])} to "
        f"{format_currency(data['gross_profit_current'])}, a change of "
        f"{format_currency(abs(gross_profit_change_abs))} or "
        f"{format_percent(abs(gross_profit_change_pct))}."
    )

    if gross_margin_change is not None:
        if gross_margin_change > 0:
            margin_text = (
                f" Gross margin improved from "
                f"{format_percent(metrics['gross_margin_prior'])} to "
                f"{format_percent(metrics['gross_margin_current'])}, indicating "
                f"stronger profitability at the gross level."
            )
        elif gross_margin_change < 0:
            margin_text = (
                f" Gross margin declined from "
                f"{format_percent(metrics['gross_margin_prior'])} to "
                f"{format_percent(metrics['gross_margin_current'])}, indicating "
                f"pressure on profitability at the gross level."
            )
        else:
            margin_text = (
                f" Gross margin was unchanged at "
                f"{format_percent(metrics['gross_margin_current'])}."
            )
        commentary += margin_text

    return commentary


def generate_operating_expense_commentary(data, metrics, interpretation):
    """Generate operating expense commentary."""
    operating_expense_change_abs = metrics.get("operating_expense_change_abs")
    operating_expense_change_pct = metrics.get("operating_expense_change_pct")
    context = clean_management_context(interpretation)
    supporting_signals = interpretation.get("supporting_signals", [])

    if operating_expense_change_abs is None or operating_expense_change_pct is None:
        return (
            "Operating expense commentary could not be generated due to incomplete data."
        )

    direction = describe_direction(
        operating_expense_change_abs,
        positive_word="increased",
        negative_word="decreased",
    )

    commentary = (
        f"Operating expenses {direction} from "
        f"{format_currency(data['operating_expense_prior'])} to "
        f"{format_currency(data['operating_expense_current'])}, a change of "
        f"{format_currency(abs(operating_expense_change_abs))} or "
        f"{format_percent(abs(operating_expense_change_pct))}."
    )

    if "Cost pressure from expense growth outpacing revenue" in supporting_signals:
        commentary += (
            " Expense growth outpaced revenue growth, which created pressure on "
            "profitability."
        )
    elif operating_expense_change_abs < 0:
        commentary += " Lower operating expenses supported improved cost discipline."

    if context:
        commentary += f" Management noted that {context[0].lower() + context[1:]}"

    return commentary


def generate_operating_income_conclusion(data, metrics, interpretation):
    """Generate operating income conclusion."""
    operating_income_change_abs = metrics.get("operating_income_change_abs")
    operating_income_change_pct = metrics.get("operating_income_change_pct")
    causal_pattern = interpretation.get("causal_pattern", "mixed performance")

    if operating_income_change_abs is None or operating_income_change_pct is None:
        return (
            "Operating income commentary could not be generated due to incomplete data."
        )

    direction = describe_direction(
        operating_income_change_abs,
        positive_word="increased",
        negative_word="decreased",
    )

    if operating_income_change_abs > 0:
        implication = "This indicates stronger profitability during the period."
    elif operating_income_change_abs < 0:
        implication = (
            "This indicates that cost and margin pressures more than offset any "
            "top-line benefit."
        )
    else:
        implication = "This indicates relatively stable profitability during the period."

    return (
        f"Operating income {direction} from "
        f"{format_currency(data['operating_income_prior'])} to "
        f"{format_currency(data['operating_income_current'])}, a change of "
        f"{format_currency(abs(operating_income_change_abs))} or "
        f"{format_percent(abs(operating_income_change_pct))}. "
        f"{implication} The overall pattern was {causal_pattern.lower()}."
    )


def generate_key_watchout(metrics, interpretation):
    """Generate an optional key watchout."""
    supporting_signals = interpretation.get("supporting_signals", [])
    unfavorable_signals = interpretation.get("unfavorable_signals", [])

    if "Cost pressure from expense growth outpacing revenue" in supporting_signals:
        return (
            "Operating expenses are growing faster than revenue, which should be "
            "monitored closely if top-line growth moderates."
        )

    if "Weak profitability conversion" in supporting_signals:
        return (
            "Revenue growth is not converting efficiently into operating income, "
            "suggesting the need to monitor cost structure and margin performance."
        )

    if "Operating margin compressed" in unfavorable_signals:
        return (
            "Operating margin compression should remain a focus area, as it may "
            "signal reduced profitability efficiency."
        )

    return "Continue monitoring margin performance and expense discipline in future periods."


def generate_narrative_sections(data, metrics, interpretation):
    """Generate all narrative sections."""
    return {
        "executive_summary": generate_executive_summary(
            data,
            metrics,
            interpretation,
        ),
        "revenue_commentary": generate_revenue_commentary(
            data,
            metrics,
            interpretation,
        ),
        "gross_profit_commentary": generate_gross_profit_commentary(
            data,
            metrics,
            interpretation,
        ),
        "operating_expense_commentary": generate_operating_expense_commentary(
            data,
            metrics,
            interpretation,
        ),
        "operating_income_conclusion": generate_operating_income_conclusion(
            data,
            metrics,
            interpretation,
        ),
        "key_watchout": generate_key_watchout(
            metrics,
            interpretation,
        ),
    }