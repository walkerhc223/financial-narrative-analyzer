from computation import compute_metrics
from interpretation import interpret_metrics
from narrative import (
    generate_executive_summary,
    generate_gross_profit_commentary,
    generate_operating_expense_commentary,
    generate_operating_income_conclusion,
    generate_revenue_commentary,
)
from test_interpretation import _registry_from_yaml_edits


def _data(**overrides):
    # Revenue up, gross margin down (35.7% -> 34.4%), SG&A up, operating income down.
    return {
        "company_name": "Sample Co",
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
        **overrides,
    }


def _build(data, registry=None):
    metrics = compute_metrics(data)
    return metrics, interpret_metrics(metrics, registry=registry)


def test_flipping_revenue_and_gross_margin_flips_narrative_judgments(tmp_path):
    data = _data()
    metrics, before = _build(data)
    assert "This provided a favorable top-line contribution" in generate_revenue_commentary(data, metrics, before)
    assert "pressure on profitability at the gross level" in generate_gross_profit_commentary(data, metrics, before)
    assert "with gross margin pressure" in before["causal_pattern"]

    def edit(raw):
        raw["accounts"]["Revenue"].update(favorable_when="decrease")
        raw["derived_lines"]["Gross margin"].update(favorable_when="decrease")

    registry = _registry_from_yaml_edits(tmp_path, edit)
    metrics, after = _build(data, registry)

    revenue = generate_revenue_commentary(data, metrics, after)
    assert "This created pressure on overall performance." in revenue
    assert "favorable top-line" not in revenue

    gross = generate_gross_profit_commentary(data, metrics, after)
    assert "Gross margin declined from 35.7% to 34.4%, indicating stronger profitability at the gross level." in gross
    assert "pressure on profitability" not in gross

    assert "gross margin pressure" not in generate_executive_summary(data, metrics, after)


def test_sga_dollars_up_share_down_reads_favorable():
    data = _data(
        revenue_prior=1_000_000, revenue_current=1_200_000,
        operating_expense_prior=200_000, operating_expense_current=210_000,
    )
    metrics, interpretation = _build(data)
    text = generate_operating_expense_commentary(data, metrics, interpretation)
    assert "Operating expenses increased from" in text
    assert "Operating expenses fell as a share of revenue, supporting cost discipline." in text


def test_sga_unfavorable_sentence():
    data = _data()
    metrics, interpretation = _build(data)
    text = generate_operating_expense_commentary(data, metrics, interpretation)
    assert "Expense growth outpaced revenue growth, which created pressure on profitability." in text


def test_sga_flat_share_reads_neutral():
    data = _data(
        revenue_prior=1_000_000, revenue_current=1_200_000,
        operating_expense_prior=200_000, operating_expense_current=240_000,
    )
    metrics, interpretation = _build(data)
    assert interpretation["line_verdicts"]["SG&A"]["verdict"] == "flat"
    text = generate_operating_expense_commentary(data, metrics, interpretation)
    assert text.endswith("Operating expenses held steady as a share of revenue.")


def test_sga_undetermined_share_gives_factual_sentence_only():
    data = _data(revenue_current=0)
    metrics, interpretation = _build(data)
    assert interpretation["line_verdicts"]["SG&A"]["verdict"] == "undetermined"
    text = generate_operating_expense_commentary(data, metrics, interpretation)
    assert text.endswith("%.")
    for phrase in ("share of revenue", "outpaced", "cost discipline"):
        assert phrase not in text


def test_operating_income_implication_follows_verdict(tmp_path):
    data = _data()
    metrics, interpretation = _build(data)
    assert "cost and margin pressures more than offset" in generate_operating_income_conclusion(
        data, metrics, interpretation
    )

    registry = _registry_from_yaml_edits(
        tmp_path, lambda raw: raw["derived_lines"]["Operating income"].update(favorable_when="decrease")
    )
    metrics, flipped = _build(data, registry)
    assert "This indicates stronger profitability during the period." in generate_operating_income_conclusion(
        data, metrics, flipped
    )


def test_flat_and_undetermined_verdicts_for_other_lines():
    data = _data(gross_profit_current=410_000, gross_profit_prior=410_000)
    metrics, interpretation = _build(data)
    interpretation["line_verdicts"]["Operating income"]["verdict"] = "flat"
    assert "relatively stable profitability" in generate_operating_income_conclusion(data, metrics, interpretation)
    interpretation["line_verdicts"]["Operating income"]["verdict"] = "undetermined"
    text = generate_operating_income_conclusion(data, metrics, interpretation)
    assert "This indicates" not in text
    assert "The overall pattern was" in text

    interpretation["line_verdicts"]["Revenue"]["verdict"] = "flat"
    assert "neutral top-line impact" in generate_revenue_commentary(data, metrics, interpretation)
    interpretation["line_verdicts"]["Revenue"]["verdict"] = "undetermined"
    assert generate_revenue_commentary(data, metrics, interpretation).endswith("%.")

    interpretation["line_verdicts"]["Gross margin"]["verdict"] = "undetermined"
    gross = generate_gross_profit_commentary(data, metrics, interpretation)
    assert gross.endswith("to 32.8%.") and "indicating" not in gross
    interpretation["line_verdicts"]["Gross margin"]["verdict"] = "flat"
    assert "Gross margin was unchanged at" in generate_gross_profit_commentary(data, metrics, interpretation)


def test_executive_summary_grammar_for_flat():
    data = _data(revenue_current=1_150_000)
    metrics, interpretation = _build(data)
    summary = generate_executive_summary(data, metrics, interpretation)
    assert "versus Q1 2025: revenue was flat and operating income decreased." in summary
