import pytest

from decision_engine import SEMANTIC_REGISTRY, analyze_all, analyze_variance


def test_registry_loads_expected_accounts():
    # Guards the module's import-time YAML load: if semantic_registry.yaml
    # goes missing, is malformed, or a key gets renamed, this fails at
    # collection time instead of silently.
    assert set(SEMANTIC_REGISTRY.keys()) == {"Revenue", "COGS", "SG&A"}

    revenue_rule = SEMANTIC_REGISTRY["Revenue"]
    assert revenue_rule.significant is True
    assert revenue_rule.favorable_when == "increase"
    assert revenue_rule.category == "income"


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
