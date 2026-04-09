"""Admin CLI — dictionary validation and query log reporting."""
from __future__ import annotations

from typing import Any

import yaml

from querycreator.logging.analyzer import QueryAnalyzer


def validate_dictionary(yaml_path: str) -> list[str]:
    """Validate a business dictionary YAML file. Returns list of errors."""
    errors: list[str] = []

    # Check file is readable
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return [f"파일을 찾을 수 없습니다: {yaml_path}"]
    except Exception as e:
        return [f"파일 읽기 오류: {e}"]

    if not data or not isinstance(data, dict):
        return ["YAML 파일이 비어 있거나 형식이 올바르지 않습니다."]

    # Check schema field exists
    if "schema" not in data:
        errors.append("필수 필드 누락: 'schema' 필드가 없습니다.")

    # Validate tables
    tables = data.get("tables", {})
    if isinstance(tables, dict):
        for tbl_name, tbl_info in tables.items():
            if not isinstance(tbl_info, dict):
                errors.append(f"테이블 '{tbl_name}': 정보가 딕셔너리 형식이 아닙니다.")
                continue
            if "business_name" not in tbl_info:
                errors.append(f"테이블 '{tbl_name}': 필수 필드 'business_name'이 없습니다.")
            if "description" not in tbl_info:
                errors.append(f"테이블 '{tbl_name}': 필수 필드 'description'이 없습니다.")

    # Validate functions
    functions = data.get("functions", {})
    if isinstance(functions, dict):
        for func_name, func_info in functions.items():
            if not isinstance(func_info, dict):
                errors.append(f"함수 '{func_name}': 정보가 딕셔너리 형식이 아닙니다.")
                continue
            if "business_name" not in func_info:
                errors.append(f"함수 '{func_name}': 필수 필드 'business_name'이 없습니다.")
            if "parameters" not in func_info:
                errors.append(f"함수 '{func_name}': 필수 필드 'parameters'가 없습니다.")

    return errors


def generate_report(logs: list[dict[str, Any]]) -> str:
    """Generate text report from query logs."""
    analyzer = QueryAnalyzer()

    failure_info = analyzer.failure_report(logs)
    table_ranking = analyzer.table_usage_ranking(logs)
    slow_patterns = analyzer.find_slow_patterns(logs)

    total = failure_info["total"]
    failed = failure_info["failed"]
    success_rate = failure_info["success_rate"]

    lines: list[str] = []
    lines.append("# 쿼리 실행 보고서")
    lines.append("")

    lines.append("## 요약")
    lines.append(f"- 전체 쿼리: {total}건")
    lines.append(f"- 실패 쿼리: {failed}건")
    lines.append(f"- 성공률: {success_rate}%")
    lines.append("")

    if table_ranking:
        lines.append("## 테이블 사용 순위")
        for rank, (tbl, count) in enumerate(table_ranking, start=1):
            lines.append(f"  {rank}. {tbl}: {count}회")
        lines.append("")

    if slow_patterns:
        lines.append("## 느린 쿼리 패턴")
        for pattern in slow_patterns:
            lines.append(f"  - 테이블: {pattern['tables']}")
            lines.append(f"    평균 실행 시간: {pattern['avg_time_ms']}ms")
            lines.append(f"    최대 실행 시간: {pattern['max_time_ms']}ms")
            lines.append(f"    쿼리 수: {pattern['count']}건")
        lines.append("")

    if failed > 0:
        lines.append("## 실패 쿼리 목록")
        for log in logs:
            if not log.get("success", True):
                sql = log.get("sql", "(SQL 없음)")
                error = log.get("error", "알 수 없는 오류")
                lines.append(f"  - SQL: {sql}")
                lines.append(f"    오류: {error}")
        lines.append("")

    return "\n".join(lines)
