from querycreator.core.query.formatter import ResultFormatter

def test_format_rows_to_table():
    rows = [{"ORDER_NO": "A001", "CUST_CD": "C100"}, {"ORDER_NO": "A002", "CUST_CD": "C200"}]
    f = ResultFormatter()
    output = f.format_for_llm(rows)
    assert "A001" in output
    assert "ORDER_NO" in output

def test_format_empty_result():
    f = ResultFormatter()
    output = f.format_for_llm([])
    assert "0건" in output

def test_format_with_code_translation():
    rows = [{"PROC_CD": "010", "WEIGHT": 150.5}, {"PROC_CD": "020", "WEIGHT": 145.2}]
    code_map = {"PROC_CD": {"010": "원료투입", "020": "가열"}}
    f = ResultFormatter(code_mappings=code_map)
    output = f.format_for_llm(rows)
    assert "원료투입" in output
    assert "가열" in output

def test_format_large_result_truncated():
    rows = [{"ID": i, "VAL": f"value_{i}"} for i in range(2000)]
    f = ResultFormatter(max_display_rows=100)
    output = f.format_for_llm(rows)
    assert "100" in output

def test_format_summary_included():
    rows = [{"ORDER_NO": "A001", "WEIGHT": 100}, {"ORDER_NO": "A002", "WEIGHT": 200}]
    f = ResultFormatter()
    output = f.format_for_llm(rows)
    assert "2건" in output
