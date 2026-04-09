"""Unified metadata catalog."""
from __future__ import annotations
from typing import Any
from querycreator.core.metadata.collector import MetadataCollector
from querycreator.core.metadata.dictionary import BusinessDictionary
from querycreator.db.connection import DBConnection

_LARGE_TABLE_THRESHOLD = 100_000


class MetadataCatalog:
    def __init__(self, dictionary: BusinessDictionary, collector: MetadataCollector, db: DBConnection, common_code_table: str = "TB_COMMON_CODE") -> None:
        self._dictionary = dictionary
        self._collector = collector
        self._db = db
        self._common_code_table = common_code_table
        self._physical_meta: dict[str, dict[str, Any]] = {}
        self._common_codes_cache: dict[str, list[dict[str, Any]]] = {}

    def initialize(self) -> None:
        self._physical_meta = self._collector.collect_all()

    def search(self, keyword: str) -> dict[str, Any]:
        dict_results = self._dictionary.search(keyword)
        enriched_tables = []
        for tbl_info in dict_results["tables"]:
            tbl_name = tbl_info["table_name"]
            physical = self._physical_meta.get(tbl_name, {})
            enriched = {
                **tbl_info, "num_rows": physical.get("num_rows", 0),
                "columns": physical.get("columns", []), "indexes": physical.get("indexes", []),
                "constraints": physical.get("constraints", []), "comments": physical.get("comments", {}),
                "indexed_columns": self._extract_indexed_columns(physical),
                "warnings": self._generate_warnings(tbl_name, physical),
            }
            enriched_tables.append(enriched)
        return {"tables": enriched_tables, "functions": dict_results["functions"], "joins": dict_results["joins"]}

    def get_common_codes(self, code_group: str) -> list[dict[str, Any]]:
        if code_group in self._common_codes_cache:
            return self._common_codes_cache[code_group]
        rows = self._db.execute(
            f"SELECT code_group, code_value, code_name FROM {self._common_code_table} WHERE code_group = :cg",
            {"cg": code_group}, max_rows=500)
        self._common_codes_cache[code_group] = rows
        return rows

    def _extract_indexed_columns(self, physical: dict[str, Any]) -> list[str]:
        return sorted({idx["column_name"] for idx in physical.get("indexes", [])})

    def _generate_warnings(self, tbl_name: str, physical: dict[str, Any]) -> list[str]:
        warnings = []
        num_rows = physical.get("num_rows", 0)
        if num_rows >= _LARGE_TABLE_THRESHOLD:
            warnings.append(f"대용량 테이블 ({num_rows:,}건) - 반드시 WHERE 조건과 인덱스 컬럼 사용 필요")
        constraints = physical.get("constraints", [])
        if not any(c.get("type") == "PK" for c in constraints) and num_rows > 0:
            warnings.append("PK가 없는 테이블 - 조인 시 주의 필요")
        if not self._extract_indexed_columns(physical) and num_rows >= _LARGE_TABLE_THRESHOLD:
            warnings.append("인덱스 없음 - 풀스캔 위험")
        return warnings
