import pytest

from computation import compute_metrics
from interpretation import interpret_metrics


@pytest.fixture
def sample_input_data():
    return {
        "company_name": "Sample Co",
        "reporting_period": "Q1 2026",
        "comparison_period": "Q1 2025",
        "revenue_current": 950_000,
        "revenue_prior": 1_050_000,
        "gross_profit_current": 360_000,
        "gross_profit_prior": 380_000,
        "operating_expense_current": 210_000,
        "operating_expense_prior": 260_000,
        "operating_income_current": 150_000,
        "operating_income_prior": 120_000,
    }


@pytest.fixture
def sample_metrics(sample_input_data):
    return compute_metrics(sample_input_data)


@pytest.fixture
def sample_interpretation(sample_metrics):
    return interpret_metrics(
        sample_metrics,
        management_notes="Labor and software costs increased during the quarter.",
    )
