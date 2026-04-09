# QueryCreator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python app for Agent that lets LLMs auto-generate and execute Oracle SQL queries based on business metadata, safely returning results to end users.

**Architecture:** Three LLM-callable tools (`get_metadata`, `execute_query`, `call_function`) backed by a 4-layer metadata system (business dictionary, physical metadata, common codes, operator knowledge). All queries pass through a validation layer enforcing safety rules before execution on a SELECT-only Oracle account. A DB abstraction layer with mock support enables development without a live Oracle instance.

**Tech Stack:** Python 3.11+, oracledb (thin mode), PyYAML, sqlparse, pytest, FastAPI (admin, later phase)

---

## File Structure

```
querycreator/
├── pyproject.toml
├── README.md
├── src/
│   └── querycreator/
│       ├── __init__.py
│       ├── app.py                          # Agent entry point
│       ├── config/
│       │   ├── __init__.py
│       │   ├── db_config.py                # Oracle connection settings (env-based)
│       │   ├── schema_config.py            # Target schema list
│       │   └── safety_rules.py             # Default safety rules
│       ├── db/
│       │   ├── __init__.py
│       │   ├── connection.py               # DB connection interface + Oracle impl
│       │   └── mock_connection.py          # Mock DB for testing
│       ├── core/
│       │   ├── __init__.py
│       │   ├── metadata/
│       │   │   ├── __init__.py
│       │   │   ├── collector.py            # Oracle dictionary auto-collection
│       │   │   ├── dictionary.py           # Business dictionary (YAML ↔ DB mapping)
│       │   │   ├── catalog.py              # Unified metadata catalog
│       │   │   └── knowledge.py            # Operator hints/rules
│       │   ├── query/
│       │   │   ├── __init__.py
│       │   │   ├── validator.py            # SQL safety validation
│       │   │   ├── executor.py             # Query execution with timeout
│       │   │   └── formatter.py            # Result formatting + code translation
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── get_metadata.py         # Metadata lookup tool
│       │       ├── execute_query.py        # SQL execution tool
│       │       └── call_function.py        # Stored function tool
│       ├── logging/
│       │   ├── __init__.py
│       │   ├── query_log.py               # Query execution history
│       │   └── analyzer.py                # Slow query analysis
│       └── admin/
│           ├── __init__.py
│           └── cli.py                      # Admin CLI tool
├── data/
│   └── dictionaries/
│       ├── _template.yaml                  # Dictionary YAML template
│       └── sample_production.yaml          # Sample: production schema
├── data/
│   └── knowledge/
│       └── sample_production.yaml          # Sample: operator hints
├── tests/
│   ├── __init__.py
│   ├── conftest.py                         # Shared fixtures (mock DB, sample data)
│   ├── test_db_connection.py
│   ├── test_collector.py
│   ├── test_dictionary.py
│   ├── test_catalog.py
│   ├── test_validator.py
│   ├── test_executor.py
│   ├── test_formatter.py
│   ├── test_tools.py
│   ├── test_query_log.py
│   ├── test_analyzer.py
│   ├── test_knowledge.py
│   ├── test_cli.py
│   └── test_e2e.py                         # End-to-end scenarios
├── docs/
│   ├── setup-guide.md
│   ├── admin-guide.md
│   ├── onboarding-guide.md
│   ├── api-reference.md
│   └── safety-rules.md
└── prompts/
    └── system_prompt.md                    # LLM system prompt for Agent
```

---

### Task 1: Project Scaffolding and Config

**Files:**
- Create: `pyproject.toml`
- Create: `src/querycreator/__init__.py`
- Create: `src/querycreator/config/__init__.py`
- Create: `src/querycreator/config/db_config.py`
- Create: `src/querycreator/config/schema_config.py`
- Create: `src/querycreator/config/safety_rules.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "querycreator"
version = "0.1.0"
description = "LLM-powered Oracle DB query generator for Agent"
requires-python = ">=3.11"
dependencies = [
    "oracledb>=2.0.0",
    "pyyaml>=6.0",
    "sqlparse>=0.5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]
admin = [
    "fastapi>=0.110.0",
    "uvicorn>=0.29.0",
    "jinja2>=3.1.0",
]
cli = [
    "click>=8.1.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create `src/querycreator/__init__.py`**

```python
"""QueryCreator: LLM-powered Oracle DB query generator."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create `src/querycreator/config/__init__.py`**

```python
"""Configuration modules."""
```

- [ ] **Step 4: Create `src/querycreator/config/db_config.py`**

```python
"""Oracle DB connection configuration via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DBConfig:
    """Oracle DB connection parameters."""

    host: str
    port: int
    service_name: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return f"{self.host}:{self.port}/{self.service_name}"

    @classmethod
    def from_env(cls) -> DBConfig:
        """Load config from environment variables.

        Required env vars:
            QC_DB_HOST, QC_DB_PORT, QC_DB_SERVICE,
            QC_DB_USER, QC_DB_PASSWORD
        """
        host = os.environ["QC_DB_HOST"]
        port = int(os.environ.get("QC_DB_PORT", "1521"))
        service = os.environ["QC_DB_SERVICE"]
        user = os.environ["QC_DB_USER"]
        password = os.environ["QC_DB_PASSWORD"]
        return cls(
            host=host, port=port, service_name=service,
            user=user, password=password,
        )
```

- [ ] **Step 5: Create `src/querycreator/config/schema_config.py`**

```python
"""Target schema configuration."""

from __future__ import annotations

import os


def get_target_schemas() -> list[str]:
    """Return list of Oracle schemas this instance manages.

    Reads from QC_SCHEMAS env var (comma-separated).
    Example: QC_SCHEMAS=PROD_ORDER,PROD_PLAN
    """
    raw = os.environ.get("QC_SCHEMAS", "")
    if not raw.strip():
        return []
    return [s.strip().upper() for s in raw.split(",") if s.strip()]
