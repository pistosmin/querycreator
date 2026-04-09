"""Business dictionary: maps business terms to DB objects."""

from __future__ import annotations

import os
from typing import Any

import yaml


class BusinessDictionary:
    """Loads YAML dictionary files and searches by keyword."""

    def __init__(self, dict_dir: str) -> None:
        self._dict_dir = dict_dir
        self._tables: dict[str, dict[str, Any]] = {}
        self._functions: dict[str, dict[str, Any]] = {}
        self._joins: list[dict[str, Any]] = []

    def load(self) -> None:
        """Load all YAML files from the dictionary directory."""
        self._tables.clear()
        self._functions.clear()
        self._joins.clear()
        for fname in os.listdir(self._dict_dir):
            if not fname.endswith((".yaml", ".yml")) or fname.startswith("_"):
                continue
            path = os.path.join(self._dict_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            self._load_schema(data)

    def _load_schema(self, data: dict[str, Any]) -> None:
        for tbl_name, tbl_info in data.get("tables", {}).items():
            self._tables[tbl_name.upper()] = {
                "table_name": tbl_name.upper(),
                "schema": data.get("schema", ""),
                **tbl_info,
            }
        for func_name, func_info in data.get("functions", {}).items():
            self._functions[func_name.upper()] = {
                "function_name": func_name.upper(),
                "schema": data.get("schema", ""),
                **func_info,
            }
        for join_info in data.get("joins", []):
            self._joins.append(join_info)

    def search(self, keyword: str) -> dict[str, list[dict[str, Any]]]:
        """Search tables, functions, and joins by keyword.
        Matches against: table_name, business_name, aliases, description, column descriptions, function names.
        """
        keyword_upper = keyword.upper().strip()
        keywords = keyword_upper.split()

        matched_tables = []
        matched_functions = []
        matched_joins = []

        for tbl_name, info in self._tables.items():
            if self._matches(info, keywords, tbl_name):
                matched_tables.append(info)

        for func_name, info in self._functions.items():
            if self._matches_function(info, keywords, func_name):
                matched_functions.append(info)

        matched_table_names = {t["table_name"] for t in matched_tables}
        for join_info in self._joins:
            join_tables = {t.upper() for t in join_info.get("tables", [])}
            if join_tables & matched_table_names:
                matched_joins.append(join_info)

        return {"tables": matched_tables, "functions": matched_functions, "joins": matched_joins}

    def get_table_info(self, table_name: str) -> dict[str, Any] | None:
        return self._tables.get(table_name.upper())

    def get_function_info(self, func_name: str) -> dict[str, Any] | None:
        return self._functions.get(func_name.upper())

    def _matches(self, info: dict[str, Any], keywords: list[str], tbl_name: str) -> bool:
        searchable = " ".join([
            tbl_name,
            info.get("business_name", ""),
            info.get("description", ""),
            " ".join(info.get("aliases", [])),
            " ".join(str(v) for v in info.get("key_columns", {}).values()),
        ]).upper()
        return all(kw in searchable for kw in keywords)

    def _matches_function(self, info: dict[str, Any], keywords: list[str], func_name: str) -> bool:
        searchable = " ".join([
            func_name,
            info.get("business_name", ""),
            info.get("description", ""),
            info.get("usage", ""),
        ]).upper()
        return all(kw in searchable for kw in keywords)
