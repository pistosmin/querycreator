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
    col_names = [c["column_name"] for c in columns["TB_ORDER"]]
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
