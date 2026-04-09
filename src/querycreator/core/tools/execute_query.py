"""ExecuteQueryTool — validates and executes SQL queries."""
from __future__ import annotations
from typing import Any
from querycreator.core.query.executor import QueryExecutor
from querycreator.core.query.formatter import ResultFormatter


class ExecuteQueryTool:
    def __init__(self, executor: QueryExecutor, formatter: ResultFormatter) -> None:
        self._executor = executor
        self._formatter = formatter

    def run(self, sql: str) -> str:
        result = self._executor.execute(sql)
        if not result.success:
            return (
                f"쿼리 실행 실패: {result.error}\n\n"
                "힌트: SELECT 문만 허용되며, WHERE 조건과 인덱스 컬럼을 사용하세요. "
                "쿼리를 수정한 후 다시 시도해주세요."
            )
        formatted = self._formatter.format_for_llm(result.rows)
        note = ""
        if result.row_limit_applied:
            note = "\n\n참고: 행 제한이 자동으로 적용되었습니다."
        return f"{formatted}{note}"

    @staticmethod
    def tool_schema() -> dict[str, Any]:
        return {
            "name": "execute_query",
            "description": (
                "SQL SELECT 쿼리를 실행하고 결과를 반환합니다. "
                "DML(INSERT/UPDATE/DELETE) 및 DDL은 허용되지 않습니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "실행할 SQL SELECT 쿼리문",
                    }
                },
                "required": ["sql"],
            },
        }
