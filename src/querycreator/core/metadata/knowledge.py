"""Operator knowledge base — hints, sample queries, rules."""
from __future__ import annotations
import os
from typing import Any
import yaml

class KnowledgeBase:
    def __init__(self, knowledge_dir: str) -> None:
        self._dir = knowledge_dir
        self._table_hints: dict[str, dict[str, Any]] = {}
        self._join_rules: list[dict[str, Any]] = []
        self._forbidden_patterns: list[str] = []
    def load(self) -> None:
        self._table_hints.clear()
        self._join_rules.clear()
        self._forbidden_patterns.clear()
        if not os.path.isdir(self._dir): return
        for fname in os.listdir(self._dir):
            if not fname.endswith((".yaml", ".yml")) or fname.startswith("_"): continue
            with open(os.path.join(self._dir, fname), "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data: self._load_data(data)
    def _load_data(self, data: dict[str, Any]) -> None:
        for tbl, hints in data.get("table_hints", {}).items():
            self._table_hints[tbl.upper()] = hints
        self._join_rules.extend(data.get("join_rules", []))
        self._forbidden_patterns.extend(data.get("forbidden_patterns", []))
    def get_table_hints(self, table_name: str) -> dict[str, Any] | None:
        return self._table_hints.get(table_name.upper())
    def get_sample_queries(self, table_name: str) -> list[dict[str, Any]]:
        hints = self._table_hints.get(table_name.upper())
        return hints.get("sample_queries", []) if hints else []
    def get_join_rules(self, *table_names: str) -> list[dict[str, Any]]:
        names = {t.upper() for t in table_names}
        return [r for r in self._join_rules if {t.upper() for t in r.get("tables", [])} & names]
    def get_forbidden_patterns(self) -> list[str]:
        return list(self._forbidden_patterns)
