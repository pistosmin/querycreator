"""Shared test fixtures."""

from __future__ import annotations

import pytest

from querycreator.db.mock_connection import MockConnection, MockData


@pytest.fixture
def sample_tables():
    return [
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "NUM_ROWS": 50000, "COMMENTS": "주문 테이블"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "NUM_ROWS": 5000000, "COMMENTS": "생산 진행 테이블"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PRODUCT", "NUM_ROWS": 1000, "COMMENTS": "제품 테이블"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_COMMON_CODE", "NUM_ROWS": 500, "COMMENTS": "공통 코드 테이블"},
    ]


@pytest.fixture
def sample_columns():
    return [
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_NO", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 20, "NULLABLE": "N", "COLUMN_ID": 1},
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "CUST_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 10, "NULLABLE": "Y", "COLUMN_ID": 2},
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_DATE", "DATA_TYPE": "DATE", "DATA_LENGTH": 7, "NULLABLE": "Y", "COLUMN_ID": 3},
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "STATUS_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 2, "NULLABLE": "Y", "COLUMN_ID": 4},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "ORDER_NO", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 20, "NULLABLE": "N", "COLUMN_ID": 1},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROC_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 3, "NULLABLE": "Y", "COLUMN_ID": 2},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "WEIGHT", "DATA_TYPE": "NUMBER", "DATA_LENGTH": 22, "NULLABLE": "Y", "COLUMN_ID": 3},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROD_DATE", "DATA_TYPE": "DATE", "DATA_LENGTH": 7, "NULLABLE": "Y", "COLUMN_ID": 4},
        {"OWNER": "TEST", "TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_GROUP", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 20, "NULLABLE": "N", "COLUMN_ID": 1},
        {"OWNER": "TEST", "TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_VALUE", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 10, "NULLABLE": "N", "COLUMN_ID": 2},
        {"OWNER": "TEST", "TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_NAME", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 100, "NULLABLE": "Y", "COLUMN_ID": 3},
    ]


@pytest.fixture
def sample_indexes():
    return [
        {"OWNER": "TEST", "INDEX_NAME": "IDX_ORDER_DATE", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_DATE", "COLUMN_POSITION": 1},
        {"OWNER": "TEST", "INDEX_NAME": "IDX_ORDER_CUST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "CUST_CD", "COLUMN_POSITION": 1},
        {"OWNER": "TEST", "INDEX_NAME": "IDX_PROG_ORDER", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "ORDER_NO", "COLUMN_POSITION": 1},
        {"OWNER": "TEST", "INDEX_NAME": "IDX_PROG_DATE", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROD_DATE", "COLUMN_POSITION": 1},
    ]


@pytest.fixture
def sample_constraints():
    return [
        {"OWNER": "TEST", "CONSTRAINT_NAME": "PK_ORDER", "TABLE_NAME": "TB_ORDER", "CONSTRAINT_TYPE": "P", "COLUMN_NAME": "ORDER_NO"},
    ]


@pytest.fixture
def sample_comments():
    return [
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_NO", "COMMENTS": "주문번호"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "CUST_CD", "COMMENTS": "고객코드"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_DATE", "COMMENTS": "주문일자"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "STATUS_CD", "COMMENTS": "상태코드"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "ORDER_NO", "COMMENTS": "주문번호"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROC_CD", "COMMENTS": "공정코드"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "WEIGHT", "COMMENTS": "중량"},
        {"OWNER": "TEST", "TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROD_DATE", "COMMENTS": "생산일자"},
    ]


@pytest.fixture
def sample_common_codes():
    return [
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "010", "CODE_NAME": "절단"},
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "020", "CODE_NAME": "성형"},
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "030", "CODE_NAME": "용접"},
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "040", "CODE_NAME": "도장"},
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "050", "CODE_NAME": "검사"},
        {"CODE_GROUP": "STATUS_CD", "CODE_VALUE": "01", "CODE_NAME": "대기"},
        {"CODE_GROUP": "STATUS_CD", "CODE_VALUE": "02", "CODE_NAME": "진행"},
        {"CODE_GROUP": "STATUS_CD", "CODE_VALUE": "03", "CODE_NAME": "완료"},
    ]


@pytest.fixture
def mock_data(sample_tables, sample_columns, sample_indexes, sample_constraints, sample_comments, sample_common_codes):
    return MockData(
        tables=sample_tables,
        columns=sample_columns,
        indexes=sample_indexes,
        constraints=sample_constraints,
        comments=sample_comments,
        common_codes=sample_common_codes,
        function_results={
            "F_SUM_PROGRESS": [
                {"ORDER_NO": "ORD-001", "TOTAL_WEIGHT": 1500.5, "PROC_CD": "010"},
                {"ORDER_NO": "ORD-002", "TOTAL_WEIGHT": 2300.0, "PROC_CD": "020"},
            ]
        },
        table_data={
            "LARGE_TABLE": [{"ID": i, "VALUE": f"val_{i}"} for i in range(100)],
        },
    )


@pytest.fixture
def mock_db(mock_data):
    return MockConnection(mock_data)
