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
