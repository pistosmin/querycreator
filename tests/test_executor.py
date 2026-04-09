from querycreator.core.query.executor import QueryExecutor, ExecutionResult
from querycreator.core.query.validator import QueryValidator
from querycreator.config.safety_rules import SafetyRules
from querycreator.db.mock_connection import MockConnection

def make_executor(mock_db):
    rules = SafetyRules()
    validator = QueryValidator(rules=rules, table_row_counts={})
    return QueryExecutor(db=mock_db, validator=validator, rules=rules)

def test_execute_valid_query(mock_db):
    executor = make_executor(mock_db)
    result = executor.execute("SELECT order_no, cust_cd FROM tb_order WHERE order_no = 'A001'")
    assert result.success
    assert result.rows is not None

def test_execute_invalid_query_returns_error(mock_db):
    executor = make_executor(mock_db)
    result = executor.execute("DELETE FROM tb_order")
    assert not result.success
    assert "SELECT" in result.error

def test_execute_returns_execution_time(mock_db):
    executor = make_executor(mock_db)
    result = executor.execute("SELECT order_no FROM tb_order WHERE order_no = 'A001'")
    assert result.execution_time_ms >= 0

def test_execute_function_call(mock_db):
    executor = make_executor(mock_db)
    result = executor.execute_function("F_SUM_PROGRESS", {"P_ORDER_NO": "A001"})
    assert result.success
    assert len(result.rows) > 0

def test_execute_unknown_function(mock_db):
    executor = make_executor(mock_db)
    result = executor.execute_function("F_NONEXISTENT", {"P_X": "1"})
    assert result.success
    assert len(result.rows) == 0

def test_execute_adds_row_limit_when_missing(mock_db):
    executor = make_executor(mock_db)
    result = executor.execute("SELECT order_no FROM tb_order WHERE order_no = 'A001'")
    assert result.success
    assert result.row_limit_applied
