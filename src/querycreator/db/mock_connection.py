"""Mock DB connection for testing without Oracle."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from querycreator.db.connection import DBConnection


@dataclass
class MockData:
    """Sample data for mock DB."""
    tables: list[dict[str, Any]] = field(default_factory=list)
    columns: list[dict[str, Any]] = field(default_factory=list)
    indexes: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    common_codes: list[dict[str, Any]] = field(default_factory=list)
    function_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    table_data: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


class MockConnection(DBConnection):
    """In-memory mock that simulates Oracle dictionary views and data queries."""

    def __init__(self, data: MockData) -> None:
        self._data = data
        self._closed = False

    def execute(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_seconds: int = 30,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        sql_upper = sql.upper().strip()

        if "ALL_TABLES" in sql_upper:
            rows = self._filter_rows(self._data.tables, params)
        elif "ALL_TAB_COLUMNS" in sql_upper or "ALL_COL_COMMENTS" in sql_upper:
            if "COMMENT" in sql_upper:
                rows = self._filter_rows(self._data.comments, params)
            else:
                rows = self._filter_rows(self._data.columns, params)
        elif "ALL_IND_COLUMNS" in sql_upper:
            rows = self._filter_rows(self._data.indexes, params)
        elif "ALL_CONSTRAINTS" in sql_upper or "ALL_CONS_COLUMNS" in sql_upper:
            rows = self._filter_rows(self._data.constraints, params)
        elif "TB_COMMON_CODE" in sql_upper:
            rows = self._filter_common_codes(sql_upper, params)
        elif "TABLE(" in sql_upper:
            rows = self._handle_function_call(sql_upper, params)
        else:
            rows = self._handle_generic_query(sql_upper, params)

        return rows[:max_rows]

    def call_function(
        self,
        func_name: str,
        params: dict[str, Any],
        *,
        timeout_seconds: int = 30,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        func_upper = func_name.upper()
        if func_upper in self._data.function_results:
            return self._data.function_results[func_upper][:max_rows]
        return []

    def close(self) -> None:
        self._closed = True

    def _filter_rows(self, rows: list[dict[str, Any]], params: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not params:
            return rows
        result = rows
        for key, value in params.items():
            key_upper = key.upper()
            matched_col = None
            for col_name in (rows[0].keys() if rows else []):
                if col_name.upper() == key_upper or key_upper in col_name.upper():
                    matched_col = col_name
                    break
            if matched_col:
                result = [r for r in result if r.get(matched_col) == value]
        return result

    def _filter_common_codes(self, sql_upper: str, params: dict[str, Any] | None) -> list[dict[str, Any]]:
        rows = self._data.common_codes
        if params:
            for key, value in params.items():
                rows = [r for r in rows if any(str(v).upper() == str(value).upper() for v in r.values())]
        return rows

    def _handle_function_call(self, sql_upper: str, params: dict[str, Any] | None) -> list[dict[str, Any]]:
        match = re.search(r"TABLE\((\w+)\(", sql_upper)
        if match:
            func_name = match.group(1)
            if func_name in self._data.function_results:
                return self._data.function_results[func_name]
        return []

    def _handle_generic_query(self, sql_upper: str, params: dict[str, Any] | None) -> list[dict[str, Any]]:
        for table_name, rows in self._data.table_data.items():
            if table_name.upper() in sql_upper:
                return rows
        return [{"RESULT": "mock_value"}]
