from computation import compute_metrics

sample_data = {
    "revenue_current": 950_000,
    "revenue_prior": 1_050_000,
    "gross_profit_current": 360_000,
    "gross_profit_prior": 380_000,
    "operating_expense_current": 210_000,
    "operating_expense_prior": 260_000,
    "operating_income_current": 150_000,
    "operating_income_prior": 120_000,
}


def test_revenue_change():
    result = compute_metrics(sample_data)
    assert result["revenue_change_abs"] == -100_000
    assert round(result["revenue_change_pct"], 4) == -0.0952


def test_margins_and_ratios():
    result = compute_metrics(sample_data)
    assert round(result["gross_margin_current"], 4) == 0.3789
    assert round(result["operating_margin_current"], 4) == 0.1579
    assert round(result["operating_expense_ratio_current"], 4) == 0.2211


def test_gross_profit_change():
    result = compute_metrics(sample_data)
    assert result["gross_profit_change_abs"] == -20_000
    assert round(result["gross_profit_change_pct"], 4) == -0.0526


def test_operating_expense_change():
    result = compute_metrics(sample_data)
    assert result["operating_expense_change_abs"] == -50_000
    assert round(result["operating_expense_change_pct"], 4) == -0.1923


def test_operating_income_change():
    result = compute_metrics(sample_data)
    assert result["operating_income_change_abs"] == 30_000
    assert round(result["operating_income_change_pct"], 4) == 0.25


def test_revenue_vs_opex_growth_gap():
    result = compute_metrics(sample_data)
    assert round(result["revenue_change_pct"], 4) == -0.0952
    assert round(result["operating_expense_change_pct"], 4) == -0.1923
    expected_gap = result["revenue_change_pct"] - result["operating_expense_change_pct"]
    assert result["revenue_vs_opex_growth_gap"] == expected_gap
    assert round(result["revenue_vs_opex_growth_gap"], 4) == 0.0971


def test_revenue_vs_operating_income_growth_gap():
    result = compute_metrics(sample_data)
    assert round(result["revenue_change_pct"], 4) == -0.0952
    assert round(result["operating_income_change_pct"], 4) == 0.25
    expected_gap = result["revenue_change_pct"] - result["operating_income_change_pct"]
    assert result["revenue_vs_operating_income_growth_gap"] == expected_gap
    assert round(result["revenue_vs_operating_income_growth_gap"], 4) == -0.3452


def test_gross_profit_vs_revenue_growth_gap():
    result = compute_metrics(sample_data)
    assert round(result["gross_profit_change_pct"], 4) == -0.0526
    assert round(result["revenue_change_pct"], 4) == -0.0952
    expected_gap = result["gross_profit_change_pct"] - result["revenue_change_pct"]
    assert result["gross_profit_vs_revenue_growth_gap"] == expected_gap
    assert round(result["gross_profit_vs_revenue_growth_gap"], 4) == 0.0426


def test_zero_prior_revenue_returns_none():
    data = {
        **sample_data,
        "revenue_prior": 0,
        "gross_profit_prior": 0,
        "operating_expense_prior": 0,
        "operating_income_prior": 0,
    }
    result = compute_metrics(data)
    assert result["revenue_change_pct"] is None
    assert result["gross_margin_prior"] is None
    assert result["operating_margin_change"] is None
    assert result["revenue_vs_opex_growth_gap"] is None
    assert result["revenue_vs_operating_income_growth_gap"] is None
    assert result["gross_profit_vs_revenue_growth_gap"] is None

def test_breakeven_prior_operating_income():
    data = {**sample_data, "operating_income_prior": 0}
    result = compute_metrics(data)

    # Subtraction is unaffected by the zero prior
    assert result["operating_income_change_abs"] == 150_000

    # Growth from a zero base is undefined, not zero
    assert result["operating_income_change_pct"] is None

    # Zero is the numerator here, so the division is valid:
    # the company genuinely broke even at a 0.0% operating margin
    assert result["operating_margin_prior"] == 0.0
    assert round(result["operating_margin_change"], 4) == 0.1579

    # None propagates only to the gap that depends on it
    assert result["revenue_vs_operating_income_growth_gap"] is None

    # ...and stops there: this gap never touches operating income
    assert round(result["revenue_vs_opex_growth_gap"], 4) == 0.0971
    
    
    