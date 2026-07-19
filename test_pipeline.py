from computation import compute_metrics

def test_revenue_change_summit_care():
    data = {
        "revenue_current": 950_000,
        "revenue_prior": 1_050_000,
        "gross_profit_current": 360_000,
        "gross_profit_prior": 380_000,
        "operating_expense_current": 210_000,
        "operating_expense_prior": 260_000,
        "operating_income_current": 150_000,
        "operating_income_prior": 120_000,
    }
    result = compute_metrics(data)
    assert result["revenue_change_abs"] == -100_000
    assert round(result["revenue_change_pct"], 4) == -0.0952