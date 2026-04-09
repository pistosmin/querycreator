"""DB connection interface and Oracle implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DBConnection(ABC):
    """Abstract interface for database connections."""

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
            cursor.calltimeout = timeout_seconds * 1000
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
