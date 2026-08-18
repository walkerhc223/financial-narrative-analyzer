from interpretation import (
    apply_causal_pattern_rules,
    determine_primary_headline_signal,
    interpret_metrics,
    is_material,
)


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


def test_materiality_and_causal_pattern(sample_metrics):
    interpretation = interpret_metrics(sample_metrics)

    assert interpretation["material_signals"] == [
        "Revenue",
        "Gross profit",
        "Operating expense",
        "Operating income",
    ]
    assert interpretation["causal_pattern"] == "Lower revenue with improved cost discipline"

    # is_material: materiality via pct alone, via abs alone, and below both thresholds
    assert is_material(abs_change=5_000, pct_change=0.10, threshold_pct=0.05, threshold_abs=10_000)
    assert is_material(abs_change=15_000, pct_change=0.01, threshold_pct=0.05, threshold_abs=10_000)
    assert not is_material(abs_change=1_000, pct_change=0.01, threshold_pct=0.05, threshold_abs=10_000)
    assert not is_material(abs_change=None, pct_change=None, threshold_pct=0.05, threshold_abs=10_000)

    # causal pattern falls back when required inputs are missing
    interpretation_missing = {"causal_pattern": None}
    apply_causal_pattern_rules(
        {"revenue_change_abs": None, "operating_income_change_abs": 1},
        interpretation_missing,
    )
    assert interpretation_missing["causal_pattern"] == "Insufficient data to determine pattern"


def test_headline_signal_and_management_context(sample_metrics):
    interpretation = interpret_metrics(sample_metrics, management_notes="Labor costs rose.")

    assert interpretation["primary_headline_signal"] == "Profitability improved during the period"
    assert interpretation["management_context_usage"] == "Labor costs rose."

    no_notes_interpretation = interpret_metrics(sample_metrics)
    assert no_notes_interpretation["management_context_usage"] is None

    # revenue-driven headline when operating income isn't material
    revenue_only = {"material_signals": ["Revenue"]}
    determine_primary_headline_signal({"revenue_change_abs": -1}, revenue_only)
    assert revenue_only["primary_headline_signal"] == "Revenue decline was the main driver of performance"

    # neither material -> mixed fallback
    neither = {"material_signals": []}
    determine_primary_headline_signal({}, neither)
    assert neither["primary_headline_signal"] == "Performance was mixed during the period"
