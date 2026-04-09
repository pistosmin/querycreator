"""Query executor — validates then runs SQL on Oracle."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any
from querycreator.config.safety_rules import SafetyRules
from querycreator.core.query.validator import QueryValidator
from querycreator.db.connection import DBConnection, QueryExecutionError

@dataclass
class ExecutionResult:
    success: bool
    rows: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    execution_time_ms: float = 0.0
    row_count: int = 0
    row_limit_applied: bool = False

class QueryExecutor:
    def __init__(self, db: DBConnection, validator: QueryValidator, rules: SafetyRules) -> None:
        self._db = db
        self._validator = validator
        self._rules = rules

    def execute(self, sql: str) -> ExecutionResult:
        validation = self._validator.validate(sql)
        if not validation.is_valid:
            return ExecutionResult(success=False, error=validation.reason)
        row_limit_applied = validation.row_limit_missing
        start = time.monotonic()
        try:
            rows = self._db.execute(sql, timeout_seconds=self._rules.timeout_seconds, max_rows=self._rules.max_rows)
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(success=True, rows=rows, execution_time_ms=round(elapsed, 2), row_count=len(rows), row_limit_applied=row_limit_applied)
        except QueryExecutionError as e:
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(success=False, error=self._friendly_error(e), execution_time_ms=round(elapsed, 2))
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(success=False, error=f"쿼리 실행 중 오류가 발생했습니다: {e}", execution_time_ms=round(elapsed, 2))

    def execute_function(self, func_name: str, params: dict[str, Any]) -> ExecutionResult:
        start = time.monotonic()
        try:
            rows = self._db.call_function(func_name, params, timeout_seconds=self._rules.timeout_seconds, max_rows=self._rules.max_rows)
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(success=True, rows=rows, execution_time_ms=round(elapsed, 2), row_count=len(rows))
        except QueryExecutionError as e:
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(success=False, error=self._friendly_error(e), execution_time_ms=round(elapsed, 2))
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(success=False, error=f"펑션 호출 중 오류가 발생했습니다: {e}", execution_time_ms=round(elapsed, 2))

    def _friendly_error(self, e: QueryExecutionError) -> str:
        code = e.ora_code
        if code == 1013: return "쿼리 실행 시간이 초과되었습니다 (타임아웃). 조건을 더 구체적으로 지정해주세요."
        if code == 942: return "테이블 또는 뷰가 존재하지 않습니다. 테이블명을 확인해주세요."
        if code == 904: return "컬럼명이 올바르지 않습니다. 컬럼명을 확인해주세요."
        if code == 936: return "SQL 문법 오류입니다. 쿼리를 확인해주세요."
        return f"데이터베이스 오류: {e.message}"
