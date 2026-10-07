import pytest

from decision_engine import (
    MATERIALITY_RULE,
    SEMANTIC_REGISTRY,
    analyze_all,
    analyze_variance,
    check_materiality,
)


def test_registry_loads_expected_accounts():
    # Guards the module's import-time YAML load: if semantic_registry.yaml
    # goes missing, is malformed, or a key gets renamed, this fails at
    # collection time instead of silently.
    assert set(SEMANTIC_REGISTRY.keys()) == {"Revenue", "COGS", "SG&A"}

    revenue_rule = SEMANTIC_REGISTRY["Revenue"]
    assert revenue_rule.significant is True
    assert revenue_rule.favorable_when == "increase"
    assert revenue_rule.category == "income"


def test_materiality_thresholds_load_from_yaml():
    # The v2 thresholds come from the YAML, not hardcoded numbers in the code.
    assert MATERIALITY_RULE.pct_change == 0.10
    assert MATERIALITY_RULE.prior_revenue_share == 0.01


def test_analyze_variance_unknown_account_raises():
    with pytest.raises(ValueError):
        analyze_variance("Utilities", current=15_000, prior=10_000)


def test_analyze_variance_classifies_explain_flag_ignore():
    # Revenue: well past both thresholds -> EXPLAIN
    explain_result = analyze_variance("Revenue", current=120_000, prior=100_000)
    assert explain_result.classification == "EXPLAIN"

    # SG&A: dollar change clears min_abs_threshold * flag_proximity (4000)
    # but not the full 5000 threshold, and pct change stays under 10% -> FLAG
    flag_result = analyze_variance("SG&A", current=54_500, prior=50_000)
    assert flag_result.classification == "FLAG"

    # SG&A: small dollar and pct change, below flag proximity -> IGNORE
    ignore_result = analyze_variance("SG&A", current=50_100, prior=50_000)
    assert ignore_result.classification == "IGNORE"


def test_analyze_variance_zero_prior():
    assert analyze_variance("COGS", current=5_000, prior=0).classification == "EXPLAIN"
    assert analyze_variance("COGS", current=0, prior=0).classification == "IGNORE"


def test_analyze_all_rejects_unknown_account():
    with pytest.raises(ValueError):
        analyze_all({"Utilities": {"current": 15_000, "prior": 10_000}})


def test_analyze_all_returns_result_per_account():
    results = analyze_all(
        {
            "Revenue": {"current": 120_000, "prior": 100_000},
            "COGS": {"current": 70_000, "prior": 68_000},
        }
    )
    assert [r.account for r in results] == ["Revenue", "COGS"]


# --- v2 materiality: check_materiality ---
# Thresholds: 10% change, and $ change >= 1% of prior total revenue.
# With prior total revenue = 1,000,000, the dollar floor is $10,000.


def test_materiality_normal_material_case():
    # 20% change and $20,000 change (above the $10,000 floor) -> material
    result = check_materiality(current=120_000, prior=100_000, prior_total_revenue=1_000_000)
    assert result == {"material": True, "sign_flip": False}


def test_materiality_fails_pct_only():
    # 5% change fails the 10% test, but $50,000 clears the $10,000 floor
    result = check_materiality(current=1_050_000, prior=1_000_000, prior_total_revenue=1_000_000)
    assert result == {"material": False, "sign_flip": False}


def test_materiality_fails_dollar_only():
    # 20% change passes the % test, but $4,000 is below the $10,000 floor
    result = check_materiality(current=24_000, prior=20_000, prior_total_revenue=1_000_000)
    assert result == {"material": False, "sign_flip": False}


def test_materiality_prior_zero_dollar_test_decides():
    # Prior = 0: % test passes automatically, so only the dollar test matters
    assert check_materiality(current=15_000, prior=0, prior_total_revenue=1_000_000) == {
        "material": True,
        "sign_flip": False,
    }
    assert check_materiality(current=5_000, prior=0, prior_total_revenue=1_000_000) == {
        "material": False,
        "sign_flip": False,
    }


def test_materiality_prior_revenue_zero_or_negative_raises():
    with pytest.raises(ValueError):
        check_materiality(current=120_000, prior=100_000, prior_total_revenue=0)
    with pytest.raises(ValueError):
        check_materiality(current=120_000, prior=100_000, prior_total_revenue=-5_000)


def test_materiality_sign_flip_uses_absolute_values():
    # Loss of -$50,000 turns into a $20,000 profit: change is $70,000, 140% of |prior|
    result = check_materiality(current=20_000, prior=-50_000, prior_total_revenue=1_000_000)
    assert result == {"material": True, "sign_flip": True}

    # Profit to loss, also flagged as a sign flip
    result = check_materiality(current=-30_000, prior=20_000, prior_total_revenue=1_000_000)
    assert result == {"material": True, "sign_flip": True}


def test_materiality_revenue_tests_against_its_own_prior():
    # Revenue is passed as its own prior total revenue. 13% change and $150,000
    # change, both above the thresholds -> material.
    result = check_materiality(
        current=1_300_000,
        prior=1_150_000,
        prior_total_revenue=1_150_000,
    )
    assert result == {"material": True, "sign_flip": False}

    # Same line, but a 8.7% change fails the 10% test even though the dollars pass
    result = check_materiality(
        current=1_250_000,
        prior=1_150_000,
        prior_total_revenue=1_150_000,
    )
    assert result == {"material": False, "sign_flip": False}
