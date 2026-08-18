from main import main


def test_main_end_to_end_report(capsys):
    main()
    captured = capsys.readouterr()

    assert "FINANCIAL NARRATIVE ANALYZER REPORT" in captured.out
    assert "ABC Health Services" in captured.out
    for header in [
        "EXECUTIVE SUMMARY",
        "REVENUE COMMENTARY",
        "GROSS PROFIT COMMENTARY",
        "OPERATING EXPENSE COMMENTARY",
        "OPERATING INCOME CONCLUSION",
        "KEY WATCHOUT",
    ]:
        assert header in captured.out
