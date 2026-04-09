"""CallFunctionTool — calls Oracle stored functions via catalog."""
from __future__ import annotations
from typing import Any
from querycreator.core.metadata.catalog import MetadataCatalog
from querycreator.core.query.executor import QueryExecutor
from querycreator.core.query.formatter import ResultFormatter


class CallFunctionTool:
    def __init__(self, executor: QueryExecutor, formatter: ResultFormatter, catalog: MetadataCatalog) -> None:
        self._executor = executor
        self._formatter = formatter
        self._catalog = catalog

    def run(self, function_name: str, parameters: dict[str, Any]) -> str:
        result = self._executor.execute_function(function_name, parameters)
        if not result.success:
            return f"함수 실행 실패: {result.error}"
        return self._formatter.format_for_llm(result.rows)

    @staticmethod
    def tool_schema() -> dict[str, Any]:
        return {
            "name": "call_function",
            "description": (
                "Oracle 저장 함수를 호출하고 결과를 반환합니다. "
                "함수명과 파라미터를 지정하여 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "호출할 함수명 (예: 'F_SUM_PROGRESS')",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "함수 파라미터 (키-값 쌍)",
                        "additionalProperties": True,
                    },
                },
                "required": ["function_name", "parameters"],
            },
        }
