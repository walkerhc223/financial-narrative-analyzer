"""
Report assembler for the Financial Narrative Analyzer.

This module is responsible for combining narrative sections into one
clean, structured management-style report.
"""


def assemble_report(data, sections):
    """Assemble the final report as a single formatted string."""
    company_name = data["company_name"]
    reporting_period = data["reporting_period"]
    comparison_period = data["comparison_period"]

    report_lines = [
        "FINANCIAL NARRATIVE ANALYZER REPORT",
        "=" * 70,
        f"Company: {company_name}",
        f"Period: {reporting_period} vs {comparison_period}",
        "=" * 70,
        "",
        "EXECUTIVE SUMMARY",
        "-" * 70,
        sections["executive_summary"],
        "",
        "REVENUE COMMENTARY",
        "-" * 70,
        sections["revenue_commentary"],
        "",
        "GROSS PROFIT COMMENTARY",
        "-" * 70,
        sections["gross_profit_commentary"],
        "",
        "OPERATING EXPENSE COMMENTARY",
        "-" * 70,
        sections["operating_expense_commentary"],
        "",
        "OPERATING INCOME CONCLUSION",
        "-" * 70,
        sections["operating_income_conclusion"],
        "",
        "KEY WATCHOUT",
        "-" * 70,
        sections["key_watchout"],
    ]

    return "\n".join(report_lines)