```

- [ ] **Step 6: Create `src/querycreator/config/safety_rules.py`**

```python
"""Default safety rules for query validation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SafetyRules:
    """Safety rules applied to every generated query."""

    # Only SELECT allowed
    allowed_statements: list[str] = field(default_factory=lambda: ["SELECT"])

    # Max rows returned
    max_rows: int = 1000

    # Query timeout in seconds
    timeout_seconds: int = 30

    # Block SELECT *
    block_select_star: bool = True

    # Block leading wildcard LIKE '%...'
    block_leading_wildcard: bool = True

    # Tables with num_rows above this threshold require WHERE clause
    large_table_threshold: int = 100_000

    # Max retry count when validation fails
    max_validation_retries: int = 2

    # Operator-defined forbidden patterns (populated from knowledge base)
    forbidden_patterns: list[str] = field(default_factory=list)
```

- [ ] **Step 7: Create `tests/__init__.py`**

```python
"""QueryCreator test suite."""
```

- [ ] **Step 8: Install project in dev mode and verify**

Run: `cd /Users/pistosmin/develop/querycreator && pip install -e ".[dev]" 2>&1 | tail -5`
Expected: "Successfully installed querycreator-0.1.0" (or similar)

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml src/ tests/__init__.py
git commit -m "feat: project scaffolding - pyproject.toml, config modules"
git push
```

---

### Task 2: DB Connection Abstraction and Mock

**Files:**
- Create: `src/querycreator/db/__init__.py`
- Create: `src/querycreator/db/connection.py`
- Create: `src/querycreator/db/mock_connection.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db_connection.py`

- [ ] **Step 1: Write the failing test `tests/test_db_connection.py`**

```python
"""Tests for DB connection abstraction."""

from querycreator.db.connection import DBConnection
from querycreator.db.mock_connection import MockConnection


def test_mock_connection_execute_returns_rows(mock_db: MockConnection):
    rows = mock_db.execute("SELECT table_name FROM all_tables WHERE owner = :owner", {"owner": "TEST"})
    assert isinstance(rows, list)
    assert len(rows) > 0


def test_mock_connection_execute_with_timeout(mock_db: MockConnection):
    rows = mock_db.execute(
        "SELECT 1 FROM dual",
        timeout_seconds=30,
    )
    assert rows is not None


def test_mock_connection_respects_max_rows(mock_db: MockConnection):
    rows = mock_db.execute("SELECT * FROM large_table", max_rows=5)
    assert len(rows) <= 5


def test_connection_is_abstract():
    """DBConnection cannot be instantiated directly."""
    try:
        DBConnection()
        assert False, "Should raise TypeError"
    except TypeError:
        pass
```

- [ ] **Step 2: Create shared fixtures `tests/conftest.py`**

```python
"""Shared test fixtures."""

import pytest
from querycreator.db.mock_connection import MockConnection, MockData


@pytest.fixture
def sample_tables() -> list[dict]:
    return [
        {"TABLE_NAME": "TB_ORDER", "NUM_ROWS": 50000, "OWNER": "TEST"},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "NUM_ROWS": 5000000, "OWNER": "TEST"},
        {"TABLE_NAME": "TB_PRODUCT", "NUM_ROWS": 1000, "OWNER": "TEST"},
        {"TABLE_NAME": "TB_COMMON_CODE", "NUM_ROWS": 500, "OWNER": "TEST"},
    ]


@pytest.fixture
def sample_columns() -> list[dict]:
    return [
        {"TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_NO", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 20, "NULLABLE": "N", "COLUMN_ID": 1},
        {"TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "CUST_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 10, "NULLABLE": "N", "COLUMN_ID": 2},
        {"TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_DATE", "DATA_TYPE": "DATE", "DATA_LENGTH": 7, "NULLABLE": "N", "COLUMN_ID": 3},
        {"TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "STATUS_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 3, "NULLABLE": "Y", "COLUMN_ID": 4},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "ORDER_NO", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 20, "NULLABLE": "N", "COLUMN_ID": 1},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROC_CD", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 5, "NULLABLE": "N", "COLUMN_ID": 2},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "WEIGHT", "DATA_TYPE": "NUMBER", "DATA_LENGTH": 22, "NULLABLE": "Y", "COLUMN_ID": 3},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROD_DATE", "DATA_TYPE": "DATE", "DATA_LENGTH": 7, "NULLABLE": "Y", "COLUMN_ID": 4},
        {"TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_GROUP", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 10, "NULLABLE": "N", "COLUMN_ID": 1},
        {"TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_VALUE", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 10, "NULLABLE": "N", "COLUMN_ID": 2},
        {"TABLE_NAME": "TB_COMMON_CODE", "COLUMN_NAME": "CODE_NAME", "DATA_TYPE": "VARCHAR2", "DATA_LENGTH": 100, "NULLABLE": "Y", "COLUMN_ID": 3},
    ]


@pytest.fixture
def sample_indexes() -> list[dict]:
    return [
        {"TABLE_NAME": "TB_ORDER", "INDEX_NAME": "IDX_ORDER_DATE", "COLUMN_NAME": "ORDER_DATE", "COLUMN_POSITION": 1},
        {"TABLE_NAME": "TB_ORDER", "INDEX_NAME": "IDX_ORDER_CUST", "COLUMN_NAME": "CUST_CD", "COLUMN_POSITION": 1},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "INDEX_NAME": "IDX_PROG_ORDER", "COLUMN_NAME": "ORDER_NO", "COLUMN_POSITION": 1},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "INDEX_NAME": "IDX_PROG_DATE", "COLUMN_NAME": "PROD_DATE", "COLUMN_POSITION": 1},
    ]


@pytest.fixture
def sample_constraints() -> list[dict]:
    return [
        {"TABLE_NAME": "TB_ORDER", "CONSTRAINT_NAME": "PK_ORDER", "CONSTRAINT_TYPE": "P", "COLUMN_NAME": "ORDER_NO"},
    ]


@pytest.fixture
def sample_comments() -> list[dict]:
    return [
        {"TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_NO", "COMMENTS": "주문번호"},
        {"TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "CUST_CD", "COMMENTS": "고객코드"},
        {"TABLE_NAME": "TB_ORDER", "COLUMN_NAME": "ORDER_DATE", "COMMENTS": "주문일자"},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "PROC_CD", "COMMENTS": "공정코드"},
        {"TABLE_NAME": "TB_PROD_PROGRESS", "COLUMN_NAME": "WEIGHT", "COMMENTS": "중량(톤)"},
    ]


@pytest.fixture
def sample_common_codes() -> list[dict]:
    return [
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "010", "CODE_NAME": "원료투입"},
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "020", "CODE_NAME": "가열"},
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "030", "CODE_NAME": "압연"},
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "040", "CODE_NAME": "냉각"},
        {"CODE_GROUP": "PROC_CD", "CODE_VALUE": "050", "CODE_NAME": "포장"},
        {"CODE_GROUP": "STATUS_CD", "CODE_VALUE": "01", "CODE_NAME": "접수"},
        {"CODE_GROUP": "STATUS_CD", "CODE_VALUE": "02", "CODE_NAME": "진행중"},
        {"CODE_GROUP": "STATUS_CD", "CODE_VALUE": "03", "CODE_NAME": "완료"},
    ]


@pytest.fixture
def mock_data(
    sample_tables, sample_columns, sample_indexes,
    sample_constraints, sample_comments, sample_common_codes,
) -> MockData:
    return MockData(
        tables=sample_tables,
        columns=sample_columns,
        indexes=sample_indexes,
        constraints=sample_constraints,
        comments=sample_comments,
        common_codes=sample_common_codes,
        function_results={
            "F_SUM_PROGRESS": [
                {"PROC_CD": "010", "PROC_NAME": "원료투입", "TOTAL_WEIGHT": 150.5},
                {"PROC_CD": "020", "PROC_NAME": "가열", "TOTAL_WEIGHT": 145.2},
                {"PROC_CD": "030", "PROC_NAME": "압연", "TOTAL_WEIGHT": 140.0},
            ],
        },
    )


@pytest.fixture
def mock_db(mock_data: MockData) -> MockConnection:
    return MockConnection(mock_data)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_db_connection.py -v 2>&1 | tail -10`
Expected: FAIL — modules not found

- [ ] **Step 4: Create `src/querycreator/db/__init__.py`**

```python
"""Database connection abstraction."""
```

- [ ] **Step 5: Create `src/querycreator/db/connection.py`**

```python
"""DB connection interface and Oracle implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DBConnection(ABC):
    """Abstract interface for database connections.

    All DB access goes through this interface so we can swap
    Oracle for a mock in tests.
    """

    @abstractmethod
    def execute(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_seconds: int = 30,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return rows as list of dicts."""
        ...

    @abstractmethod
    def call_function(
        self,
        func_name: str,
        params: dict[str, Any],
        *,
        timeout_seconds: int = 30,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        """Call a stored function and return its result set."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
        ...


class OracleConnection(DBConnection):
    """Oracle DB connection using oracledb thin mode."""

    def __init__(self, dsn: str, user: str, password: str) -> None:
        import oracledb

        oracledb.init_oracle_client()  # thin mode — no client needed
        self._conn = oracledb.connect(user=user, password=password, dsn=dsn)

    def execute(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_seconds: int = 30,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        import oracledb

        cursor = self._conn.cursor()
        try:
            cursor.calltimeout = timeout_seconds * 1000  # milliseconds
            cursor.execute(sql, params or {})
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchmany(max_rows)
            return [dict(zip(columns, row)) for row in rows]
        except oracledb.DatabaseError as e:
            error_obj = e.args[0]
            raise QueryExecutionError(
                ora_code=getattr(error_obj, "code", None),
                message=str(error_obj),
            ) from e
        finally:
            cursor.close()

    def call_function(
        self,
        func_name: str,
        params: dict[str, Any],
        *,
        timeout_seconds: int = 30,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        param_list = ", ".join(f":{k}" for k in params)
        sql = f"SELECT * FROM TABLE({func_name}({param_list}))"
        return self.execute(sql, params, timeout_seconds=timeout_seconds, max_rows=max_rows)

    def close(self) -> None:
        self._conn.close()


class QueryExecutionError(Exception):
    """Raised when a query fails on Oracle."""

    def __init__(self, ora_code: int | None, message: str) -> None:
        self.ora_code = ora_code
        self.message = message
        super().__init__(f"ORA-{ora_code}: {message}" if ora_code else message)
```

- [ ] **Step 6: Create `src/querycreator/db/mock_connection.py`**

```python
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
    # Generic table data for ad-hoc queries
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

        # Route to appropriate mock data based on SQL pattern
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

    def _filter_rows(
        self, rows: list[dict[str, Any]], params: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
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

    def _filter_common_codes(
        self, sql_upper: str, params: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        rows = self._data.common_codes
        if params:
            for key, value in params.items():
                rows = [
                    r for r in rows
                    if any(str(v).upper() == str(value).upper() for v in r.values())
                ]
        return rows

    def _handle_function_call(
        self, sql_upper: str, params: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        match = re.search(r"TABLE\((\w+)\(", sql_upper)
        if match:
            func_name = match.group(1)
            if func_name in self._data.function_results:
                return self._data.function_results[func_name]
        return []

    def _handle_generic_query(
        self, sql_upper: str, params: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        for table_name, rows in self._data.table_data.items():
            if table_name.upper() in sql_upper:
                return rows
        return [{"RESULT": "mock_value"}]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_db_connection.py -v`
Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add src/querycreator/db/ tests/conftest.py tests/test_db_connection.py
git commit -m "feat: DB connection abstraction with Oracle and Mock implementations"
git push
```

---

### Task 3: Business Dictionary

**Files:**
- Create: `src/querycreator/core/__init__.py`
- Create: `src/querycreator/core/metadata/__init__.py`
- Create: `src/querycreator/core/metadata/dictionary.py`
- Create: `data/dictionaries/_template.yaml`
- Create: `data/dictionaries/sample_production.yaml`
- Create: `tests/test_dictionary.py`

- [ ] **Step 1: Write the failing test `tests/test_dictionary.py`**

```python
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
            "parameters": {
                "P_ORDER_NO": "주문번호",
            },
            "usage": "주문의 공정별 생산량 조회 시 사용",
        },
    },
    "joins": [
        {
            "tables": ["TB_ORDER", "TB_PROD_PROGRESS"],
            "condition": "TB_ORDER.ORDER_NO = TB_PROD_PROGRESS.ORDER_NO",
            "description": "주문-진행량 연결",
        },
    ],
}


def _write_yaml(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)


def test_load_dictionary_from_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prod.yaml")
        _write_yaml(SAMPLE_DICT, path)
        bd = BusinessDictionary(tmpdir)
        bd.load()
        assert bd.get_table_info("TB_ORDER") is not None


def test_search_by_keyword_returns_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prod.yaml")
        _write_yaml(SAMPLE_DICT, path)
        bd = BusinessDictionary(tmpdir)
        bd.load()
        results = bd.search("주문")
        table_names = [r["table_name"] for r in results.get("tables", [])]
        assert "TB_ORDER" in table_names


def test_search_by_alias():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prod.yaml")
        _write_yaml(SAMPLE_DICT, path)
        bd = BusinessDictionary(tmpdir)
        bd.load()
        results = bd.search("수주")
        table_names = [r["table_name"] for r in results.get("tables", [])]
        assert "TB_ORDER" in table_names


def test_search_by_table_name_directly():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prod.yaml")
        _write_yaml(SAMPLE_DICT, path)
        bd = BusinessDictionary(tmpdir)
        bd.load()
        results = bd.search("TB_PROD_PROGRESS")
        table_names = [r["table_name"] for r in results.get("tables", [])]
        assert "TB_PROD_PROGRESS" in table_names


def test_search_returns_functions():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prod.yaml")
        _write_yaml(SAMPLE_DICT, path)
        bd = BusinessDictionary(tmpdir)
        bd.load()
        results = bd.search("진행량 합산")
        assert len(results.get("functions", [])) > 0


def test_search_returns_join_info():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prod.yaml")
        _write_yaml(SAMPLE_DICT, path)
        bd = BusinessDictionary(tmpdir)
        bd.load()
        results = bd.search("주문")
        assert len(results.get("joins", [])) > 0


def test_get_function_info():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prod.yaml")
        _write_yaml(SAMPLE_DICT, path)
        bd = BusinessDictionary(tmpdir)
        bd.load()
        func = bd.get_function_info("F_SUM_PROGRESS")
        assert func is not None
        assert func["business_name"] == "공정별 진행량 합산"


def test_search_no_match_returns_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "prod.yaml")
        _write_yaml(SAMPLE_DICT, path)
        bd = BusinessDictionary(tmpdir)
        bd.load()
        results = bd.search("존재하지않는키워드xyz")
        assert len(results.get("tables", [])) == 0
        assert len(results.get("functions", [])) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_dictionary.py -v 2>&1 | tail -5`
Expected: FAIL — module not found

- [ ] **Step 3: Create package init files**

`src/querycreator/core/__init__.py`:
```python
"""Core business logic."""
```

`src/querycreator/core/metadata/__init__.py`:
```python
"""Metadata management modules."""
```

- [ ] **Step 4: Implement `src/querycreator/core/metadata/dictionary.py`**

```python
"""Business dictionary: maps business terms to DB objects."""

from __future__ import annotations

import os
from typing import Any

import yaml


class BusinessDictionary:
    """Loads YAML dictionary files and searches by keyword.

    Each YAML file describes one schema's tables, functions, and join rules.
    """

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

        Matches against: table_name, business_name, aliases,
        description, column descriptions, function names.
        Also matches direct table/function name references.
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

        # Find joins involving matched tables
        matched_table_names = {t["table_name"] for t in matched_tables}
        for join_info in self._joins:
            join_tables = {t.upper() for t in join_info.get("tables", [])}
            if join_tables & matched_table_names:
                matched_joins.append(join_info)

        return {
            "tables": matched_tables,
            "functions": matched_functions,
            "joins": matched_joins,
        }

    def get_table_info(self, table_name: str) -> dict[str, Any] | None:
        return self._tables.get(table_name.upper())

    def get_function_info(self, func_name: str) -> dict[str, Any] | None:
        return self._functions.get(func_name.upper())

    def _matches(
        self, info: dict[str, Any], keywords: list[str], tbl_name: str,
    ) -> bool:
        searchable = " ".join([
            tbl_name,
            info.get("business_name", ""),
            info.get("description", ""),
            " ".join(info.get("aliases", [])),
            " ".join(str(v) for v in info.get("key_columns", {}).values()),
        ]).upper()

        return all(kw in searchable for kw in keywords)

    def _matches_function(
        self, info: dict[str, Any], keywords: list[str], func_name: str,
    ) -> bool:
        searchable = " ".join([
            func_name,
            info.get("business_name", ""),
            info.get("description", ""),
            info.get("usage", ""),
        ]).upper()

        return all(kw in searchable for kw in keywords)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_dictionary.py -v`
Expected: 8 passed

- [ ] **Step 6: Create `data/dictionaries/_template.yaml`**

```yaml
# QueryCreator 업무 사전 템플릿
# 이 파일을 복사하여 스키마별 업무 사전을 작성하세요.
# 파일명 예: production.yaml, quality.yaml

schema: SCHEMA_NAME  # Oracle 스키마명 (대문자)

tables:
  # TB_TABLE_NAME:
  #   business_name: 업무명 (예: 주문, 생산, 출하)
  #   description: 테이블 설명
  #   key_columns:
  #     COLUMN_NAME: 컬럼 업무명
  #   aliases:       # 사용자가 쓸 수 있는 다른 이름들
  #     - 별칭1
  #     - 별칭2

  EXAMPLE_TABLE:
    business_name: 예시
    description: "예시 테이블 설명"
    key_columns:
      COL1: 컬럼1 설명
      COL2: 컬럼2 설명
    aliases:
      - 예시별칭

functions:
  # F_FUNCTION_NAME:
  #   business_name: 펑션 업무명
  #   description: 펑션 설명
  #   parameters:
  #     P_PARAM1: 파라미터 설명
  #   usage: 이 펑션을 사용하는 상황 설명

joins:
  # - tables: [TB_A, TB_B]
  #   condition: "TB_A.KEY = TB_B.KEY"
  #   description: 조인 설명
```

- [ ] **Step 7: Create `data/dictionaries/sample_production.yaml`**

```yaml
schema: PROD

tables:
  TB_ORDER:
    business_name: 주문
    description: "고객 주문 마스터 테이블. 수주 정보, 납기, 고객 정보 포함."
    key_columns:
      ORDER_NO: 주문번호
      CUST_CD: 고객코드
      ORDER_DATE: 주문일자
      STATUS_CD: 상태코드
      DUE_DATE: 납기일
    aliases:
      - 수주
      - 오더

  TB_PROD_PROGRESS:
    business_name: 진행량
    description: "공정별 생산 진행 현황. 각 공정 단계에서의 제품 중량 기록."
    key_columns:
      ORDER_NO: 주문번호
      PROC_CD: 공정코드
      WEIGHT: 중량(톤)
      PROD_DATE: 생산일자
      PRODUCT_CD: 제품코드
    aliases:
      - 생산실적
      - 공정진행
      - 생산현황

  TB_PRODUCT:
    business_name: 제품
    description: "제품 마스터 테이블."
    key_columns:
      PRODUCT_CD: 제품코드
      PRODUCT_NAME: 제품명
      SPEC: 규격
    aliases:
      - 품목

functions:
  F_SUM_PROGRESS:
    business_name: 공정별 진행량 합산
    description: "주문번호를 넣으면 공정 단계별 중량 합계를 테이블로 리턴"
    parameters:
      P_ORDER_NO: 주문번호
    usage: "주문의 공정별 생산량을 조회할 때 사용. 직접 GROUP BY보다 이 펑션을 우선 사용."

joins:
  - tables: [TB_ORDER, TB_PROD_PROGRESS]
    condition: "TB_ORDER.ORDER_NO = TB_PROD_PROGRESS.ORDER_NO"
    description: "주문-진행량 조인 (주문번호 기준)"

  - tables: [TB_PROD_PROGRESS, TB_PRODUCT]
    condition: "TB_PROD_PROGRESS.PRODUCT_CD = TB_PRODUCT.PRODUCT_CD"
    description: "진행량-제품 조인 (제품코드 기준)"
```

- [ ] **Step 8: Commit**

```bash
git add src/querycreator/core/ data/dictionaries/ tests/test_dictionary.py
git commit -m "feat: business dictionary - keyword search, YAML loading, aliases"
git push
```

---

### Task 4: Metadata Collector

**Files:**
- Create: `src/querycreator/core/metadata/collector.py`
- Create: `tests/test_collector.py`

- [ ] **Step 1: Write the failing test `tests/test_collector.py`**

```python
"""Tests for Oracle dictionary metadata collector."""

from querycreator.core.metadata.collector import MetadataCollector
from querycreator.db.mock_connection import MockConnection


def test_collect_tables(mock_db: MockConnection):
    collector = MetadataCollector(mock_db, schema="TEST")
    tables = collector.collect_tables()
    assert len(tables) > 0
    assert "TB_ORDER" in tables
    assert tables["TB_ORDER"]["num_rows"] == 50000


def test_collect_columns(mock_db: MockConnection):
    collector = MetadataCollector(mock_db, schema="TEST")
    columns = collector.collect_columns()
    assert "TB_ORDER" in columns
    order_cols = columns["TB_ORDER"]
    col_names = [c["column_name"] for c in order_cols]
    assert "ORDER_NO" in col_names


def test_collect_indexes(mock_db: MockConnection):
    collector = MetadataCollector(mock_db, schema="TEST")
    indexes = collector.collect_indexes()
    assert "TB_ORDER" in indexes
    idx_names = [i["index_name"] for i in indexes["TB_ORDER"]]
    assert "IDX_ORDER_DATE" in idx_names


def test_collect_constraints(mock_db: MockConnection):
    collector = MetadataCollector(mock_db, schema="TEST")
    constraints = collector.collect_constraints()
    assert "TB_ORDER" in constraints


def test_collect_comments(mock_db: MockConnection):
    collector = MetadataCollector(mock_db, schema="TEST")
    comments = collector.collect_comments()
    assert "TB_ORDER" in comments
    assert comments["TB_ORDER"].get("ORDER_NO") == "주문번호"


def test_collect_all_returns_unified(mock_db: MockConnection):
    collector = MetadataCollector(mock_db, schema="TEST")
    meta = collector.collect_all()
    assert "TB_ORDER" in meta
    order = meta["TB_ORDER"]
    assert "num_rows" in order
    assert "columns" in order
    assert "indexes" in order
    assert "comments" in order
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_collector.py -v 2>&1 | tail -5`
Expected: FAIL — module not found

- [ ] **Step 3: Implement `src/querycreator/core/metadata/collector.py`**

```python
"""Oracle dictionary metadata collector.

Collects table, column, index, constraint, and comment information
from Oracle dictionary views (ALL_TABLES, ALL_TAB_COLUMNS, etc.).
"""

from __future__ import annotations

from typing import Any

from querycreator.db.connection import DBConnection


class MetadataCollector:
    """Collects physical metadata from Oracle dictionary views."""

    def __init__(self, db: DBConnection, schema: str) -> None:
        self._db = db
        self._schema = schema.upper()

    def collect_tables(self) -> dict[str, dict[str, Any]]:
        """Collect table names and row count estimates."""
        rows = self._db.execute(
            "SELECT table_name, num_rows FROM all_tables WHERE owner = :owner",
            {"owner": self._schema},
            max_rows=5000,
        )
        return {
            row["TABLE_NAME"]: {"num_rows": row.get("NUM_ROWS", 0) or 0}
            for row in rows
        }

    def collect_columns(self) -> dict[str, list[dict[str, Any]]]:
        """Collect column info grouped by table."""
        rows = self._db.execute(
            "SELECT table_name, column_name, data_type, data_length, nullable, column_id "
            "FROM all_tab_columns WHERE owner = :owner ORDER BY table_name, column_id",
            {"owner": self._schema},
            max_rows=50000,
        )
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            tbl = row["TABLE_NAME"]
            if tbl not in result:
                result[tbl] = []
            result[tbl].append({
                "column_name": row["COLUMN_NAME"],
                "data_type": row["DATA_TYPE"],
                "data_length": row.get("DATA_LENGTH"),
                "nullable": row.get("NULLABLE", "Y") == "Y",
                "position": row.get("COLUMN_ID"),
            })
        return result

    def collect_indexes(self) -> dict[str, list[dict[str, Any]]]:
        """Collect index info grouped by table."""
        rows = self._db.execute(
            "SELECT table_name, index_name, column_name, column_position "
            "FROM all_ind_columns WHERE table_owner = :owner "
            "ORDER BY table_name, index_name, column_position",
            {"owner": self._schema},
            max_rows=50000,
        )
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            tbl = row["TABLE_NAME"]
            if tbl not in result:
                result[tbl] = []
            result[tbl].append({
                "index_name": row["INDEX_NAME"],
                "column_name": row["COLUMN_NAME"],
                "position": row.get("COLUMN_POSITION"),
            })
        return result

    def collect_constraints(self) -> dict[str, list[dict[str, Any]]]:
        """Collect PK/FK constraints grouped by table."""
        rows = self._db.execute(
            "SELECT table_name, constraint_name, constraint_type, column_name "
            "FROM all_constraints NATURAL JOIN all_cons_columns "
            "WHERE owner = :owner AND constraint_type IN ('P', 'R')",
            {"owner": self._schema},
            max_rows=50000,
        )
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            tbl = row["TABLE_NAME"]
            if tbl not in result:
                result[tbl] = []
            result[tbl].append({
                "constraint_name": row["CONSTRAINT_NAME"],
                "type": "PK" if row["CONSTRAINT_TYPE"] == "P" else "FK",
                "column_name": row.get("COLUMN_NAME"),
            })
        return result

    def collect_comments(self) -> dict[str, dict[str, str]]:
        """Collect column comments grouped by table."""
        rows = self._db.execute(
            "SELECT table_name, column_name, comments "
            "FROM all_col_comments WHERE owner = :owner AND comments IS NOT NULL",
            {"owner": self._schema},
            max_rows=50000,
        )
        result: dict[str, dict[str, str]] = {}
        for row in rows:
            tbl = row["TABLE_NAME"]
            if tbl not in result:
                result[tbl] = {}
            result[tbl][row["COLUMN_NAME"]] = row["COMMENTS"]
        return result

    def collect_all(self) -> dict[str, dict[str, Any]]:
        """Collect all metadata and merge into a unified structure.

        Returns dict keyed by table_name, each containing:
            num_rows, columns, indexes, constraints, comments
        """
        tables = self.collect_tables()
        columns = self.collect_columns()
        indexes = self.collect_indexes()
        constraints = self.collect_constraints()
        comments = self.collect_comments()

        result: dict[str, dict[str, Any]] = {}
        for tbl_name, tbl_info in tables.items():
            result[tbl_name] = {
                "num_rows": tbl_info["num_rows"],
                "columns": columns.get(tbl_name, []),
                "indexes": indexes.get(tbl_name, []),
                "constraints": constraints.get(tbl_name, []),
                "comments": comments.get(tbl_name, {}),
            }
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_collector.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/querycreator/core/metadata/collector.py tests/test_collector.py
git commit -m "feat: Oracle dictionary metadata collector"
git push
```

---

### Task 5: Metadata Catalog (Unified Layer)

**Files:**
- Create: `src/querycreator/core/metadata/catalog.py`
- Create: `tests/test_catalog.py`

- [ ] **Step 1: Write the failing test `tests/test_catalog.py`**

```python
"""Tests for unified metadata catalog."""

import os
import tempfile

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
        },
    },
    "joins": [
        {
            "tables": ["TB_ORDER", "TB_PROD_PROGRESS"],
            "condition": "TB_ORDER.ORDER_NO = TB_PROD_PROGRESS.ORDER_NO",
            "description": "주문-진행량",
        },
    ],
}


def _make_catalog(mock_db: MockConnection) -> MetadataCatalog:
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "test.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(SAMPLE_DICT, f, allow_unicode=True)

    dictionary = BusinessDictionary(tmpdir)
    dictionary.load()
    collector = MetadataCollector(mock_db, schema="TEST")
    return MetadataCatalog(
        dictionary=dictionary,
        collector=collector,
        db=mock_db,
        common_code_table="TB_COMMON_CODE",
    )


def test_search_returns_enriched_table_info(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    catalog.initialize()
    result = catalog.search("주문")
    assert len(result["tables"]) > 0
    order = result["tables"][0]
    # Business info from dictionary
    assert order["business_name"] == "주문"
    # Physical info from collector
    assert "num_rows" in order
    assert "columns" in order
    assert "indexes" in order


def test_search_returns_functions(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    catalog.initialize()
    result = catalog.search("진행량 합산")
    assert len(result["functions"]) > 0


def test_search_includes_warnings_for_large_tables(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    catalog.initialize()
    result = catalog.search("진행량")
    progress_tables = [t for t in result["tables"] if t["table_name"] == "TB_PROD_PROGRESS"]
    assert len(progress_tables) > 0
    assert "warnings" in progress_tables[0]
    assert any("대용량" in w for w in progress_tables[0]["warnings"])


def test_search_includes_index_hints(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    catalog.initialize()
    result = catalog.search("주문")
    order = [t for t in result["tables"] if t["table_name"] == "TB_ORDER"][0]
    assert "indexed_columns" in order
    assert len(order["indexed_columns"]) > 0


def test_get_common_codes(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    catalog.initialize()
    codes = catalog.get_common_codes("PROC_CD")
    assert len(codes) > 0
    assert any(c["CODE_NAME"] == "원료투입" for c in codes)


def test_search_includes_join_info(mock_db: MockConnection):
    catalog = _make_catalog(mock_db)
    catalog.initialize()
    result = catalog.search("주문")
    assert len(result["joins"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_catalog.py -v 2>&1 | tail -5`
Expected: FAIL

- [ ] **Step 3: Implement `src/querycreator/core/metadata/catalog.py`**

```python
"""Unified metadata catalog.

Merges business dictionary, physical metadata, common codes,
and operator knowledge into a single search interface.
"""

from __future__ import annotations

from typing import Any

from querycreator.core.metadata.collector import MetadataCollector
from querycreator.core.metadata.dictionary import BusinessDictionary
from querycreator.db.connection import DBConnection

# Tables with more rows than this get a warning
_LARGE_TABLE_THRESHOLD = 100_000


class MetadataCatalog:
    """Unified metadata search combining all 4 layers."""

    def __init__(
        self,
        dictionary: BusinessDictionary,
        collector: MetadataCollector,
        db: DBConnection,
        common_code_table: str = "TB_COMMON_CODE",
    ) -> None:
        self._dictionary = dictionary
        self._collector = collector
        self._db = db
        self._common_code_table = common_code_table
        self._physical_meta: dict[str, dict[str, Any]] = {}
        self._common_codes_cache: dict[str, list[dict[str, Any]]] = {}

    def initialize(self) -> None:
        """Load physical metadata from DB. Call once at startup."""
        self._physical_meta = self._collector.collect_all()

    def search(self, keyword: str) -> dict[str, Any]:
        """Search across all metadata layers.

        Returns enriched results combining business + physical info.
        """
        dict_results = self._dictionary.search(keyword)

        enriched_tables = []
        for tbl_info in dict_results["tables"]:
            tbl_name = tbl_info["table_name"]
            physical = self._physical_meta.get(tbl_name, {})
            enriched = {
                **tbl_info,
                "num_rows": physical.get("num_rows", 0),
                "columns": physical.get("columns", []),
                "indexes": physical.get("indexes", []),
                "constraints": physical.get("constraints", []),
                "comments": physical.get("comments", {}),
                "indexed_columns": self._extract_indexed_columns(physical),
                "warnings": self._generate_warnings(tbl_name, physical),
            }
            enriched_tables.append(enriched)

        return {
            "tables": enriched_tables,
            "functions": dict_results["functions"],
            "joins": dict_results["joins"],
        }

    def get_common_codes(self, code_group: str) -> list[dict[str, Any]]:
        """Fetch common code values for a given code group."""
        if code_group in self._common_codes_cache:
            return self._common_codes_cache[code_group]

        rows = self._db.execute(
            f"SELECT code_group, code_value, code_name "
            f"FROM {self._common_code_table} "
            f"WHERE code_group = :cg",
            {"cg": code_group},
            max_rows=500,
        )
        self._common_codes_cache[code_group] = rows
        return rows

    def _extract_indexed_columns(self, physical: dict[str, Any]) -> list[str]:
        indexes = physical.get("indexes", [])
        return sorted({idx["column_name"] for idx in indexes})

    def _generate_warnings(
        self, tbl_name: str, physical: dict[str, Any],
    ) -> list[str]:
        warnings = []
        num_rows = physical.get("num_rows", 0)
        if num_rows >= _LARGE_TABLE_THRESHOLD:
            warnings.append(
                f"대용량 테이블 ({num_rows:,}건) - 반드시 WHERE 조건과 인덱스 컬럼 사용 필요"
            )

        # No PK warning
        constraints = physical.get("constraints", [])
        has_pk = any(c.get("type") == "PK" for c in constraints)
        if not has_pk and num_rows > 0:
            warnings.append("PK가 없는 테이블 - 조인 시 주의 필요")

        indexed_cols = self._extract_indexed_columns(physical)
        if not indexed_cols and num_rows >= _LARGE_TABLE_THRESHOLD:
            warnings.append("인덱스 없음 - 풀스캔 위험")

        return warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_catalog.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/querycreator/core/metadata/catalog.py tests/test_catalog.py
git commit -m "feat: unified metadata catalog - 4-layer integration"
git push
```

---

### Task 6: Query Validator

**Files:**
- Create: `src/querycreator/core/query/__init__.py`
- Create: `src/querycreator/core/query/validator.py`
- Create: `tests/test_validator.py`

- [ ] **Step 1: Write the failing test `tests/test_validator.py`**

```python
"""Tests for SQL query validator."""

from querycreator.core.query.validator import QueryValidator, ValidationResult
from querycreator.config.safety_rules import SafetyRules


def make_validator(
    large_tables: dict[str, int] | None = None,
    forbidden_patterns: list[str] | None = None,
) -> QueryValidator:
    rules = SafetyRules()
    if forbidden_patterns:
        rules.forbidden_patterns = forbidden_patterns
    return QueryValidator(
        rules=rules,
        table_row_counts=large_tables or {},
    )


# --- Allowed queries ---

def test_simple_select_passes():
    v = make_validator()
    r = v.validate("SELECT order_no, cust_cd FROM tb_order WHERE order_no = 'A001'")
    assert r.is_valid


def test_select_with_rownum_passes():
    v = make_validator()
    r = v.validate("SELECT * FROM tb_small WHERE ROWNUM <= 100")
    assert r.is_valid  # SELECT * allowed if not blocked on small table


def test_select_with_fetch_first_passes():
    v = make_validator()
    r = v.validate("SELECT col1 FROM tb_x FETCH FIRST 50 ROWS ONLY")
    assert r.is_valid


def test_subquery_passes():
    v = make_validator()
    r = v.validate(
        "SELECT a.order_no FROM tb_order a "
        "WHERE a.cust_cd IN (SELECT cust_cd FROM tb_cust WHERE active = 'Y') "
        "AND ROWNUM <= 100"
    )
    assert r.is_valid


def test_with_clause_passes():
    v = make_validator()
    r = v.validate(
        "WITH orders AS (SELECT order_no FROM tb_order WHERE status = '01') "
        "SELECT * FROM orders WHERE ROWNUM <= 100"
    )
    assert r.is_valid


# --- Blocked queries ---

def test_insert_blocked():
    v = make_validator()
    r = v.validate("INSERT INTO tb_order VALUES ('X', 'Y', SYSDATE)")
    assert not r.is_valid
    assert "SELECT" in r.reason


def test_update_blocked():
    v = make_validator()
    r = v.validate("UPDATE tb_order SET status_cd = '03' WHERE order_no = 'A001'")
    assert not r.is_valid


def test_delete_blocked():
    v = make_validator()
    r = v.validate("DELETE FROM tb_order WHERE order_no = 'A001'")
    assert not r.is_valid


def test_drop_blocked():
    v = make_validator()
    r = v.validate("DROP TABLE tb_order")
    assert not r.is_valid


def test_select_star_blocked():
    v = make_validator()
    r = v.validate("SELECT * FROM tb_order WHERE order_no = 'A001'")
    assert not r.is_valid
    assert "SELECT *" in r.reason or "*" in r.reason


def test_leading_wildcard_blocked():
    v = make_validator()
    r = v.validate("SELECT order_no FROM tb_order WHERE cust_cd LIKE '%ABC'")
    assert not r.is_valid
    assert "LIKE" in r.reason or "와일드카드" in r.reason.lower() or "wildcard" in r.reason.lower()


def test_large_table_without_where_blocked():
    v = make_validator(large_tables={"TB_PROD_PROGRESS": 5_000_000})
    r = v.validate("SELECT order_no, weight FROM tb_prod_progress FETCH FIRST 100 ROWS ONLY")
    assert not r.is_valid
    assert "WHERE" in r.reason or "조건" in r.reason


def test_large_table_with_where_passes():
    v = make_validator(large_tables={"TB_PROD_PROGRESS": 5_000_000})
    r = v.validate(
        "SELECT order_no, weight FROM tb_prod_progress "
        "WHERE prod_date >= DATE '2026-01-01' FETCH FIRST 100 ROWS ONLY"
    )
    assert r.is_valid


def test_forbidden_pattern_blocked():
    v = make_validator(forbidden_patterns=["CROSS JOIN"])
    r = v.validate("SELECT a.x, b.y FROM tb_a a CROSS JOIN tb_b b WHERE ROWNUM <= 10")
    assert not r.is_valid
    assert "CROSS JOIN" in r.reason


def test_no_row_limit_adds_warning():
    v = make_validator()
    r = v.validate("SELECT order_no FROM tb_order WHERE order_no = 'A001'")
    # Should pass but with a warning or auto-added limit info
    assert r.is_valid
    assert r.row_limit_missing


def test_function_call_passes():
    v = make_validator()
    r = v.validate("SELECT * FROM TABLE(F_SUM_PROGRESS('A001'))")
    # TABLE() function calls are special — SELECT * is OK here
    assert r.is_valid


def test_empty_query_blocked():
    v = make_validator()
    r = v.validate("")
    assert not r.is_valid


def test_multiple_statements_blocked():
    v = make_validator()
    r = v.validate("SELECT 1 FROM dual; DROP TABLE tb_order")
    assert not r.is_valid
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_validator.py -v 2>&1 | tail -5`
Expected: FAIL

- [ ] **Step 3: Create `src/querycreator/core/query/__init__.py`**

```python
"""Query processing modules."""
```

- [ ] **Step 4: Implement `src/querycreator/core/query/validator.py`**

```python
"""SQL query validator enforcing safety rules.

Validates LLM-generated SQL before execution:
- Only SELECT allowed
- No SELECT * (except TABLE() function calls)
- No leading wildcard LIKE
- Large tables require WHERE clause
- Row limit check (ROWNUM / FETCH FIRST)
- Custom forbidden patterns
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML

from querycreator.config.safety_rules import SafetyRules


@dataclass
class ValidationResult:
    """Result of query validation."""

    is_valid: bool
    reason: str = ""
    row_limit_missing: bool = False


class QueryValidator:
    """Validates SQL queries against safety rules."""

    def __init__(
        self,
        rules: SafetyRules,
        table_row_counts: dict[str, int] | None = None,
    ) -> None:
        self._rules = rules
        self._table_rows = {k.upper(): v for k, v in (table_row_counts or {}).items()}

    def validate(self, sql: str) -> ValidationResult:
        """Validate a SQL string. Returns ValidationResult."""
        sql = sql.strip()

        if not sql:
            return ValidationResult(False, "빈 쿼리입니다.")

        # Multiple statements check
        parsed = sqlparse.parse(sql)
        statements = [s for s in parsed if s.ttype is not sqlparse.tokens.Whitespace and str(s).strip()]
        if len(statements) > 1:
            return ValidationResult(False, "복수 SQL문은 허용되지 않습니다. 하나의 SELECT문만 사용하세요.")

        sql_upper = sql.upper()

        # Statement type check
        if not self._is_select(sql_upper):
            return ValidationResult(
                False,
                "SELECT 문만 허용됩니다. INSERT/UPDATE/DELETE/DROP 등은 사용할 수 없습니다.",
            )

        # SELECT * check (except TABLE() function calls)
        if self._rules.block_select_star and self._has_select_star(sql_upper):
            return ValidationResult(
                False,
                "SELECT * 는 허용되지 않습니다. 필요한 컬럼을 명시하세요.",
            )

        # Leading wildcard LIKE check
        if self._rules.block_leading_wildcard and self._has_leading_wildcard(sql_upper):
            return ValidationResult(
                False,
                "LIKE '%...' 패턴(앞쪽 와일드카드)은 성능 문제로 차단됩니다. 앞글자 일치(LIKE 'ABC%')만 사용하세요.",
            )

        # Large table without WHERE check
        large_table_issue = self._check_large_tables(sql_upper)
        if large_table_issue:
            return ValidationResult(False, large_table_issue)

        # Forbidden patterns
        for pattern in self._rules.forbidden_patterns:
            if pattern.upper() in sql_upper:
                return ValidationResult(False, f"금지된 패턴입니다: {pattern}")

        # Row limit check
        row_limit_missing = not self._has_row_limit(sql_upper)

        return ValidationResult(
            is_valid=True,
            row_limit_missing=row_limit_missing,
        )

    def _is_select(self, sql_upper: str) -> bool:
        """Check that the statement is a SELECT (or WITH...SELECT)."""
        stripped = sql_upper.lstrip()
        if stripped.startswith("SELECT") or stripped.startswith("WITH"):
            # Make sure no DML/DDL keywords appear as top-level statements
            for blocked in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "MERGE"):
                # Check if blocked keyword appears at statement level (not in subquery/string)
                if re.match(rf"^{blocked}\b", stripped):
                    return False
            return True
        return False

    def _has_select_star(self, sql_upper: str) -> bool:
        """Detect SELECT * but allow SELECT * FROM TABLE(func())."""
        if "TABLE(" in sql_upper:
            return False
        # Match SELECT * or SELECT alias.* patterns
        return bool(re.search(r"\bSELECT\s+\*\s", sql_upper))

    def _has_leading_wildcard(self, sql_upper: str) -> bool:
        """Detect LIKE '%...' patterns."""
        return bool(re.search(r"LIKE\s+'%", sql_upper))

    def _has_row_limit(self, sql_upper: str) -> bool:
        """Check for ROWNUM or FETCH FIRST."""
        return "ROWNUM" in sql_upper or "FETCH FIRST" in sql_upper or "FETCH NEXT" in sql_upper

    def _check_large_tables(self, sql_upper: str) -> str | None:
        """Check if large tables are queried without WHERE clause."""
        if not self._table_rows:
            return None

        # Extract table names from FROM/JOIN clauses
        for tbl_name, row_count in self._table_rows.items():
            if row_count < self._rules.large_table_threshold:
                continue
            if tbl_name in sql_upper:
                if "WHERE" not in sql_upper:
                    return (
                        f"대용량 테이블 {tbl_name} ({row_count:,}건)에 WHERE 조건이 없습니다. "
                        f"반드시 검색 조건을 추가하세요."
                    )
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_validator.py -v`
Expected: 17 passed

- [ ] **Step 6: Commit**

```bash
git add src/querycreator/core/query/ tests/test_validator.py
git commit -m "feat: SQL query validator - safety rules enforcement"
git push
```

---

### Task 7: Query Executor and Formatter

**Files:**
- Create: `src/querycreator/core/query/executor.py`
- Create: `src/querycreator/core/query/formatter.py`
- Create: `tests/test_executor.py`
- Create: `tests/test_formatter.py`

- [ ] **Step 1: Write the failing test `tests/test_executor.py`**

```python
"""Tests for query executor."""

from querycreator.core.query.executor import QueryExecutor, ExecutionResult
from querycreator.core.query.validator import QueryValidator
from querycreator.config.safety_rules import SafetyRules
from querycreator.db.mock_connection import MockConnection


def make_executor(mock_db: MockConnection) -> QueryExecutor:
    rules = SafetyRules()
    validator = QueryValidator(rules=rules, table_row_counts={})
    return QueryExecutor(db=mock_db, validator=validator, rules=rules)


def test_execute_valid_query(mock_db: MockConnection):
    executor = make_executor(mock_db)
    result = executor.execute("SELECT order_no, cust_cd FROM tb_order WHERE order_no = 'A001'")
    assert result.success
    assert result.rows is not None


def test_execute_invalid_query_returns_error(mock_db: MockConnection):
    executor = make_executor(mock_db)
    result = executor.execute("DELETE FROM tb_order")
    assert not result.success
    assert "SELECT" in result.error


def test_execute_returns_execution_time(mock_db: MockConnection):
    executor = make_executor(mock_db)
    result = executor.execute("SELECT order_no FROM tb_order WHERE order_no = 'A001'")
    assert result.execution_time_ms >= 0


def test_execute_function_call(mock_db: MockConnection):
    executor = make_executor(mock_db)
    result = executor.execute_function("F_SUM_PROGRESS", {"P_ORDER_NO": "A001"})
    assert result.success
    assert len(result.rows) > 0


def test_execute_unknown_function(mock_db: MockConnection):
    executor = make_executor(mock_db)
    result = executor.execute_function("F_NONEXISTENT", {"P_X": "1"})
    assert result.success  # Empty result is not an error
    assert len(result.rows) == 0


def test_execute_adds_row_limit_when_missing(mock_db: MockConnection):
    executor = make_executor(mock_db)
    result = executor.execute("SELECT order_no FROM tb_order WHERE order_no = 'A001'")
    assert result.success
    # Executor should have added FETCH FIRST or used max_rows
    assert result.row_limit_applied
```

- [ ] **Step 2: Write the failing test `tests/test_formatter.py`**

```python
"""Tests for result formatter."""

from querycreator.core.query.formatter import ResultFormatter


def test_format_rows_to_table():
    rows = [
        {"ORDER_NO": "A001", "CUST_CD": "C100"},
        {"ORDER_NO": "A002", "CUST_CD": "C200"},
    ]
    f = ResultFormatter()
    output = f.format_for_llm(rows)
    assert "A001" in output
    assert "ORDER_NO" in output


def test_format_empty_result():
    f = ResultFormatter()
    output = f.format_for_llm([])
    assert "결과 없음" in output or "0건" in output


def test_format_with_code_translation():
    rows = [
        {"PROC_CD": "010", "WEIGHT": 150.5},
        {"PROC_CD": "020", "WEIGHT": 145.2},
    ]
    code_map = {
        "PROC_CD": {"010": "원료투입", "020": "가열"},
    }
    f = ResultFormatter(code_mappings=code_map)
    output = f.format_for_llm(rows)
    assert "원료투입" in output
    assert "가열" in output


def test_format_large_result_truncated():
    rows = [{"ID": i, "VAL": f"value_{i}"} for i in range(2000)]
    f = ResultFormatter(max_display_rows=100)
    output = f.format_for_llm(rows)
    assert "100" in output or "건" in output


def test_format_summary_included():
    rows = [
        {"ORDER_NO": "A001", "WEIGHT": 100},
        {"ORDER_NO": "A002", "WEIGHT": 200},
    ]
    f = ResultFormatter()
    output = f.format_for_llm(rows)
    assert "2건" in output or "2 건" in output or "총 2" in output
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_executor.py tests/test_formatter.py -v 2>&1 | tail -5`
Expected: FAIL

- [ ] **Step 4: Implement `src/querycreator/core/query/executor.py`**

```python
"""Query executor — validates then runs SQL on Oracle."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from querycreator.config.safety_rules import SafetyRules
from querycreator.core.query.validator import QueryValidator
from querycreator.db.connection import DBConnection, QueryExecutionError


@dataclass
class ExecutionResult:
    """Result of a query execution."""

    success: bool
    rows: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    execution_time_ms: float = 0.0
    row_count: int = 0
    row_limit_applied: bool = False


class QueryExecutor:
    """Validates and executes queries safely."""

    def __init__(
        self,
        db: DBConnection,
        validator: QueryValidator,
        rules: SafetyRules,
    ) -> None:
        self._db = db
        self._validator = validator
        self._rules = rules

    def execute(self, sql: str) -> ExecutionResult:
        """Validate and execute a SELECT query."""
        validation = self._validator.validate(sql)
        if not validation.is_valid:
            return ExecutionResult(success=False, error=validation.reason)

        row_limit_applied = validation.row_limit_missing

        start = time.monotonic()
        try:
            rows = self._db.execute(
                sql,
                timeout_seconds=self._rules.timeout_seconds,
                max_rows=self._rules.max_rows,
            )
            elapsed = (time.monotonic() - start) * 1000

            return ExecutionResult(
                success=True,
                rows=rows,
                execution_time_ms=round(elapsed, 2),
                row_count=len(rows),
                row_limit_applied=row_limit_applied,
            )
        except QueryExecutionError as e:
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(
                success=False,
                error=self._friendly_error(e),
                execution_time_ms=round(elapsed, 2),
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(
                success=False,
                error=f"쿼리 실행 중 오류가 발생했습니다: {e}",
                execution_time_ms=round(elapsed, 2),
            )

    def execute_function(
        self, func_name: str, params: dict[str, Any],
    ) -> ExecutionResult:
        """Call a stored function and return results."""
        start = time.monotonic()
        try:
            rows = self._db.call_function(
                func_name,
                params,
                timeout_seconds=self._rules.timeout_seconds,
                max_rows=self._rules.max_rows,
            )
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(
                success=True,
                rows=rows,
                execution_time_ms=round(elapsed, 2),
                row_count=len(rows),
            )
        except QueryExecutionError as e:
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(
                success=False,
                error=self._friendly_error(e),
                execution_time_ms=round(elapsed, 2),
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ExecutionResult(
                success=False,
                error=f"펑션 호출 중 오류가 발생했습니다: {e}",
                execution_time_ms=round(elapsed, 2),
            )

    def _friendly_error(self, e: QueryExecutionError) -> str:
        code = e.ora_code
        if code == 1013:
            return "쿼리 실행 시간이 초과되었습니다 (타임아웃). 조건을 더 구체적으로 지정해주세요."
        if code == 942:
            return "테이블 또는 뷰가 존재하지 않습니다. 테이블명을 확인해주세요."
        if code == 904:
            return "컬럼명이 올바르지 않습니다. 컬럼명을 확인해주세요."
        if code == 936:
            return "SQL 문법 오류입니다. 쿼리를 확인해주세요."
        return f"데이터베이스 오류: {e.message}"
```

- [ ] **Step 5: Implement `src/querycreator/core/query/formatter.py`**

```python
"""Result formatter for LLM consumption.

Converts query results into a text format that LLMs can interpret
and relay to users. Includes code value translation.
"""

from __future__ import annotations

from typing import Any


class ResultFormatter:
    """Formats query results for LLM interpretation."""

    def __init__(
        self,
        code_mappings: dict[str, dict[str, str]] | None = None,
        max_display_rows: int = 100,
    ) -> None:
        self._code_mappings = code_mappings or {}
        self._max_display_rows = max_display_rows

    def format_for_llm(self, rows: list[dict[str, Any]]) -> str:
        """Format rows into a text representation for LLM."""
        if not rows:
            return "조회 결과 없음 (0건)"

        total = len(rows)
        display_rows = rows[: self._max_display_rows]
        truncated = total > self._max_display_rows

        # Translate codes
        translated = [self._translate_row(row) for row in display_rows]

        # Build markdown table
        columns = list(translated[0].keys())
        lines = []

        # Header
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")

        # Rows
        for row in translated:
            vals = [str(row.get(c, "")) for c in columns]
            lines.append("| " + " | ".join(vals) + " |")

        # Summary
        summary = f"\n총 {total}건"
        if truncated:
            summary += f" (상위 {self._max_display_rows}건만 표시)"

        return "\n".join(lines) + summary

    def _translate_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Replace code values with human-readable names."""
        translated = {}
        for col, val in row.items():
            col_upper = col.upper()
            if col_upper in self._code_mappings and str(val) in self._code_mappings[col_upper]:
                translated[col] = f"{self._code_mappings[col_upper][str(val)]}({val})"
            else:
                translated[col] = val
        return translated
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_executor.py tests/test_formatter.py -v`
Expected: 11 passed

- [ ] **Step 7: Commit**

```bash
git add src/querycreator/core/query/executor.py src/querycreator/core/query/formatter.py tests/test_executor.py tests/test_formatter.py
git commit -m "feat: query executor with timeout + result formatter with code translation"
git push
```

---

### Task 8: LLM Tools

**Files:**
- Create: `src/querycreator/core/tools/__init__.py`
- Create: `src/querycreator/core/tools/get_metadata.py`
- Create: `src/querycreator/core/tools/execute_query.py`
- Create: `src/querycreator/core/tools/call_function.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test `tests/test_tools.py`**

```python
"""Tests for LLM-facing tools."""

import os
import tempfile

import yaml

from querycreator.core.tools.get_metadata import GetMetadataTool
from querycreator.core.tools.execute_query import ExecuteQueryTool
from querycreator.core.tools.call_function import CallFunctionTool
from querycreator.core.metadata.catalog import MetadataCatalog
from querycreator.core.metadata.collector import MetadataCollector
from querycreator.core.metadata.dictionary import BusinessDictionary
from querycreator.core.query.executor import QueryExecutor
from querycreator.core.query.validator import QueryValidator
from querycreator.core.query.formatter import ResultFormatter
from querycreator.config.safety_rules import SafetyRules
from querycreator.db.mock_connection import MockConnection


SAMPLE_DICT = {
    "schema": "TEST",
    "tables": {
        "TB_ORDER": {
            "business_name": "주문",
            "description": "고객 주문 마스터",
            "key_columns": {"ORDER_NO": "주문번호"},
            "aliases": ["수주"],
        },
    },
    "functions": {
        "F_SUM_PROGRESS": {
            "business_name": "공정별 진행량 합산",
            "description": "주문번호 기준 합산",
            "parameters": {"P_ORDER_NO": "주문번호"},
            "usage": "공정별 생산량 조회",
        },
    },
    "joins": [],
}


def _build_tools(mock_db: MockConnection):
    tmpdir = tempfile.mkdtemp()
    with open(os.path.join(tmpdir, "test.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(SAMPLE_DICT, f, allow_unicode=True)

    dictionary = BusinessDictionary(tmpdir)
    dictionary.load()
    collector = MetadataCollector(mock_db, schema="TEST")
    catalog = MetadataCatalog(dictionary=dictionary, collector=collector, db=mock_db)
    catalog.initialize()

    rules = SafetyRules()
    validator = QueryValidator(rules=rules, table_row_counts={})
    executor = QueryExecutor(db=mock_db, validator=validator, rules=rules)
    formatter = ResultFormatter()

    get_metadata = GetMetadataTool(catalog=catalog)
    execute_query = ExecuteQueryTool(executor=executor, formatter=formatter)
    call_function = CallFunctionTool(executor=executor, formatter=formatter, catalog=catalog)

    return get_metadata, execute_query, call_function


def test_get_metadata_tool(mock_db: MockConnection):
    get_meta, _, _ = _build_tools(mock_db)
    result = get_meta.run(keyword="주문")
    assert "TB_ORDER" in result
    assert "주문" in result


def test_get_metadata_tool_schema():
    """Tool exposes a schema for LLM tool registration."""
    assert GetMetadataTool.tool_schema()["name"] == "get_metadata"
    assert "parameters" in GetMetadataTool.tool_schema()


def test_execute_query_tool(mock_db: MockConnection):
    _, exec_query, _ = _build_tools(mock_db)
    result = exec_query.run(sql="SELECT order_no FROM tb_order WHERE order_no = 'A001'")
    assert "성공" in result or "건" in result


def test_execute_query_tool_blocked_query(mock_db: MockConnection):
    _, exec_query, _ = _build_tools(mock_db)
    result = exec_query.run(sql="DELETE FROM tb_order")
    assert "SELECT" in result or "허용" in result


def test_call_function_tool(mock_db: MockConnection):
    _, _, call_func = _build_tools(mock_db)
    result = call_func.run(function_name="F_SUM_PROGRESS", parameters={"P_ORDER_NO": "A001"})
    assert "원료투입" in result or "PROC_CD" in result or "건" in result


def test_call_function_tool_unknown(mock_db: MockConnection):
    _, _, call_func = _build_tools(mock_db)
    result = call_func.run(function_name="F_NONEXISTENT", parameters={"P_X": "1"})
    # Should not crash — returns empty or not-found message
    assert "0건" in result or "없음" in result or "존재하지 않" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_tools.py -v 2>&1 | tail -5`
Expected: FAIL

- [ ] **Step 3: Create `src/querycreator/core/tools/__init__.py`**

```python
"""LLM-callable tools for Agent."""
```

- [ ] **Step 4: Implement `src/querycreator/core/tools/get_metadata.py`**

```python
"""get_metadata tool — searches business dictionary + physical metadata."""

from __future__ import annotations

import json
from typing import Any

from querycreator.core.metadata.catalog import MetadataCatalog


class GetMetadataTool:
    """LLM-callable tool: look up table/function metadata by keyword."""

    def __init__(self, catalog: MetadataCatalog) -> None:
        self._catalog = catalog

    def run(self, keyword: str) -> str:
        """Search metadata by business keyword or table name.

        Returns a formatted string with table info, columns, indexes,
        warnings, functions, and join relationships.
        """
        results = self._catalog.search(keyword)
        parts = []

        for tbl in results.get("tables", []):
            section = [f"## 테이블: {tbl['table_name']} ({tbl.get('business_name', '')})"]
            section.append(f"설명: {tbl.get('description', '')}")
            section.append(f"행 수: {tbl.get('num_rows', '알 수 없음'):,}건")

            if tbl.get("warnings"):
                section.append("⚠ 주의사항:")
                for w in tbl["warnings"]:
                    section.append(f"  - {w}")

            if tbl.get("indexed_columns"):
                section.append(f"인덱스 컬럼: {', '.join(tbl['indexed_columns'])}")

            if tbl.get("key_columns"):
                section.append("주요 컬럼:")
                for col, desc in tbl["key_columns"].items():
                    section.append(f"  - {col}: {desc}")

            if tbl.get("columns"):
                section.append("전체 컬럼:")
                for col in tbl["columns"]:
                    comment = tbl.get("comments", {}).get(col["column_name"], "")
                    nullable = "" if col.get("nullable") else " (NOT NULL)"
                    section.append(
                        f"  - {col['column_name']} {col['data_type']}"
                        f"{nullable}"
                        f"{' -- ' + comment if comment else ''}"
                    )

            parts.append("\n".join(section))

        for func in results.get("functions", []):
            section = [f"## 펑션: {func['function_name']} ({func.get('business_name', '')})"]
            section.append(f"설명: {func.get('description', '')}")
            section.append(f"용도: {func.get('usage', '')}")
            if func.get("parameters"):
                section.append("파라미터:")
                for p, desc in func["parameters"].items():
                    section.append(f"  - {p}: {desc}")
            parts.append("\n".join(section))

        for join in results.get("joins", []):
            tables = ", ".join(join.get("tables", []))
            condition = join.get("condition", "")
            parts.append(f"## 조인: {tables}\n조건: {condition}\n설명: {join.get('description', '')}")

        if not parts:
            return f"'{keyword}'에 대한 메타데이터를 찾을 수 없습니다."

        return "\n\n".join(parts)

    @staticmethod
    def tool_schema() -> dict[str, Any]:
        """Return tool schema for Agent registration."""
        return {
            "name": "get_metadata",
            "description": (
                "업무 키워드 또는 테이블명으로 DB 메타데이터를 조회합니다. "
                "테이블 구조, 컬럼, 인덱스, 관련 펑션, 조인 관계를 반환합니다. "
                "쿼리를 작성하기 전에 반드시 이 도구로 관련 테이블 정보를 확인하세요."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색할 업무 키워드 (예: '주문', '생산량') 또는 테이블명 (예: 'TB_ORDER')",
                    },
                },
                "required": ["keyword"],
            },
        }
```

- [ ] **Step 5: Implement `src/querycreator/core/tools/execute_query.py`**

```python
"""execute_query tool — validates and runs SQL on Oracle."""

from __future__ import annotations

from typing import Any

from querycreator.core.query.executor import QueryExecutor
from querycreator.core.query.formatter import ResultFormatter


class ExecuteQueryTool:
    """LLM-callable tool: execute a SELECT query."""

    def __init__(self, executor: QueryExecutor, formatter: ResultFormatter) -> None:
        self._executor = executor
        self._formatter = formatter

    def run(self, sql: str) -> str:
        """Validate, execute SQL, and return formatted results."""
        result = self._executor.execute(sql)

        if not result.success:
            return (
                f"쿼리 실행 실패: {result.error}\n\n"
                "위 사유를 참고하여 쿼리를 수정한 후 다시 시도하세요."
            )

        formatted = self._formatter.format_for_llm(result.rows)

        meta = f"\n\n실행 시간: {result.execution_time_ms}ms"
        if result.row_limit_applied:
            meta += f" (결과 행수 제한 적용: 최대 {result.row_count}건)"

        return formatted + meta

    @staticmethod
    def tool_schema() -> dict[str, Any]:
        """Return tool schema for Agent registration."""
        return {
            "name": "execute_query",
            "description": (
                "Oracle DB에서 SELECT 쿼리를 실행합니다. "
                "쿼리는 안전성 검증을 거친 후 실행됩니다. "
                "반드시 get_metadata로 테이블 정보를 확인한 후 사용하세요. "
                "규칙: SELECT만 허용, SELECT * 금지, 인덱스 컬럼 활용, "
                "대용량 테이블은 반드시 WHERE 조건 포함."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "실행할 SELECT SQL문",
                    },
                },
                "required": ["sql"],
            },
        }
```

- [ ] **Step 6: Implement `src/querycreator/core/tools/call_function.py`**

```python
"""call_function tool — calls Oracle stored functions."""

from __future__ import annotations

from typing import Any

from querycreator.core.metadata.catalog import MetadataCatalog
from querycreator.core.query.executor import QueryExecutor
from querycreator.core.query.formatter import ResultFormatter


class CallFunctionTool:
    """LLM-callable tool: call a stored function."""

    def __init__(
        self,
        executor: QueryExecutor,
        formatter: ResultFormatter,
        catalog: MetadataCatalog,
    ) -> None:
        self._executor = executor
        self._formatter = formatter
        self._catalog = catalog

    def run(self, function_name: str, parameters: dict[str, Any]) -> str:
        """Call a stored function and return formatted results."""
        result = self._executor.execute_function(function_name, parameters)

        if not result.success:
            return f"펑션 호출 실패: {result.error}"

        formatted = self._formatter.format_for_llm(result.rows)
        meta = f"\n\n펑션: {function_name} | 실행 시간: {result.execution_time_ms}ms"
        return formatted + meta

    @staticmethod
    def tool_schema() -> dict[str, Any]:
        """Return tool schema for Agent registration."""
        return {
            "name": "call_function",
            "description": (
                "Oracle 스토어드 펑션을 호출합니다. "
                "get_metadata에서 펑션 정보를 확인한 후, "
                "적합한 펑션이 있으면 직접 SQL 대신 이 도구를 사용하세요."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "호출할 펑션명 (예: 'F_SUM_PROGRESS')",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "펑션 파라미터 (예: {\"P_ORDER_NO\": \"A001\"})",
                    },
                },
                "required": ["function_name", "parameters"],
            },
        }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_tools.py -v`
Expected: 6 passed

- [ ] **Step 8: Commit**

```bash
git add src/querycreator/core/tools/ tests/test_tools.py
git commit -m "feat: LLM tools - get_metadata, execute_query, call_function"
git push
```

---

### Task 9: App Entry Point

**Files:**
- Create: `src/querycreator/app.py`

- [ ] **Step 1: Implement `src/querycreator/app.py`**

```python
"""Agent app entry point.

Initializes all components and exposes tools for LLM invocation.
"""

from __future__ import annotations

from typing import Any

from querycreator.config.db_config import DBConfig
from querycreator.config.safety_rules import SafetyRules
from querycreator.config.schema_config import get_target_schemas
from querycreator.core.metadata.catalog import MetadataCatalog
from querycreator.core.metadata.collector import MetadataCollector
from querycreator.core.metadata.dictionary import BusinessDictionary
from querycreator.core.query.executor import QueryExecutor
from querycreator.core.query.formatter import ResultFormatter
from querycreator.core.query.validator import QueryValidator
from querycreator.core.tools.call_function import CallFunctionTool
from querycreator.core.tools.execute_query import ExecuteQueryTool
from querycreator.core.tools.get_metadata import GetMetadataTool
from querycreator.db.connection import DBConnection, OracleConnection


class QueryCreatorApp:
    """Main application class — wires all components together."""

    def __init__(
        self,
        db: DBConnection,
        dict_dir: str,
        schema: str,
        common_code_table: str = "TB_COMMON_CODE",
    ) -> None:
        self._db = db
        rules = SafetyRules()

        dictionary = BusinessDictionary(dict_dir)
        dictionary.load()

        collector = MetadataCollector(db, schema=schema)
        catalog = MetadataCatalog(
            dictionary=dictionary,
            collector=collector,
            db=db,
            common_code_table=common_code_table,
        )
        catalog.initialize()

        # Build table row counts for validator
        table_rows = {
            tbl: info["num_rows"]
            for tbl, info in collector.collect_tables().items()
        }

        validator = QueryValidator(rules=rules, table_row_counts=table_rows)
        executor = QueryExecutor(db=db, validator=validator, rules=rules)
        formatter = ResultFormatter()

        self.get_metadata = GetMetadataTool(catalog=catalog)
        self.execute_query = ExecuteQueryTool(executor=executor, formatter=formatter)
        self.call_function = CallFunctionTool(
            executor=executor, formatter=formatter, catalog=catalog,
        )

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return all tool schemas for Agent registration."""
        return [
            GetMetadataTool.tool_schema(),
            ExecuteQueryTool.tool_schema(),
            CallFunctionTool.tool_schema(),
        ]

    def handle_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Route a tool call from Agent to the appropriate handler."""
        if tool_name == "get_metadata":
            return self.get_metadata.run(**arguments)
        elif tool_name == "execute_query":
            return self.execute_query.run(**arguments)
        elif tool_name == "call_function":
            return self.call_function.run(**arguments)
        else:
            return f"알 수 없는 도구입니다: {tool_name}"


def create_app_from_env(dict_dir: str = "data/dictionaries") -> QueryCreatorApp:
    """Create app instance using environment variables for config."""
    config = DBConfig.from_env()
    schemas = get_target_schemas()
    schema = schemas[0] if schemas else "PROD"

    db = OracleConnection(dsn=config.dsn, user=config.user, password=config.password)
    return QueryCreatorApp(db=db, dict_dir=dict_dir, schema=schema)
```

- [ ] **Step 2: Commit**

```bash
git add src/querycreator/app.py
git commit -m "feat: app entry point - wires all components for Agent"
git push
```

---

### Task 10: Query Logging

**Files:**
- Create: `src/querycreator/logging/__init__.py`
- Create: `src/querycreator/logging/query_log.py`
- Create: `src/querycreator/logging/analyzer.py`
- Create: `tests/test_query_log.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write the failing test `tests/test_query_log.py`**

```python
"""Tests for query logging."""

import json
import os
import tempfile

from querycreator.logging.query_log import QueryLog, LogEntry


def test_log_entry_creation():
    entry = LogEntry(
        user_question="주문 A001의 상태",
        generated_sql="SELECT status_cd FROM tb_order WHERE order_no = 'A001'",
        tables_used=["TB_ORDER"],
        execution_time_ms=45.2,
        success=True,
        row_count=1,
    )
    assert entry.success
    assert "TB_ORDER" in entry.tables_used


def test_log_write_and_read():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "query.jsonl")
        logger = QueryLog(log_path)

        entry = LogEntry(
            user_question="테스트 질문",
            generated_sql="SELECT 1 FROM dual",
            tables_used=["DUAL"],
            execution_time_ms=10.0,
            success=True,
            row_count=1,
        )
        logger.write(entry)

        entries = logger.read_all()
        assert len(entries) == 1
        assert entries[0]["user_question"] == "테스트 질문"


def test_log_multiple_entries():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "query.jsonl")
        logger = QueryLog(log_path)

        for i in range(5):
            logger.write(LogEntry(
                user_question=f"질문 {i}",
                generated_sql=f"SELECT {i} FROM dual",
                tables_used=["DUAL"],
                execution_time_ms=float(i * 10),
                success=True,
                row_count=1,
            ))

        entries = logger.read_all()
        assert len(entries) == 5


def test_log_failed_entry():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "query.jsonl")
        logger = QueryLog(log_path)

        logger.write(LogEntry(
            user_question="잘못된 질문",
            generated_sql="DELETE FROM tb_order",
            tables_used=[],
            execution_time_ms=0,
            success=False,
            row_count=0,
            error="SELECT만 허용",
        ))

        entries = logger.read_all()
        assert not entries[0]["success"]
        assert "SELECT" in entries[0]["error"]
```

- [ ] **Step 2: Write the failing test `tests/test_analyzer.py`**

```python
"""Tests for query log analyzer."""

from querycreator.logging.analyzer import QueryAnalyzer


def _sample_logs():
    return [
        {"tables_used": ["TB_ORDER"], "execution_time_ms": 50, "success": True},
        {"tables_used": ["TB_ORDER"], "execution_time_ms": 200, "success": True},
        {"tables_used": ["TB_ORDER", "TB_PROD_PROGRESS"], "execution_time_ms": 5000, "success": True},
        {"tables_used": ["TB_ORDER", "TB_PROD_PROGRESS"], "execution_time_ms": 31000, "success": False, "error": "타임아웃"},
        {"tables_used": ["TB_PRODUCT"], "execution_time_ms": 30, "success": True},
        {"tables_used": ["TB_PROD_PROGRESS"], "execution_time_ms": 28000, "success": True},
    ]


def test_slow_query_patterns():
    analyzer = QueryAnalyzer(threshold_ms=1000)
    patterns = analyzer.find_slow_patterns(_sample_logs())
    # TB_ORDER+TB_PROD_PROGRESS join is slow
    assert any("TB_PROD_PROGRESS" in str(p["tables"]) for p in patterns)


def test_failure_rate():
    analyzer = QueryAnalyzer()
    report = analyzer.failure_report(_sample_logs())
    assert report["total"] == 6
    assert report["failed"] == 1


def test_table_usage_ranking():
    analyzer = QueryAnalyzer()
    ranking = analyzer.table_usage_ranking(_sample_logs())
    # TB_ORDER should be most used
    assert ranking[0][0] == "TB_ORDER" or ranking[0][0] == "TB_PROD_PROGRESS"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_query_log.py tests/test_analyzer.py -v 2>&1 | tail -5`
Expected: FAIL

- [ ] **Step 4: Create `src/querycreator/logging/__init__.py`**

```python
"""Logging and analysis modules."""
```

- [ ] **Step 5: Implement `src/querycreator/logging/query_log.py`**

```python
"""Query execution log — records every tool invocation to JSONL."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class LogEntry:
    """One query execution record."""

    user_question: str
    generated_sql: str
    tables_used: list[str]
    execution_time_ms: float
    success: bool
    row_count: int = 0
    error: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class QueryLog:
    """Append-only JSONL query log."""

    def __init__(self, log_path: str) -> None:
        self._path = log_path

    def write(self, entry: LogEntry) -> None:
        """Append a log entry."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        """Read all log entries."""
        if not os.path.exists(self._path):
            return []
        entries = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries
```

- [ ] **Step 6: Implement `src/querycreator/logging/analyzer.py`**

```python
"""Query log analyzer — finds slow patterns and usage stats."""

from __future__ import annotations

from collections import Counter
from typing import Any


class QueryAnalyzer:
    """Analyzes query logs for performance patterns."""

    def __init__(self, threshold_ms: float = 1000) -> None:
        self._threshold_ms = threshold_ms

    def find_slow_patterns(self, logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find table/join patterns that are consistently slow."""
        pattern_times: dict[str, list[float]] = {}

        for log in logs:
            tables = sorted(log.get("tables_used", []))
            key = "+".join(tables) if tables else "UNKNOWN"
            time_ms = log.get("execution_time_ms", 0)
            if key not in pattern_times:
                pattern_times[key] = []
            pattern_times[key].append(time_ms)

        slow_patterns = []
        for pattern, times in pattern_times.items():
            avg_time = sum(times) / len(times)
            if avg_time >= self._threshold_ms:
                slow_patterns.append({
                    "tables": pattern,
                    "avg_time_ms": round(avg_time, 1),
                    "max_time_ms": round(max(times), 1),
                    "count": len(times),
                })

        return sorted(slow_patterns, key=lambda x: x["avg_time_ms"], reverse=True)

    def failure_report(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate failure summary."""
        total = len(logs)
        failed = sum(1 for log in logs if not log.get("success", True))
        return {
            "total": total,
            "failed": failed,
            "success_rate": round((total - failed) / total * 100, 1) if total else 0,
        }

    def table_usage_ranking(
        self, logs: list[dict[str, Any]],
    ) -> list[tuple[str, int]]:
        """Rank tables by usage frequency."""
        counter: Counter[str] = Counter()
        for log in logs:
            for tbl in log.get("tables_used", []):
                counter[tbl] += 1
        return counter.most_common()
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_query_log.py tests/test_analyzer.py -v`
Expected: 7 passed

- [ ] **Step 8: Commit**

```bash
git add src/querycreator/logging/ tests/test_query_log.py tests/test_analyzer.py
git commit -m "feat: query logging and slow-pattern analyzer"
git push
```

---

### Task 11: Operator Knowledge Management

**Files:**
- Create: `src/querycreator/core/metadata/knowledge.py`
- Create: `data/knowledge/sample_production.yaml`
- Create: `tests/test_knowledge.py`

- [ ] **Step 1: Write the failing test `tests/test_knowledge.py`**

```python
"""Tests for operator knowledge base."""

import os
import tempfile

import yaml

from querycreator.core.metadata.knowledge import KnowledgeBase


SAMPLE_KNOWLEDGE = {
    "schema": "PROD",
    "table_hints": {
        "TB_PROD_PROGRESS": {
            "index_hints": ["PROD_DATE 인덱스를 반드시 활용하세요"],
            "warnings": ["10억건 이상 - 반드시 날짜 조건 필수"],
            "sample_queries": [
                {
                    "description": "주문별 공정별 생산량 합계",
                    "sql": "SELECT proc_cd, SUM(weight) FROM tb_prod_progress WHERE order_no = :order_no GROUP BY proc_cd",
                },
            ],
        },
    },
    "join_rules": [
        {
            "tables": ["TB_ORDER", "TB_PROD_PROGRESS"],
            "hint": "반드시 ORDER_NO로 조인. PLANT_CD도 포함하면 더 빠름.",
        },
    ],
    "forbidden_patterns": [
        "CROSS JOIN",
        "CONNECT BY",
    ],
}


def _make_kb() -> tuple[KnowledgeBase, str]:
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "prod.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(SAMPLE_KNOWLEDGE, f, allow_unicode=True)
    kb = KnowledgeBase(tmpdir)
    kb.load()
    return kb, tmpdir


def test_load_knowledge():
    kb, _ = _make_kb()
    hints = kb.get_table_hints("TB_PROD_PROGRESS")
    assert hints is not None
    assert len(hints["index_hints"]) > 0


def test_get_sample_queries():
    kb, _ = _make_kb()
    samples = kb.get_sample_queries("TB_PROD_PROGRESS")
    assert len(samples) > 0
    assert "proc_cd" in samples[0]["sql"]


def test_get_join_rules():
    kb, _ = _make_kb()
    rules = kb.get_join_rules("TB_ORDER", "TB_PROD_PROGRESS")
    assert len(rules) > 0
    assert "ORDER_NO" in rules[0]["hint"]


def test_get_forbidden_patterns():
    kb, _ = _make_kb()
    patterns = kb.get_forbidden_patterns()
    assert "CROSS JOIN" in patterns


def test_no_hints_for_unknown_table():
    kb, _ = _make_kb()
    hints = kb.get_table_hints("TB_NONEXISTENT")
    assert hints is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_knowledge.py -v 2>&1 | tail -5`
Expected: FAIL

- [ ] **Step 3: Implement `src/querycreator/core/metadata/knowledge.py`**

```python
"""Operator knowledge base — hints, sample queries, rules.

Loaded from YAML files in the knowledge directory.
Operators add knowledge incrementally as issues arise.
"""

from __future__ import annotations

import os
from typing import Any

import yaml


class KnowledgeBase:
    """Manages operator-provided hints and rules."""

    def __init__(self, knowledge_dir: str) -> None:
        self._dir = knowledge_dir
        self._table_hints: dict[str, dict[str, Any]] = {}
        self._join_rules: list[dict[str, Any]] = []
        self._forbidden_patterns: list[str] = []

    def load(self) -> None:
        """Load all YAML knowledge files."""
        self._table_hints.clear()
        self._join_rules.clear()
        self._forbidden_patterns.clear()

        if not os.path.isdir(self._dir):
            return

        for fname in os.listdir(self._dir):
            if not fname.endswith((".yaml", ".yml")) or fname.startswith("_"):
                continue
            path = os.path.join(self._dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            self._load_data(data)

    def _load_data(self, data: dict[str, Any]) -> None:
        for tbl_name, hints in data.get("table_hints", {}).items():
            self._table_hints[tbl_name.upper()] = hints

        self._join_rules.extend(data.get("join_rules", []))
        self._forbidden_patterns.extend(data.get("forbidden_patterns", []))

    def get_table_hints(self, table_name: str) -> dict[str, Any] | None:
        """Get operator hints for a specific table."""
        return self._table_hints.get(table_name.upper())

    def get_sample_queries(self, table_name: str) -> list[dict[str, Any]]:
        """Get sample queries for a table."""
        hints = self._table_hints.get(table_name.upper())
        if not hints:
            return []
        return hints.get("sample_queries", [])

    def get_join_rules(self, *table_names: str) -> list[dict[str, Any]]:
        """Get join rules involving the given tables."""
        names_upper = {t.upper() for t in table_names}
        matched = []
        for rule in self._join_rules:
            rule_tables = {t.upper() for t in rule.get("tables", [])}
            if rule_tables & names_upper:
                matched.append(rule)
        return matched

    def get_forbidden_patterns(self) -> list[str]:
        """Get all forbidden SQL patterns."""
        return list(self._forbidden_patterns)
```

- [ ] **Step 4: Create `data/knowledge/sample_production.yaml`**

```yaml
schema: PROD

table_hints:
  TB_PROD_PROGRESS:
    index_hints:
      - "PROD_DATE 컬럼에 인덱스가 있으므로 날짜 조건에 반드시 활용하세요"
      - "ORDER_NO 컬럼에 인덱스가 있으므로 주문번호 조건 시 활용하세요"
    warnings:
      - "대용량 테이블 - 반드시 WHERE 조건 필수"
      - "날짜 범위를 최대 3개월로 제한하세요"
    sample_queries:
      - description: "주문별 공정별 생산량 합계"
        sql: >
          SELECT proc_cd, SUM(weight) AS total_weight
          FROM tb_prod_progress
          WHERE order_no = :order_no
          GROUP BY proc_cd
          ORDER BY proc_cd

      - description: "오늘 생산 현황"
        sql: >
          SELECT proc_cd, COUNT(*) AS cnt, SUM(weight) AS total_weight
          FROM tb_prod_progress
          WHERE prod_date = TRUNC(SYSDATE)
          GROUP BY proc_cd

join_rules:
  - tables: [TB_ORDER, TB_PROD_PROGRESS]
    hint: "반드시 ORDER_NO로 조인하세요."

forbidden_patterns:
  - "CROSS JOIN"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_knowledge.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add src/querycreator/core/metadata/knowledge.py data/knowledge/ tests/test_knowledge.py
git commit -m "feat: operator knowledge base - hints, sample queries, join rules"
git push
```

---

### Task 12: E2E Integration Tests

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: Write E2E test scenarios**

```python
"""End-to-end integration tests.

Simulates the full flow: user question → metadata lookup → SQL generation → execution.
Uses mock DB throughout.
"""

import os
import tempfile

import yaml

from querycreator.app import QueryCreatorApp
from querycreator.db.mock_connection import MockConnection, MockData


DICT_DATA = {
    "schema": "TEST",
    "tables": {
        "TB_ORDER": {
            "business_name": "주문",
            "description": "고객 주문 마스터",
            "key_columns": {"ORDER_NO": "주문번호", "CUST_CD": "고객코드", "ORDER_DATE": "주문일자", "STATUS_CD": "상태코드"},
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
            "description": "주문번호 기준 합산",
            "parameters": {"P_ORDER_NO": "주문번호"},
            "usage": "공정별 생산량 조회",
        },
    },
    "joins": [
        {"tables": ["TB_ORDER", "TB_PROD_PROGRESS"], "condition": "TB_ORDER.ORDER_NO = TB_PROD_PROGRESS.ORDER_NO", "description": "주문-진행량"},
    ],
}


def _make_app(mock_db: MockConnection) -> QueryCreatorApp:
    tmpdir = tempfile.mkdtemp()
    with open(os.path.join(tmpdir, "test.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(DICT_DATA, f, allow_unicode=True)
    return QueryCreatorApp(db=mock_db, dict_dir=tmpdir, schema="TEST")


def test_e2e_metadata_lookup(mock_db: MockConnection):
    """Scenario: user asks about '주문' → metadata returned."""
    app = _make_app(mock_db)
    result = app.handle_tool_call("get_metadata", {"keyword": "주문"})
    assert "TB_ORDER" in result
    assert "주문번호" in result


def test_e2e_select_query(mock_db: MockConnection):
    """Scenario: LLM generates a SELECT query → executed successfully."""
    app = _make_app(mock_db)
    result = app.handle_tool_call(
        "execute_query",
        {"sql": "SELECT order_no, cust_cd FROM tb_order WHERE order_no = 'A001'"},
    )
    assert "건" in result  # Should contain row count


def test_e2e_function_call(mock_db: MockConnection):
    """Scenario: LLM calls stored function → results returned."""
    app = _make_app(mock_db)
    result = app.handle_tool_call(
        "call_function",
        {"function_name": "F_SUM_PROGRESS", "parameters": {"P_ORDER_NO": "A001"}},
    )
    assert "F_SUM_PROGRESS" in result


def test_e2e_blocked_query(mock_db: MockConnection):
    """Scenario: LLM generates DELETE → blocked with reason."""
    app = _make_app(mock_db)
    result = app.handle_tool_call(
        "execute_query",
        {"sql": "DELETE FROM tb_order WHERE order_no = 'A001'"},
    )
    assert "SELECT" in result
    assert "실패" in result


def test_e2e_select_star_blocked(mock_db: MockConnection):
    """Scenario: LLM generates SELECT * → blocked."""
    app = _make_app(mock_db)
    result = app.handle_tool_call(
        "execute_query",
        {"sql": "SELECT * FROM tb_order WHERE order_no = 'A001'"},
    )
    assert "실패" in result


def test_e2e_unknown_tool(mock_db: MockConnection):
    """Scenario: unknown tool name → error message."""
    app = _make_app(mock_db)
    result = app.handle_tool_call("nonexistent_tool", {})
    assert "알 수 없는" in result


def test_e2e_tool_schemas(mock_db: MockConnection):
    """Tool schemas are well-formed for registration."""
    app = _make_app(mock_db)
    schemas = app.get_tool_schemas()
    assert len(schemas) == 3
    names = {s["name"] for s in schemas}
    assert names == {"get_metadata", "execute_query", "call_function"}
```

- [ ] **Step 2: Run E2E tests**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_e2e.py -v`
Expected: 7 passed

- [ ] **Step 3: Run full test suite**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: E2E integration tests - full flow scenarios"
git push
```

---

### Task 13: System Prompt for LLM

**Files:**
- Create: `prompts/system_prompt.md`

- [ ] **Step 1: Write system prompt**

```markdown
# QueryCreator 시스템 프롬프트

당신은 Oracle DB 데이터 조회를 도와주는 AI 어시스턴트입니다.
사용자의 자연어 질문을 이해하고, DB에서 데이터를 조회하여 결과를 알려줍니다.

## 사용 가능한 도구

1. **get_metadata** — 테이블/컬럼/펑션 정보 조회
2. **execute_query** — SQL 쿼리 실행
3. **call_function** — 스토어드 펑션 호출

## 작업 순서

**반드시 이 순서를 따르세요:**

1. 사용자 질문에서 핵심 키워드를 파악합니다.
2. `get_metadata`를 호출하여 관련 테이블/펑션 정보를 확인합니다.
3. 메타데이터 결과를 보고 판단합니다:
   - 적합한 **스토어드 펑션**이 있으면 → `call_function` 사용
   - 없으면 → SQL을 직접 작성하여 `execute_query` 사용
4. 결과를 사용자에게 자연어로 정리하여 응답합니다.

## SQL 작성 규칙

- **SELECT만 가능합니다.** INSERT/UPDATE/DELETE는 차단됩니다.
- **SELECT * 금지** — 필요한 컬럼만 명시하세요.
- **대용량 테이블은 반드시 WHERE 조건을 포함**하세요. 메타데이터의 행 수와 경고를 확인하세요.
- **인덱스 컬럼을 활용**하세요. 메타데이터에 인덱스 컬럼 정보가 포함되어 있습니다.
- **LIKE 사용 시 앞글자 일치만** 허용됩니다. `LIKE '%...'`는 차단됩니다.
- 결과 행수가 많을 수 있으므로 **FETCH FIRST N ROWS ONLY**를 적절히 사용하세요.
- 코드값(예: STATUS_CD = '01')은 결과에 자동으로 업무명이 함께 표시됩니다.

## 응답 가이드

- 조회 결과를 표 형태로 정리해주세요.
- 코드값이 있으면 업무명을 함께 알려주세요.
- 데이터가 없으면 "조회 결과가 없습니다"라고 안내하세요.
- 쿼리 실행이 실패하면 에러 사유를 확인하고 쿼리를 수정하여 재시도하세요 (최대 2회).

## 주의사항

- 메타데이터의 ⚠ 주의사항을 반드시 확인하고 따르세요.
- 조인 시 메타데이터에 명시된 조인 조건을 사용하세요.
- 샘플 쿼리가 있으면 참고하여 유사한 패턴으로 작성하세요.
- 사용자가 테이블명이나 컬럼명을 직접 언급하면 그대로 사용하세요.
```

- [ ] **Step 2: Commit**

```bash
git add prompts/
git commit -m "feat: LLM system prompt for Agent"
git push
```

---

### Task 14: Admin CLI Tool

**Files:**
- Create: `src/querycreator/admin/__init__.py`
- Create: `src/querycreator/admin/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test `tests/test_cli.py`**

```python
"""Tests for admin CLI."""

import os
import tempfile

from querycreator.admin.cli import validate_dictionary, generate_report


def test_validate_dictionary_valid():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("""
schema: PROD
tables:
  TB_ORDER:
    business_name: 주문
    description: 주문 테이블
    key_columns:
      ORDER_NO: 주문번호
functions: {}
joins: []
""")
        f.flush()
        errors = validate_dictionary(f.name)
        assert len(errors) == 0
    os.unlink(f.name)


def test_validate_dictionary_missing_schema():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("""
tables:
  TB_ORDER:
    business_name: 주문
""")
        f.flush()
        errors = validate_dictionary(f.name)
        assert any("schema" in e.lower() for e in errors)
    os.unlink(f.name)


def test_validate_dictionary_missing_business_name():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("""
schema: PROD
tables:
  TB_ORDER:
    description: 주문 테이블
""")
        f.flush()
        errors = validate_dictionary(f.name)
        assert any("business_name" in e for e in errors)
    os.unlink(f.name)


def test_generate_report_from_logs():
    logs = [
        {"tables_used": ["TB_ORDER"], "execution_time_ms": 50, "success": True},
        {"tables_used": ["TB_ORDER"], "execution_time_ms": 200, "success": True},
        {"tables_used": ["TB_ORDER"], "execution_time_ms": 5000, "success": False, "error": "타임아웃"},
    ]
    report = generate_report(logs)
    assert "총 3건" in report or "3건" in report
    assert "실패" in report
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_cli.py -v 2>&1 | tail -5`
Expected: FAIL

- [ ] **Step 3: Create `src/querycreator/admin/__init__.py`**

```python
"""Admin tools and CLI."""
```

- [ ] **Step 4: Implement `src/querycreator/admin/cli.py`**

```python
"""Admin CLI functions for operator convenience.

Provides dictionary validation, reporting, and management utilities.
"""

from __future__ import annotations

from typing import Any

import yaml

from querycreator.logging.analyzer import QueryAnalyzer


def validate_dictionary(yaml_path: str) -> list[str]:
    """Validate a business dictionary YAML file.

    Returns list of error messages. Empty list = valid.
    """
    errors = []

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return ["파일이 비어있습니다."]

    if "schema" not in data:
        errors.append("'schema' 필드가 필요합니다.")

    tables = data.get("tables", {})
    for tbl_name, tbl_info in tables.items():
        if not isinstance(tbl_info, dict):
            errors.append(f"테이블 {tbl_name}: 잘못된 형식입니다.")
            continue
        if "business_name" not in tbl_info:
            errors.append(f"테이블 {tbl_name}: 'business_name' 필드가 필요합니다.")
        if "description" not in tbl_info:
            errors.append(f"테이블 {tbl_name}: 'description' 필드가 필요합니다.")

    functions = data.get("functions", {})
    for func_name, func_info in functions.items():
        if not isinstance(func_info, dict):
            errors.append(f"펑션 {func_name}: 잘못된 형식입니다.")
            continue
        if "business_name" not in func_info:
            errors.append(f"펑션 {func_name}: 'business_name' 필드가 필요합니다.")
        if "parameters" not in func_info:
            errors.append(f"펑션 {func_name}: 'parameters' 필드가 필요합니다.")

    return errors


def generate_report(logs: list[dict[str, Any]]) -> str:
    """Generate a text report from query logs."""
    analyzer = QueryAnalyzer()

    failure = analyzer.failure_report(logs)
    ranking = analyzer.table_usage_ranking(logs)
    slow = analyzer.find_slow_patterns(logs)

    lines = []
    lines.append(f"=== 쿼리 실행 리포트 ===")
    lines.append(f"총 {failure['total']}건 | 성공 {failure['total'] - failure['failed']}건 | 실패 {failure['failed']}건 | 성공률 {failure['success_rate']}%")
    lines.append("")

    if ranking:
        lines.append("--- 테이블 사용 빈도 ---")
        for tbl, count in ranking[:10]:
            lines.append(f"  {tbl}: {count}회")
        lines.append("")

    if slow:
        lines.append("--- 느린 쿼리 패턴 ---")
        for p in slow:
            lines.append(f"  {p['tables']}: 평균 {p['avg_time_ms']}ms, 최대 {p['max_time_ms']}ms ({p['count']}회)")

    return "\n".join(lines)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/test_cli.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/querycreator/admin/ tests/test_cli.py
git commit -m "feat: admin CLI - dictionary validation and reporting"
git push
```

---

### Task 15: Documentation

**Files:**
- Create: `README.md`
- Create: `docs/setup-guide.md`
- Create: `docs/admin-guide.md`
- Create: `docs/onboarding-guide.md`
- Create: `docs/api-reference.md`
- Create: `docs/safety-rules.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# QueryCreator

Oracle DB 데이터 조회를 LLM이 자동으로 처리하는 Agent 앱.

시스템 담당자에게 반복적으로 들어오는 데이터 확인 문의를 LLM이 자동으로 처리합니다.
업무 사전과 DB 메타데이터를 기반으로 SQL을 자동 생성/실행하고 결과를 사용자에게 반환합니다.

## 아키텍처

```
사용자 → Agent → LLM ↔ QueryCreator (Python) → Oracle DB
```

LLM에게 3가지 도구를 제공합니다:
- **get_metadata**: 업무 키워드로 테이블/펑션 정보 조회
- **execute_query**: SQL 쿼리 검증 후 실행
- **call_function**: 스토어드 펑션 호출

## 빠른 시작

```bash
# 설치
pip install -e ".[dev]"

# 환경변수 설정
export QC_DB_HOST=your-oracle-host
export QC_DB_PORT=1521
export QC_DB_SERVICE=your-service
export QC_DB_USER=readonly_user
export QC_DB_PASSWORD=your-password
export QC_SCHEMAS=PROD

# 테스트 실행
pytest tests/ -v
```

## 문서

- [설치 가이드](docs/setup-guide.md)
- [시스템 관리자 운영 가이드](docs/admin-guide.md)
- [신규 스키마 적용 가이드](docs/onboarding-guide.md)
- [도구 API 명세](docs/api-reference.md)
- [안전규칙 명세](docs/safety-rules.md)
```

- [ ] **Step 2: Write `docs/setup-guide.md`**

```markdown
# 설치 및 초기 설정 가이드

## 1. Agent 앱 등록

Agent 플랫폼에서 Python 앱으로 등록합니다.
(등록 절차는 Agent 문서 참조)

## 2. 환경변수 설정

| 변수 | 설명 | 예시 |
|------|------|------|
| `QC_DB_HOST` | Oracle DB 호스트 | `192.168.1.100` |
| `QC_DB_PORT` | Oracle DB 포트 | `1521` |
| `QC_DB_SERVICE` | Oracle 서비스명 | `PRODDB` |
| `QC_DB_USER` | DB 사용자 (SELECT 전용) | `readonly_user` |
| `QC_DB_PASSWORD` | DB 비밀번호 | `****` |
| `QC_SCHEMAS` | 대상 스키마 (쉼표 구분) | `PROD,QUALITY` |

## 3. 업무 사전 작성

`data/dictionaries/` 디렉토리에 스키마별 YAML 파일을 작성합니다.

```bash
# 템플릿 복사
cp data/dictionaries/_template.yaml data/dictionaries/your_schema.yaml
```

템플릿을 참고하여 테이블, 펑션, 조인 관계를 등록합니다.
주요 테이블과 핵심 컬럼만 등록하면 됩니다 — 나머지는 Oracle 딕셔너리에서 자동 보완됩니다.

## 4. 메타데이터 수집

앱이 시작되면 자동으로 Oracle 딕셔너리에서 물리 메타데이터를 수집합니다.

## 5. 테스트

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
```

- [ ] **Step 3: Write `docs/admin-guide.md`**

```markdown
# 시스템 관리자 운영 가이드

## 일상 운영

### 로그 확인
쿼리 실행 로그는 JSONL 형식으로 저장됩니다.
`admin/cli.py`의 `generate_report()` 함수로 리포트를 생성할 수 있습니다.

### 느린 쿼리 대응
1. 리포트에서 느린 쿼리 패턴을 확인
2. 해당 테이블에 인덱스 힌트 추가: `data/knowledge/` YAML에 `table_hints` 등록
3. 필요시 샘플 쿼리 등록: 검증된 쿼리 패턴을 `sample_queries`에 추가

## 업무 사전 유지보수

### 테이블 추가 시
1. `data/dictionaries/<schema>.yaml`에 테이블 정보 추가
2. 업무명, 설명, 주요 컬럼, 별칭 등록
3. 관련 조인 관계 등록

### 스토어드 펑션 추가 시
1. `data/dictionaries/<schema>.yaml`의 `functions` 섹션에 추가
2. 파라미터, 용도, 업무명 등록

### 검증
```bash
python -c "from querycreator.admin.cli import validate_dictionary; print(validate_dictionary('data/dictionaries/your_schema.yaml'))"
```

## 운영자 힌트 등록

`data/knowledge/<schema>.yaml`에 추가:

- **인덱스 힌트**: 특정 테이블의 인덱스 활용 가이드
- **샘플 쿼리**: 자주 사용되는 검증된 쿼리 패턴
- **조인 규칙**: 테이블 간 조인 시 주의사항
- **금지 패턴**: CROSS JOIN 등 금지할 SQL 패턴

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 타임아웃 빈발 | 조건 없는 대용량 테이블 조회 | 해당 테이블에 인덱스 힌트 추가 |
| 잘못된 결과 | 업무 사전에 매핑 부족 | 업무 사전에 별칭/설명 보강 |
| 펑션을 안 쓰고 직접 쿼리 생성 | 펑션 메타데이터 부족 | 펑션의 용도(usage) 설명 보강 |
| 조인 잘못됨 | 조인 조건 미등록 | `joins` 섹션에 조인 조건 추가 |
```

- [ ] **Step 4: Write `docs/onboarding-guide.md`**

```markdown
# 신규 스키마 적용(수평전개) 가이드

## 체크리스트

- [ ] 1. SELECT 전용 DB 계정 확보 (대상 스키마 읽기 권한)
- [ ] 2. 환경변수 `QC_SCHEMAS`에 스키마 추가
- [ ] 3. 업무 사전 YAML 작성 (`data/dictionaries/<schema>.yaml`)
  - [ ] 주요 테이블 등록 (업무명, 설명, 핵심 컬럼)
  - [ ] 스토어드 펑션 등록 (있는 경우)
  - [ ] 테이블 간 조인 관계 등록
- [ ] 4. 업무 사전 검증 (`validate_dictionary`)
- [ ] 5. 운영자 힌트 등록 (선택, `data/knowledge/<schema>.yaml`)
- [ ] 6. 테스트 실행
- [ ] 7. Agent에 앱 배포
- [ ] 8. 파일럿 사용자 테스트 (5명 이내)
- [ ] 9. 로그 분석 후 업무 사전/힌트 보강

## 필요 인력
- 시스템 운영자 1명 (업무 사전 작성, DB 구조 파악)
- 개발자 1명 (설치, 테스트, 배포)

## 업무 사전 작성 팁
- 모든 테이블을 등록할 필요 없음 — 사용자 문의가 잦은 주요 테이블만 먼저 등록
- 별칭(aliases)을 충분히 등록할수록 검색 정확도 향상
- 스토어드 펑션이 있으면 반드시 등록 — LLM이 직접 쿼리보다 펑션을 우선 사용하도록 유도
```

- [ ] **Step 5: Write `docs/api-reference.md`**

```markdown
# 도구(Tool) API 명세

## get_metadata

| 항목 | 내용 |
|------|------|
| 이름 | `get_metadata` |
| 설명 | 업무 키워드 또는 테이블명으로 DB 메타데이터 조회 |

### 입력
```json
{
  "keyword": "주문"
}
```

### 출력 (텍스트)
테이블명, 업무명, 컬럼 목록, 인덱스 정보, 경고사항, 관련 펑션, 조인 관계를 포함한 텍스트.

---

## execute_query

| 항목 | 내용 |
|------|------|
| 이름 | `execute_query` |
| 설명 | SELECT 쿼리를 검증 후 실행, 결과 반환 |

### 입력
```json
{
  "sql": "SELECT order_no, cust_cd FROM tb_order WHERE order_no = 'A001'"
}
```

### 출력 (텍스트)
마크다운 테이블 형태의 결과 + 실행 시간.
검증 실패 시 에러 사유와 수정 가이드.

### 에러 코드
| 에러 | 설명 |
|------|------|
| SELECT만 허용 | DML/DDL 차단 |
| SELECT * 금지 | 컬럼 명시 필요 |
| WHERE 조건 필요 | 대용량 테이블 무조건 조회 차단 |
| 타임아웃 | 30초 초과 |

---

## call_function

| 항목 | 내용 |
|------|------|
| 이름 | `call_function` |
| 설명 | Oracle 스토어드 펑션 호출 |

### 입력
```json
{
  "function_name": "F_SUM_PROGRESS",
  "parameters": {"P_ORDER_NO": "A001"}
}
```

### 출력 (텍스트)
펑션 리턴값을 마크다운 테이블로 포맷팅.
```

- [ ] **Step 6: Write `docs/safety-rules.md`**

```markdown
# 안전규칙 명세

## 기본 규칙 (자동 적용)

| 규칙 | 목적 | 설정 |
|------|------|------|
| SELECT만 허용 | 데이터 변경 방지 | `allowed_statements: ["SELECT"]` |
| SELECT * 금지 | 불필요한 대량 데이터 전송 방지 | `block_select_star: true` |
| LIKE '%...' 차단 | 인덱스 미사용 풀스캔 방지 | `block_leading_wildcard: true` |
| 대용량 테이블 WHERE 필수 | 10만건 이상 테이블의 풀스캔 방지 | `large_table_threshold: 100000` |
| 실행 시간 제한 | DB 부하 방지 | `timeout_seconds: 30` |
| 결과 행수 제한 | 과도한 데이터 전송 방지 | `max_rows: 1000` |
| 복수 SQL문 차단 | SQL 인젝션 방지 | 자동 적용 |

## 커스터마이징

`src/querycreator/config/safety_rules.py`의 `SafetyRules` 클래스 기본값을 수정합니다.

```python
@dataclass
class SafetyRules:
    timeout_seconds: int = 30       # 타임아웃 변경
    max_rows: int = 1000            # 최대 행수 변경
    large_table_threshold: int = 100_000  # 대용량 기준 변경
```

## 운영자 추가 규칙

`data/knowledge/<schema>.yaml`의 `forbidden_patterns`에 금지 패턴을 추가합니다.

```yaml
forbidden_patterns:
  - "CROSS JOIN"
  - "CONNECT BY"
  - "DBMS_"
```
```

- [ ] **Step 7: Commit**

```bash
git add README.md docs/setup-guide.md docs/admin-guide.md docs/onboarding-guide.md docs/api-reference.md docs/safety-rules.md
git commit -m "docs: setup/admin/onboarding/API/safety-rules documentation"
git push
```

---

### Task 16: Final Verification

- [ ] **Step 1: Run full test suite with coverage**

Run: `cd /Users/pistosmin/develop/querycreator && python -m pytest tests/ -v --tb=short --cov=querycreator --cov-report=term-missing`
Expected: All tests pass, core modules >80% coverage

- [ ] **Step 2: Verify project structure**

Run: `cd /Users/pistosmin/develop/querycreator && find . -name "*.py" -not -path "./.git/*" | sort`
Expected: All planned files exist

- [ ] **Step 3: Verify git log**

Run: `cd /Users/pistosmin/develop/querycreator && git log --oneline`
Expected: Clean commit history per task

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
git push
```
