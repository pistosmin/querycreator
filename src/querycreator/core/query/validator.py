"""SQL query validator enforcing safety rules."""
from __future__ import annotations
import re
from dataclasses import dataclass
import sqlparse
from querycreator.config.safety_rules import SafetyRules

@dataclass
class ValidationResult:
    is_valid: bool
    reason: str = ""
    row_limit_missing: bool = False

class QueryValidator:
    def __init__(self, rules: SafetyRules, table_row_counts: dict[str, int] | None = None) -> None:
        self._rules = rules
        self._table_rows = {k.upper(): v for k, v in (table_row_counts or {}).items()}

    def validate(self, sql: str) -> ValidationResult:
        sql = sql.strip()
        if not sql:
            return ValidationResult(False, "빈 쿼리입니다.")

        parsed = sqlparse.parse(sql)
        statements = [s for s in parsed if s.ttype is not sqlparse.tokens.Whitespace and str(s).strip()]
        if len(statements) > 1:
            return ValidationResult(False, "복수 SQL문은 허용되지 않습니다. 하나의 SELECT문만 사용하세요.")

        sql_upper = sql.upper()

        if not self._is_select(sql_upper):
            return ValidationResult(False, "SELECT 문만 허용됩니다. INSERT/UPDATE/DELETE/DROP 등은 사용할 수 없습니다.")

        if self._rules.block_select_star and self._has_select_star(sql_upper):
            return ValidationResult(False, "SELECT * 는 허용되지 않습니다. 필요한 컬럼을 명시하세요.")

        if self._rules.block_leading_wildcard and self._has_leading_wildcard(sql_upper):
            return ValidationResult(False, "LIKE '%...' 패턴(앞쪽 와일드카드)은 성능 문제로 차단됩니다. 앞글자 일치(LIKE 'ABC%')만 사용하세요.")

        large_table_issue = self._check_large_tables(sql_upper)
        if large_table_issue:
            return ValidationResult(False, large_table_issue)

        for pattern in self._rules.forbidden_patterns:
            if pattern.upper() in sql_upper:
                return ValidationResult(False, f"금지된 패턴입니다: {pattern}")

        row_limit_missing = not self._has_row_limit(sql_upper)
        return ValidationResult(is_valid=True, row_limit_missing=row_limit_missing)

    def _is_select(self, sql_upper: str) -> bool:
        stripped = sql_upper.lstrip()
        if stripped.startswith("SELECT") or stripped.startswith("WITH"):
            for blocked in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "MERGE"):
                if re.match(rf"^{blocked}\b", stripped):
                    return False
            return True
        return False

    def _has_select_star(self, sql_upper: str) -> bool:
        if "TABLE(" in sql_upper:
            return False
        return bool(re.search(r"\bSELECT\s+\*\s", sql_upper))

    def _has_leading_wildcard(self, sql_upper: str) -> bool:
        return bool(re.search(r"LIKE\s+'%", sql_upper))

    def _has_row_limit(self, sql_upper: str) -> bool:
        return "ROWNUM" in sql_upper or "FETCH FIRST" in sql_upper or "FETCH NEXT" in sql_upper

    def _check_large_tables(self, sql_upper: str) -> str | None:
        if not self._table_rows:
            return None
        for tbl_name, row_count in self._table_rows.items():
            if row_count < self._rules.large_table_threshold:
                continue
            if tbl_name in sql_upper:
                if "WHERE" not in sql_upper:
                    return f"대용량 테이블 {tbl_name} ({row_count:,}건)에 WHERE 조건이 없습니다. 반드시 검색 조건을 추가하세요."
        return None
