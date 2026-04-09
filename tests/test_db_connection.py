"""Tests for DB connection abstraction."""

from querycreator.db.connection import DBConnection
from querycreator.db.mock_connection import MockConnection


def test_mock_connection_execute_returns_rows(mock_db: MockConnection):
    rows = mock_db.execute("SELECT table_name FROM all_tables WHERE owner = :owner", {"owner": "TEST"})
    assert isinstance(rows, list)
    assert len(rows) > 0


def test_mock_connection_execute_with_timeout(mock_db: MockConnection):
    rows = mock_db.execute("SELECT 1 FROM dual", timeout_seconds=30)
    assert rows is not None


def test_mock_connection_respects_max_rows(mock_db: MockConnection):
    rows = mock_db.execute("SELECT * FROM large_table", max_rows=5)
    assert len(rows) <= 5


def test_connection_is_abstract():
    try:
        DBConnection()
        assert False, "Should raise TypeError"
    except TypeError:
        pass
