"""Consultas de introspección del esquema de PostgreSQL para los tests."""

_ON_DELETE = {"c": "CASCADE", "n": "SET NULL", "a": "NO ACTION", "r": "RESTRICT"}


def table_names(connection) -> list[str]:
    return [
        row["table_name"]
        for row in connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
    ]


def table_columns(connection, table: str) -> set[str]:
    return {
        row["column_name"]
        for row in connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = ?",
            (table,),
        )
    }


def foreign_keys(connection, table: str) -> list[dict]:
    """Claves foráneas de `table`: columna, tabla destino y acción ON DELETE."""
    return [
        {
            "from": row["from_column"],
            "table": row["to_table"],
            "on_delete": _ON_DELETE[row["on_delete"]],
        }
        for row in connection.execute(
            """
            SELECT a.attname AS from_column,
                   target.relname AS to_table,
                   c.confdeltype AS on_delete
            FROM pg_constraint AS c
            JOIN pg_class AS source ON source.oid = c.conrelid
            JOIN pg_class AS target ON target.oid = c.confrelid
            JOIN pg_attribute AS a
                ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f'
              AND source.relname = ?
              AND source.relnamespace = 'public'::regnamespace
            """,
            (table,),
        )
    ]
