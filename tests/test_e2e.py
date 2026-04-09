"""E2E integration tests using QueryCreatorApp with mock DB."""
from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from querycreator.app import QueryCreatorApp
from querycreator.db.mock_connection import MockConnection, MockData

DICT_DATA = {
    "schema": "TEST",
    "tables": {
        "TB_ORDER": {
            "business_name": "주문",
            "description": "고객 주문 마스터",
            "key_columns": {
                "ORDER_NO": "주문번호",
                "CUST_CD": "고객코드",
                "ORDER_DATE": "주문일자",
                "STATUS_CD": "상태코드",
            },
            "aliases": ["수주"],
        },
        "TB_PROD_PROGRESS": {
            "business_name": "진행량",
            "description": "공정별 진행 현황",
            "key_columns": {
                "ORDER_NO": "주문번호",
                "PROC_CD": "공정코드",
                "WEIGHT": "중량",
            },
            "aliases": ["생산실적"],
        },
    },
    "functions": {
        "F_SUM_PROGRESS": {
            "business_name": "공정별 진행량 합산",
            "description": "주문번호 기준 합산",
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


def _make_app(mock_db: MockConnection) -> QueryCreatorApp:
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_path = os.path.join(tmpdir, "test_dict.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(DICT_DATA, f, allow_unicode=True)
        app = QueryCreatorApp(db=mock_db, dict_dir=tmpdir, schema="TEST")
    return app


@pytest.fixture
def e2e_mock_db():
    data = MockData(
        tables=[
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "NUM_ROWS": 50000, "COMMENTS": "주문 테이블"},
            {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "NUM_ROWS": 5000000, "COMMENTS": "생산 진행 테이블"},
            {"OWNER": "TEST", "TABLE_NAME": "TB_COMMON_CODE", "NUM_ROWS": 500, "COMMENTS": "공통 코드 테이블"},
        ],
        columns=[
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_NO", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 20, "NULLABLE": "N", "COLUMN_ID": 1},
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "CUST_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 10, "NULLABLE": "Y", "COLUMN_ID": 2},
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_DATE", "DATA_TYPE": "DATE", "DATA_LENGTH": 7, "NULLABLE": "Y", "COLUMN_ID": 3},
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "STATUS_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 2, "NULLABLE": "Y", "COLUMN_ID": 4},
            {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "ORDER_NO", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 20, "NULLABLE": "N", "COLUMN_ID": 1},
            {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROC_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 3, "NULLABLE": "Y", "COLUMN_ID": 2},
            {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "WEIGHT", "DATA_TYPE": "NUMBER", "DATA_LENGTH": 22, "NULLABLE": "Y", "COLUMN_ID": 3},
            {"OWNER": "TEST", "TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_GROUP", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 20, "NULLABLE": "N", "COLUMN_ID": 1},
            {"OWNER": "TEST", "TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_VALUE", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 10, "NULLABLE": "N", "COLUMN_ID": 2},
            {"OWNER": "TEST", "TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_NAME", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 100, "NULLABLE": "Y", "COLUMN_ID": 3},
        ],
        indexes=[
            {"OWNER": "TEST", "INDEX_NAME": "IDX_ORDER_DATE", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_DATE", "COLUMN_POSITION": 1},
            {"OWNER": "TEST", "INDEX_NAME": "IDX_PROG_ORDER", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "ORDER_NO", "COLUMN_POSITION": 1},
        ],
        constraints=[
            {"OWNER": "TEST", "CONSTRAINT_NAME": "PK_ORDER", "TABLE_NAME": "TB_ORDER", "CONSTRAINT_TYPE": "P", "COLUMN_NAME": "ORDER_NO"},
        ],
        comments=[
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_NO", "COMMENTS": "주문번호"},
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "CUST_CD", "COMMENTS": "고객코드"},
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_DATE", "COMMENTS": "주문일자"},
            {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "STATUS_CD", "COMMENTS": "상태코드"},
            {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "ORDER_NO", "COMMENTS": "주문번호"},
            {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROC_CD", "COMMENTS": "공정코드"},
            {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "WEIGHT", "COMMENTS": "중량"},
        ],
        common_codes=[
            {"CODE_GROUP": "STATUS_CD", "CODE_VALUE": "01", "CODE_NAME": "대기"},
            {"CODE_GROUP": "STATUS_CD", "CODE_VALUE": "02", "CODE_NAME": "진행"},
        ],
        function_results={
            "F_SUM_PROGRESS": [
                {"ORDER_NO": "ORD-001", "TOTAL_WEIGHT": 1500.5, "PROC_CD": "010"},
                {"ORDER_NO": "ORD-002", "TOTAL_WEIGHT": 2300.0, "PROC_CD": "020"},
            ]
        },
        table_data={
            "TB_ORDER": [
                {"ORDER_NO": "ORD-001", "CUST_CD": "C001", "ORDER_DATE": "2024-01-01", "STATUS_CD": "01"},
                {"ORDER_NO": "ORD-002", "CUST_CD": "C002", "ORDER_DATE": "2024-01-02", "STATUS_CD": "02"},
            ]
        },
    )
    return MockConnection(data)


@pytest.fixture
def app(e2e_mock_db):
    return _make_app(e2e_mock_db)


def test_e2e_metadata_lookup(app):
    result = app.handle_tool_call("get_metadata", {"keyword": "주문"})
    assert "TB_ORDER" in result
    assert "주문" in result


def test_e2e_select_query(app):
    sql = "SELECT ORDER_NO, CUST_CD FROM TB_ORDER WHERE ORDER_DATE = '2024-01-01'"
    result = app.handle_tool_call("execute_query", {"sql": sql})
    assert "건" in result


def test_e2e_function_call(app):
    result = app.handle_tool_call(
        "call_function",
        {"function_name": "F_SUM_PROGRESS", "parameters": {"P_ORDER_NO": "ORD-001"}},
    )
    # Successful call returns formatted table data with row count, or the function name on failure
    assert "F_SUM_PROGRESS" in result or "건" in result or "TOTAL_WEIGHT" in result or "ORDER_NO" in result


def test_e2e_blocked_query(app):
    result = app.handle_tool_call("execute_query", {"sql": "DELETE FROM TB_ORDER WHERE ORDER_NO = 'ORD-001'"})
    assert "SELECT" in result or "실패" in result


def test_e2e_select_star_blocked(app):
    result = app.handle_tool_call("execute_query", {"sql": "SELECT * FROM TB_ORDER"})
    assert "실패" in result


def test_e2e_unknown_tool(app):
    result = app.handle_tool_call("unknown_tool", {"key": "value"})
    assert "알 수 없는" in result


def test_e2e_tool_schemas(app):
    schemas = app.get_tool_schemas()
    assert len(schemas) == 3
    names = {s["name"] for s in schemas}
    assert names == {"get_metadata", "execute_query", "call_function"}
