"""Oracle dictionary metadata collector."""
from __future__ import annotations
from typing import Any
from querycreator.db.connection import DBConnection


class MetadataCollector:
    """Collects physical metadata from Oracle dictionary views."""

    def __init__(self, db: DBConnection, schema: str) -> None:
        self._db = db
        self._schema = schema.upper()

    def collect_tables(self) -> dict[str, dict[str, Any]]:
        rows = self._db.execute(
            "SELECT table_name, num_rows FROM all_tables WHERE owner = :owner",
            {"owner": self._schema}, max_rows=5000)
        return {row["TABLE_NAME"]: {"num_rows": row.get("NUM_ROWS", 0) or 0} for row in rows}

    def collect_columns(self) -> dict[str, list[dict[str, Any]]]:
        rows = self._db.execute(
            "SELECT table_name, column_name, data_type, data_length, nullable, column_id "
            "FROM all_tab_columns WHERE owner = :owner ORDER BY table_name, column_id",
            {"owner": self._schema}, max_rows=50000)
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            tbl = row["TABLE_NAME"]
            if tbl not in result:
                result[tbl] = []
            result[tbl].append({
                "column_name": row["COLUMN_NAME"], "data_type": row["DATA_TYPE"],
                "data_length": row.get("DATA_LENGTH"), "nullable": row.get("NULLABLE", "Y") == "Y",
                "position": row.get("COLUMN_ID"),
            })
        return result

    def collect_indexes(self) -> dict[str, list[dict[str, Any]]]:
        rows = self._db.execute(
            "SELECT table_name, index_name, column_name, column_position "
            "FROM all_ind_columns WHERE table_owner = :owner ORDER BY table_name, index_name, column_position",
            {"owner": self._schema}, max_rows=50000)
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            tbl = row["TABLE_NAME"]
            if tbl not in result:
                result[tbl] = []
            result[tbl].append({"index_name": row["INDEX_NAME"], "column_name": row["COLUMN_NAME"], "position": row.get("COLUMN_POSITION")})
        return result

    def collect_constraints(self) -> dict[str, list[dict[str, Any]]]:
        rows = self._db.execute(
            "SELECT table_name, constraint_name, constraint_type, column_name "
            "FROM all_constraints NATURAL JOIN all_cons_columns "
            "WHERE owner = :owner AND constraint_type IN ('P', 'R')",
            {"owner": self._schema}, max_rows=50000)
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            tbl = row["TABLE_NAME"]
            if tbl not in result:
                result[tbl] = []
            result[tbl].append({"constraint_name": row["CONSTRAINT_NAME"], "type": "PK" if row["CONSTRAINT_TYPE"] == "P" else "FK", "column_name": row.get("COLUMN_NAME")})
        return result

    def collect_comments(self) -> dict[str, dict[str, str]]:
        rows = self._db.execute(
            "SELECT table_name, column_name, comments "
            "FROM all_col_comments WHERE owner = :owner AND comments IS NOT NULL",
            {"owner": self._schema}, max_rows=50000)
        result: dict[str, dict[str, str]] = {}
        for row in rows:
            tbl = row["TABLE_NAME"]
            if tbl not in result:
                result[tbl] = {}
            result[tbl][row["COLUMN_NAME"]] = row["COMMENTS"]
        return result

    def collect_all(self) -> dict[str, dict[str, Any]]:
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
