"""
Financial Narrative Analyzer - V1

Goal:
- hardcode example input data
- compute financial metrics
- interpret the computed metrics
- generate a structured narrative
- assemble a final report
- print the final report
"""

from computation import compute_metrics
from interpretation import interpret_metrics
from narrative import generate_narrative_sections
from assembly import assemble_report
from decision_engine import analyze_all


def main():
    """Run the Financial Narrative Analyzer V1 pipeline."""

    input_data = {
        "company_name": "ABC Health Services",
        "reporting_period": "Q1 2026",
        "comparison_period": "Q1 2025",
        "revenue_current": 1_250_000,
        "revenue_prior": 1_150_000,
        "gross_profit_current": 430_000,
        "gross_profit_prior": 410_000,
        "operating_expense_current": 300_000,
        "operating_expense_prior": 275_000,
        "operating_income_current": 130_000,
        "operating_income_prior": 135_000,
    }

    # Registry-level accounts derived from the aggregate inputs so the two
    # views cannot drift apart. COGS = revenue - gross profit.
    account_data = {
        "Revenue": {
            "current": input_data["revenue_current"],
            "prior": input_data["revenue_prior"],
        },
        "COGS": {
            "current": input_data["revenue_current"] - input_data["gross_profit_current"],
            "prior": input_data["revenue_prior"] - input_data["gross_profit_prior"],
        },
        "SG&A": {
            "current": input_data["operating_expense_current"],
            "prior": input_data["operating_expense_prior"],
        },
    }

    management_notes = "Labor and software costs increased during the quarter."

    metrics = compute_metrics(input_data)
    variance_results = analyze_all(account_data)

    interpretation = interpret_metrics(
        metrics,
        management_notes=management_notes,
        materiality_threshold_pct=0.05,
        materiality_threshold_abs=10_000,
        variance_results=variance_results,
    )

    narrative_sections = generate_narrative_sections(
        input_data,
        metrics,
        interpretation,
    )

    final_report = assemble_report(input_data, narrative_sections)

    print(final_report)


if __name__ == "__main__":
    main()