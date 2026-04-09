"""Tests for LLM-callable tools."""
from __future__ import annotations

import os
import tempfile

import yaml

from querycreator.config.safety_rules import SafetyRules
from querycreator.core.metadata.catalog import MetadataCatalog
from querycreator.core.metadata.collector import MetadataCollector
from querycreator.core.metadata.dictionary import BusinessDictionary
from querycreator.core.query.executor import QueryExecutor
from querycreator.core.query.formatter import ResultFormatter
from querycreator.core.query.validator import QueryValidator
from querycreator.core.tools.call_function import CallFunctionTool
from querycreator.core.tools.execute_query import ExecuteQueryTool
from querycreator.core.tools.get_metadata import GetMetadataTool
from querycreator.db.mock_connection import MockConnection

SAMPLE_DICT = {
    "schema": "TEST",
    "tables": {
        "TB_ORDER": {
            "business_name": "주문",
            "description": "고객 주문 마스터",
            "key_columns": {"ORDER_NO": "주문번호"},
            "aliases": ["수주"],
        }
    },
    "functions": {
        "F_SUM_PROGRESS": {
            "business_name": "공정별 진행량 합산",
            "description": "주문번호 기준 합산",
            "parameters": {"P_ORDER_NO": "주문번호"},
            "usage": "공정별 생산량 조회",
        }
    },
    "joins": [],
}


def _build_tools(mock_db: MockConnection):
    with tempfile.TemporaryDirectory() as tmpdir:
        dict_file = os.path.join(tmpdir, "sample.yaml")
        with open(dict_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(SAMPLE_DICT, f, allow_unicode=True)
        dictionary = BusinessDictionary(tmpdir)
        dictionary.load()

    collector = MetadataCollector(mock_db, schema="TEST")
    catalog = MetadataCatalog(dictionary=dictionary, collector=collector, db=mock_db)
    catalog.initialize()

    table_rows = {tbl: info["num_rows"] for tbl, info in collector.collect_tables().items()}
    rules = SafetyRules()
    validator = QueryValidator(rules=rules, table_row_counts=table_rows)
    executor = QueryExecutor(db=mock_db, validator=validator, rules=rules)
    formatter = ResultFormatter()

    get_metadata = GetMetadataTool(catalog=catalog)
    execute_query = ExecuteQueryTool(executor=executor, formatter=formatter)
    call_function = CallFunctionTool(executor=executor, formatter=formatter, catalog=catalog)

    return get_metadata, execute_query, call_function


def test_get_metadata_tool(mock_db):
    get_metadata, _, _ = _build_tools(mock_db)
    result = get_metadata.run("주문")
    assert "TB_ORDER" in result
    assert "주문" in result


def test_get_metadata_tool_schema():
    schema = GetMetadataTool.tool_schema()
    assert schema["name"] == "get_metadata"


def test_execute_query_tool(mock_db):
    _, execute_query, _ = _build_tools(mock_db)
    result = execute_query.run("SELECT order_no, cust_cd FROM tb_order WHERE order_no = 'A001'")
    assert "건" in result


def test_execute_query_tool_blocked_query(mock_db):
    _, execute_query, _ = _build_tools(mock_db)
    result = execute_query.run("DELETE FROM tb_order")
    assert "SELECT" in result


def test_call_function_tool(mock_db):
    _, _, call_function = _build_tools(mock_db)
    result = call_function.run("F_SUM_PROGRESS", {"P_ORDER_NO": "ORD-001"})
    assert result  # has content


def test_call_function_tool_unknown(mock_db):
    _, _, call_function = _build_tools(mock_db)
    result = call_function.run("F_NONEXISTENT", {"P_X": "1"})
    assert "0건" in result or "없음" in result
