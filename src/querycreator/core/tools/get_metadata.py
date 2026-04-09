"""GetMetadataTool — search metadata catalog and return formatted text."""
from __future__ import annotations
from typing import Any
from querycreator.core.metadata.catalog import MetadataCatalog


class GetMetadataTool:
    def __init__(self, catalog: MetadataCatalog) -> None:
        self._catalog = catalog

    def run(self, keyword: str) -> str:
        results = self._catalog.search(keyword)
        tables = results.get("tables", [])
        functions = results.get("functions", [])
        joins = results.get("joins", [])

        if not tables and not functions and not joins:
            return f"'{keyword}'에 대한 메타데이터를 찾을 수 없습니다."

        lines: list[str] = []

        if tables:
            lines.append("## 테이블")
            for tbl in tables:
                lines.append(f"\n### {tbl['table_name']} ({tbl.get('business_name', '')})")
                if tbl.get("description"):
                    lines.append(f"설명: {tbl['description']}")
                lines.append(f"행 수: {tbl.get('num_rows', 0):,}건")
                warnings = tbl.get("warnings", [])
                if warnings:
                    lines.append("주의:")
                    for w in warnings:
                        lines.append(f"  - {w}")
                indexed_cols = tbl.get("indexed_columns", [])
                if indexed_cols:
                    lines.append(f"인덱스 컬럼: {', '.join(indexed_cols)}")
                key_columns = tbl.get("key_columns", {})
                if key_columns:
                    kc_parts = [f"{col}({desc})" for col, desc in key_columns.items()]
                    lines.append(f"키 컬럼: {', '.join(kc_parts)}")
                columns = tbl.get("columns", [])
                comments = tbl.get("comments", {})
                if columns:
                    lines.append("컬럼:")
                    for col in columns:
                        col_name = col.get("column_name", col.get("COLUMN_NAME", ""))
                        comment = comments.get(col_name, "")
                        data_type = col.get("data_type", col.get("DATA_TYPE", ""))
                        nullable = col.get("nullable", col.get("NULLABLE", "Y"))
                        null_str = "" if nullable == "Y" else " NOT NULL"
                        comment_str = f" — {comment}" if comment else ""
                        lines.append(f"  - {col_name} ({data_type}{null_str}){comment_str}")

        if functions:
            lines.append("\n## 함수")
            for func in functions:
                lines.append(f"\n### {func['function_name']} ({func.get('business_name', '')})")
                if func.get("description"):
                    lines.append(f"설명: {func['description']}")
                params = func.get("parameters", {})
                if params:
                    param_parts = [f"{p}({desc})" for p, desc in params.items()]
                    lines.append(f"파라미터: {', '.join(param_parts)}")
                if func.get("usage"):
                    lines.append(f"사용 예시: {func['usage']}")

        if joins:
            lines.append("\n## 조인 정보")
            for join in joins:
                tables_str = " ↔ ".join(join.get("tables", []))
                lines.append(f"\n- {tables_str}")
                if join.get("condition"):
                    lines.append(f"  조건: {join['condition']}")
                if join.get("description"):
                    lines.append(f"  설명: {join['description']}")

        return "\n".join(lines)

    @staticmethod
    def tool_schema() -> dict[str, Any]:
        return {
            "name": "get_metadata",
            "description": (
                "비즈니스 용어나 테이블명으로 메타데이터를 검색합니다. "
                "테이블 구조, 컬럼 정보, 조인 관계, 함수 정보를 반환합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색할 키워드 (예: '주문', 'TB_ORDER', '생산 진행')",
                    }
                },
                "required": ["keyword"],
            },
        }
