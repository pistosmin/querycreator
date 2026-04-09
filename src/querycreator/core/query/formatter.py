"""Result formatter for LLM consumption."""
from __future__ import annotations
from typing import Any

class ResultFormatter:
    def __init__(self, code_mappings: dict[str, dict[str, str]] | None = None, max_display_rows: int = 100) -> None:
        self._code_mappings = code_mappings or {}
        self._max_display_rows = max_display_rows

    def format_for_llm(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "조회 결과 없음 (0건)"
        total = len(rows)
        display_rows = rows[:self._max_display_rows]
        truncated = total > self._max_display_rows
        translated = [self._translate_row(row) for row in display_rows]
        columns = list(translated[0].keys())
        lines = []
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        for row in translated:
            vals = [str(row.get(c, "")) for c in columns]
            lines.append("| " + " | ".join(vals) + " |")
        summary = f"\n총 {total}건"
        if truncated:
            summary += f" (상위 {self._max_display_rows}건만 표시)"
        return "\n".join(lines) + summary

    def _translate_row(self, row: dict[str, Any]) -> dict[str, Any]:
        translated = {}
        for col, val in row.items():
            col_upper = col.upper()
            if col_upper in self._code_mappings and str(val) in self._code_mappings[col_upper]:
                translated[col] = f"{self._code_mappings[col_upper][str(val)]}({val})"
            else:
                translated[col] = val
        return translated
