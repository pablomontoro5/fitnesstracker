import sqlite3

from app.cli import main


SQLITE_MAGIC = b"SQLite format 3\x00"


def test_backup_cli_writes_a_verified_portable_file(tmp_path, capsys):
    assert main(["backup", "--output-dir", str(tmp_path)]) == 0

    printed_path = capsys.readouterr().out.strip()
    backups = list(tmp_path.glob("fitness_tracker_backup_*.db"))

    assert [str(path) for path in backups] == [printed_path]

    content = backups[0].read_bytes()
    # Bytes 18 y 19 de la cabecera: 1 = journal_mode DELETE (no WAL).
    assert content[:16] == SQLITE_MAGIC
    assert content[18] == 1 and content[19] == 1

    connection = sqlite3.connect(backups[0])
    try:
        assert connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0] == "ok"
    finally:
        connection.close()


def test_backup_cli_stdout_streams_the_database_without_leaving_files(
    tmp_path, monkeypatch, capsysbinary
):
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))

    assert main(["backup", "--stdout"]) == 0

    output = capsysbinary.readouterr().out

    assert output[:16] == SQLITE_MAGIC
    assert output[18] == 1 and output[19] == 1
    assert list(tmp_path.iterdir()) == []


def test_backup_cli_fails_when_the_database_is_missing(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr("app.cli.DATABASE_PATH", tmp_path / "missing.db")

    assert main(["backup", "--output-dir", str(tmp_path)]) == 1
    assert "No existe la base de datos" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_create_invite_cli_prints_a_code(capsys):
    assert main(["create-invite", "--days", "3"]) == 0

    output = capsys.readouterr().out

    assert "Código de invitación:" in output
    assert "Caduca (UTC):" in output
