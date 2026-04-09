"""Tests for SQL query validator."""
from querycreator.core.query.validator import QueryValidator, ValidationResult
from querycreator.config.safety_rules import SafetyRules


def make_validator(large_tables=None, forbidden_patterns=None):
    rules = SafetyRules()
    if forbidden_patterns:
        rules.forbidden_patterns = forbidden_patterns
    return QueryValidator(rules=rules, table_row_counts=large_tables or {})


# Allowed:
def test_simple_select_passes():
    v = make_validator()
    r = v.validate("SELECT order_no, cust_cd FROM tb_order WHERE order_no = 'A001'")
    assert r.is_valid


def test_select_with_rownum_passes():
    v = make_validator()
    r = v.validate("SELECT col1 FROM tb_small WHERE ROWNUM <= 100")
    assert r.is_valid


def test_select_with_fetch_first_passes():
    v = make_validator()
    r = v.validate("SELECT col1 FROM tb_x FETCH FIRST 50 ROWS ONLY")
    assert r.is_valid


def test_subquery_passes():
    v = make_validator()
    r = v.validate(
        "SELECT a.order_no FROM tb_order a "
        "WHERE a.cust_cd IN (SELECT cust_cd FROM tb_cust WHERE active = 'Y') "
        "AND ROWNUM <= 100"
    )
    assert r.is_valid


def test_with_clause_passes():
    v = make_validator()
    r = v.validate(
        "WITH orders AS (SELECT order_no FROM tb_order WHERE status = '01') "
        "SELECT order_no FROM orders WHERE ROWNUM <= 100"
    )
    assert r.is_valid


# Blocked:
def test_insert_blocked():
    v = make_validator()
    r = v.validate("INSERT INTO tb_order VALUES ('X', 'Y', SYSDATE)")
    assert not r.is_valid
    assert "SELECT" in r.reason


def test_update_blocked():
    v = make_validator()
    r = v.validate("UPDATE tb_order SET status_cd = '03' WHERE order_no = 'A001'")
    assert not r.is_valid


def test_delete_blocked():
    v = make_validator()
    r = v.validate("DELETE FROM tb_order WHERE order_no = 'A001'")
    assert not r.is_valid


def test_drop_blocked():
    v = make_validator()
    r = v.validate("DROP TABLE tb_order")
    assert not r.is_valid


def test_select_star_blocked():
    v = make_validator()
    r = v.validate("SELECT * FROM tb_order WHERE order_no = 'A001'")
    assert not r.is_valid


def test_leading_wildcard_blocked():
    v = make_validator()
    r = v.validate("SELECT order_no FROM tb_order WHERE cust_cd LIKE '%ABC'")
    assert not r.is_valid


def test_large_table_without_where_blocked():
    v = make_validator(large_tables={"TB_PROD_PROGRESS": 5_000_000})
    r = v.validate("SELECT order_no, weight FROM tb_prod_progress FETCH FIRST 100 ROWS ONLY")
    assert not r.is_valid


def test_large_table_with_where_passes():
    v = make_validator(large_tables={"TB_PROD_PROGRESS": 5_000_000})
    r = v.validate(
        "SELECT order_no, weight FROM tb_prod_progress "
        "WHERE prod_date >= DATE '2026-01-01' FETCH FIRST 100 ROWS ONLY"
    )
    assert r.is_valid


def test_forbidden_pattern_blocked():
    v = make_validator(forbidden_patterns=["CROSS JOIN"])
    r = v.validate("SELECT a.x, b.y FROM tb_a a CROSS JOIN tb_b b WHERE ROWNUM <= 10")
    assert not r.is_valid


def test_no_row_limit_adds_warning():
    v = make_validator()
    r = v.validate("SELECT order_no FROM tb_order WHERE order_no = 'A001'")
    assert r.is_valid
    assert r.row_limit_missing


def test_function_call_passes():
    v = make_validator()
    r = v.validate("SELECT * FROM TABLE(F_SUM_PROGRESS('A001'))")
    assert r.is_valid


def test_empty_query_blocked():
    v = make_validator()
    r = v.validate("")
    assert not r.is_valid


def test_multiple_statements_blocked():
    v = make_validator()
    r = v.validate("SELECT 1 FROM dual; DROP TABLE tb_order")
    assert not r.is_valid
