from app.database import Database


def test_database_initialization_creates_expected_tables(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    database.initialize()

    with database.connect() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {row["name"] for row in rows}
    assert {"documents", "client_requests", "proposals", "audit_events"} <= table_names
    assert database.healthcheck() is True

