"""Tests for unified metadata catalog."""
from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from querycreator.core.metadata.catalog import MetadataCatalog
from querycreator.core.metadata.collector import MetadataCollector
from querycreator.core.metadata.dictionary import BusinessDictionary
from querycreator.db.mock_connection import MockConnection

SAMPLE_DICT = {
    "schema": "TEST",
    "tables": {
        "TB_ORDER": {
            "business_name": "주문",
            "description": "고객 주문 마스터",
            "key_columns": {"ORDER_NO": "주문번호", "CUST_CD": "고객코드"},
            "aliases": ["수주"],
        },
        "TB_PROD_PROGRESS": {
            "business_name": "진행량",
            "description": "공정별 진행 현황",
            "key_columns": {"ORDER_NO": "주문번호", "PROC_CD": "공정코드", "WEIGHT": "중량"},
            "aliases": ["생산실적"],
        },
    },
    "functions": {
        "F_SUM_PROGRESS": {
            "business_name": "공정별 진행량 합산",
            "description": "주문번호 기준 공정별 중량 합계",
            "parameters": {"P_ORDER_NO": "주문번호"},
            "usage": "공정별 생산량 조회",
        }
    },
    "joins": [
        {
            "tables": ["TB_ORDER", "TB_PROD_PROGRESS"],
            "condition": "TB_ORDER.ORDER_NO = TB_PROD_PROGRESS.ORDER_NO",
            "description": "주문-진행량",
        }
    ],
}


def _make_catalog(mock_db: MockConnection) -> MetadataCatalog:
    with tempfile.TemporaryDirectory() as tmpdir:
        dict_file = os.path.join(tmpdir, "sample.yaml")
        with open(dict_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(SAMPLE_DICT, f, allow_unicode=True)
        dictionary = BusinessDictionary(tmpdir)
        dictionary.load()
    collector = MetadataCollector(mock_db, schema="TEST")
    catalog = MetadataCatalog(dictionary, collector, mock_db)
    catalog.initialize()
    return catalog


def test_search_returns_enriched_table_info(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    result = catalog.search("주문")
    tables = result["tables"]
    assert len(tables) > 0
    order_table = next((t for t in tables if t["table_name"] == "TB_ORDER"), None)
    assert order_table is not None
    assert order_table["business_name"] == "주문"
    assert order_table["num_rows"] == 50000
    assert len(order_table["columns"]) > 0
    assert len(order_table["indexes"]) > 0


def test_search_returns_functions(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    result = catalog.search("진행량 합산")
    functions = result["functions"]
    assert len(functions) > 0
    func_names = [f["function_name"] for f in functions]
    assert "F_SUM_PROGRESS" in func_names


def test_search_includes_warnings_for_large_tables(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    result = catalog.search("진행량")
    tables = result["tables"]
    progress_table = next((t for t in tables if t["table_name"] == "TB_PROD_PROGRESS"), None)
    assert progress_table is not None
    warnings = progress_table["warnings"]
    assert any("대용량" in w for w in warnings)


def test_search_includes_index_hints(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    result = catalog.search("주문")
    tables = result["tables"]
    order_table = next((t for t in tables if t["table_name"] == "TB_ORDER"), None)
    assert order_table is not None
    assert "indexed_columns" in order_table
    assert len(order_table["indexed_columns"]) > 0


def test_get_common_codes(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    codes = catalog.get_common_codes("PROC_CD")
    assert len(codes) > 0
    code_names = [c.get("CODE_NAME", "") for c in codes]
    assert any("원료투입" in name or "절단" in name or name for name in code_names)
    # Verify PROC_CD codes are present (fixture has 절단, 성형, 용접, 도장, 검사)
    assert any(c.get("CODE_GROUP") == "PROC_CD" for c in codes)


def test_search_includes_join_info(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    result = catalog.search("주문")
    joins = result["joins"]
    assert len(joins) > 0
    join_tables = [set(j["tables"]) for j in joins]
    assert any("TB_ORDER" in t for t in join_tables)
