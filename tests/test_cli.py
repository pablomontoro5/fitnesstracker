from app.cli import main


def test_create_invite_cli_prints_a_code(capsys):
    assert main(["create-invite", "--days", "3"]) == 0

    output = capsys.readouterr().out

    assert "Código de invitación:" in output
    assert "Caduca (UTC):" in output
