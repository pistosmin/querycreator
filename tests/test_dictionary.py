"""Tests for business dictionary."""
import os
import tempfile

import yaml

from querycreator.core.metadata.dictionary import BusinessDictionary

SAMPLE_DICT = {
    "schema": "PROD",
    "tables": {
        "TB_ORDER": {
            "business_name": "주문",
            "description": "고객 주문 마스터 테이블",
            "key_columns": {
                "ORDER_NO": "주문번호",
                "CUST_CD": "고객코드",
                "ORDER_DATE": "주문일자",
                "STATUS_CD": "상태코드",
            },
            "aliases": ["수주", "오더"],
        },
        "TB_PROD_PROGRESS": {
            "business_name": "진행량",
            "description": "공정별 생산 진행 현황",
            "key_columns": {
                "ORDER_NO": "주문번호",
                "PROC_CD": "공정코드",
                "WEIGHT": "중량",
                "PROD_DATE": "생산일자",
            },
            "aliases": ["생산실적", "공정진행"],
        },
    },
    "functions": {
        "F_SUM_PROGRESS": {
            "business_name": "공정별 진행량 합산",
            "description": "주문번호를 넣으면 공정 단계별 중량 합계를 리턴",
            "parameters": {"P_ORDER_NO": "주문번호"},
            "usage": "주문의 공정별 생산량 조회 시 사용",
        },
    },
    "joins": [
        {
            "tables": ["TB_ORDER", "TB_PROD_PROGRESS"],
            "condition": "TB_ORDER.ORDER_NO = TB_PROD_PROGRESS.ORDER_NO",
            "description": "주문-진행량 연결",
        }
    ],
}


def _write_yaml(data, path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)


def test_load_dictionary_from_yaml():
    """Dictionary loads tables, functions, and joins from a YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(SAMPLE_DICT, os.path.join(tmpdir, "sample.yaml"))
        bd = BusinessDictionary(tmpdir)
        bd.load()

        assert bd.get_table_info("TB_ORDER") is not None
        assert bd.get_table_info("TB_PROD_PROGRESS") is not None
        assert bd.get_function_info("F_SUM_PROGRESS") is not None


def test_search_by_keyword_returns_tables():
    """Searching by a Korean business name returns the matching table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(SAMPLE_DICT, os.path.join(tmpdir, "sample.yaml"))
        bd = BusinessDictionary(tmpdir)
        bd.load()

        result = bd.search("주문")
        table_names = [t["table_name"] for t in result["tables"]]
        assert "TB_ORDER" in table_names


def test_search_by_alias():
    """Searching by an alias returns the correct table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(SAMPLE_DICT, os.path.join(tmpdir, "sample.yaml"))
        bd = BusinessDictionary(tmpdir)
        bd.load()

        result = bd.search("오더")
        table_names = [t["table_name"] for t in result["tables"]]
        assert "TB_ORDER" in table_names


def test_search_by_table_name_directly():
    """Searching by partial table name returns the matching table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(SAMPLE_DICT, os.path.join(tmpdir, "sample.yaml"))
        bd = BusinessDictionary(tmpdir)
        bd.load()

        result = bd.search("TB_ORDER")
        table_names = [t["table_name"] for t in result["tables"]]
        assert "TB_ORDER" in table_names


def test_search_returns_functions():
    """Searching by a function-related keyword returns matching functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(SAMPLE_DICT, os.path.join(tmpdir, "sample.yaml"))
        bd = BusinessDictionary(tmpdir)
        bd.load()

        result = bd.search("F_SUM_PROGRESS")
        func_names = [f["function_name"] for f in result["functions"]]
        assert "F_SUM_PROGRESS" in func_names


def test_search_returns_join_info():
    """When a matched table participates in a join, that join is included."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(SAMPLE_DICT, os.path.join(tmpdir, "sample.yaml"))
        bd = BusinessDictionary(tmpdir)
        bd.load()

        result = bd.search("주문")
        assert len(result["joins"]) > 0
        join_tables = result["joins"][0]["tables"]
        assert "TB_ORDER" in join_tables


def test_get_function_info():
    """get_function_info returns the correct function metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(SAMPLE_DICT, os.path.join(tmpdir, "sample.yaml"))
        bd = BusinessDictionary(tmpdir)
        bd.load()

        info = bd.get_function_info("F_SUM_PROGRESS")
        assert info is not None
        assert info["function_name"] == "F_SUM_PROGRESS"
        assert info["schema"] == "PROD"
        assert "business_name" in info


def test_search_no_match_returns_empty():
    """Searching for a term with no matches returns empty lists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_yaml(SAMPLE_DICT, os.path.join(tmpdir, "sample.yaml"))
        bd = BusinessDictionary(tmpdir)
        bd.load()

        result = bd.search("NONEXISTENT_TERM_XYZ")
        assert result["tables"] == []
        assert result["functions"] == []
        assert result["joins"] == []
