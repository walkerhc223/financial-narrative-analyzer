from computation import compute_metrics
from decision_engine import check_materiality
from interpretation import (
    apply_causal_pattern_rules,
    apply_materiality_rules,
    determine_primary_headline_signal,
    interpret_metrics,
)


def sample_materiality_results(sample_input_data):
    # Same account setup as main.py: COGS = revenue - gross profit.
    prior_total_revenue = sample_input_data["revenue_prior"]
    accounts = {
        "Revenue": (sample_input_data["revenue_current"], sample_input_data["revenue_prior"]),
        "COGS": (
            sample_input_data["revenue_current"] - sample_input_data["gross_profit_current"],
            sample_input_data["revenue_prior"] - sample_input_data["gross_profit_prior"],
        ),
        "SG&A": (
            sample_input_data["operating_expense_current"],
            sample_input_data["operating_expense_prior"],
        ),
    }
    accounts["Gross profit"] = (
        sample_input_data["gross_profit_current"],
        sample_input_data["gross_profit_prior"],
    )
    accounts["Operating income"] = (
        sample_input_data["operating_income_current"],
        sample_input_data["operating_income_prior"],
    )
    return {
        name: check_materiality(current, prior, prior_total_revenue)
        for name, (current, prior) in accounts.items()
    }


def test_directional_and_relative_growth_rules(sample_metrics):
    interpretation = interpret_metrics(sample_metrics)

    assert interpretation["favorable_signals"] == [
        "Operating expenses decreased",
        "Operating income increased",
        "Gross margin expanded",
        "Operating margin expanded",
    ]
    assert interpretation["unfavorable_signals"] == [
        "Revenue decreased",
        "Gross profit decreased",
    ]
    assert interpretation["supporting_signals"] == [
        "Positive operating leverage",
        "Gross profit growth outpaced revenue growth",
        "Improving operational efficiency",
    ]


def test_improving_loss_is_improving_operational_efficiency(sample_input_data):
    # Operating loss shrinking from -20 to -10 while revenue grows 20%.
    data = {
        **sample_input_data,
        "revenue_prior": 100,
        "revenue_current": 120,
        "operating_income_prior": -20,
        "operating_income_current": -10,
    }
    metrics = compute_metrics(data)
    assert metrics["operating_income_change_pct"] == 0.5

    interpretation = interpret_metrics(metrics)
    assert "Improving operational efficiency" in interpretation["supporting_signals"]
    assert "Weak profitability conversion" not in interpretation["supporting_signals"]


def test_materiality_and_causal_pattern(sample_metrics, sample_input_data):
    materiality_results = sample_materiality_results(sample_input_data)
    interpretation = interpret_metrics(sample_metrics, materiality_results=materiality_results)

    # Revenue moved -9.5% (fails the 10% test); Gross profit moved -5.3% (fails);
    # SG&A and Operating income pass both tests.
    assert interpretation["material_signals"] == ["Operating expense", "Operating income"]
    assert interpretation["sign_flip_signals"] == []
    assert interpretation["causal_pattern"] == "Lower revenue with improved cost discipline"

    # causal pattern falls back when required inputs are missing
    interpretation_missing = {"causal_pattern": None}
    apply_causal_pattern_rules(
        {"revenue_change_abs": None, "operating_income_change_abs": 1},
        interpretation_missing,
    )
    assert interpretation_missing["causal_pattern"] == "Insufficient data to determine pattern"


def test_apply_materiality_rules_maps_accounts_to_signals():
    interpretation = {"material_signals": []}
    apply_materiality_rules(
        interpretation,
        {
            "Revenue": {"material": True, "sign_flip": False},
            "COGS": {"material": False, "sign_flip": False},
            "SG&A": {"material": True, "sign_flip": False},
        },
    )
    assert interpretation["material_signals"] == ["Revenue", "Operating expense"]

    # sign flips are recorded even when the line is not material
    flipped = {"material_signals": [], "sign_flip_signals": []}
    apply_materiality_rules(
        flipped,
        {"Gross profit": {"material": False, "sign_flip": True}},
    )
    assert flipped["material_signals"] == []
    assert flipped["sign_flip_signals"] == ["Gross profit"]

    # unknown accounts are skipped rather than raising KeyError
    unknown = {"material_signals": [], "sign_flip_signals": []}
    apply_materiality_rules(
        unknown,
        {"Utilities": {"material": True, "sign_flip": True}},
    )
    assert unknown["material_signals"] == []
    assert unknown["sign_flip_signals"] == []

    # no results supplied -> nothing is material
    empty = {"material_signals": []}
    apply_materiality_rules(empty, None)
    assert empty["material_signals"] == []


def test_headline_signal_and_management_context(sample_metrics, sample_input_data):
    materiality_results = sample_materiality_results(sample_input_data)
    interpretation = interpret_metrics(
        sample_metrics,
        management_notes="Labor costs rose.",
        materiality_results=materiality_results,
    )

    assert interpretation["primary_headline_signal"] == "Profitability improved during the period"
    assert interpretation["management_context_usage"] == "Labor costs rose."

    no_notes_interpretation = interpret_metrics(sample_metrics)
    assert no_notes_interpretation["management_context_usage"] is None

    # revenue-driven headline when revenue is material
    revenue_only = {"material_signals": ["Revenue"]}
    determine_primary_headline_signal({"revenue_change_abs": -1}, revenue_only)
    assert revenue_only["primary_headline_signal"] == "Revenue decline was the main driver of performance"

    # neither material -> mixed fallback
    neither = {"material_signals": []}
    determine_primary_headline_signal({}, neither)
    assert neither["primary_headline_signal"] == "Performance was mixed during the period"
