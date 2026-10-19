import smtplib

import pytest
from fastapi.testclient import TestClient

from app import mailer
from app.cli import main as cli_main
from app.db import get_connection
from app.main import FRONTEND_DIR, app
from tests.conftest import register_and_login


client = TestClient(app)

SMTP_ENV = {
    mailer.SMTP_HOST_ENV: "smtp.example.com",
    mailer.MAIL_FROM_ENV: "Fitness Tracker <no-reply@example.com>",
}


@pytest.fixture()
def mail_on(monkeypatch):
    for name, value in SMTP_ENV.items():
        monkeypatch.setenv(name, value)


@pytest.fixture()
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.password_resets.send_email",
        lambda to, subject, body: sent.append((to, subject, body)),
    )
    return sent


@pytest.fixture()
def no_mail(monkeypatch):
    for name in (
        mailer.SMTP_HOST_ENV,
        mailer.SMTP_PORT_ENV,
        mailer.SMTP_USER_ENV,
        mailer.SMTP_PASSWORD_ENV,
        mailer.MAIL_FROM_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


def forgot(email: str):
    return client.post("/auth/forgot-password", json={"email": email})


def extract_code(body: str) -> str:
    return next(
        line.strip() for line in body.splitlines() if line.startswith("    ")
    )


# --- Endpoint --------------------------------------------------------------


def test_forgot_password_is_unavailable_without_smtp(no_mail):
    register_and_login(client, email="a@example.com")

    response = forgot("a@example.com")

    assert response.status_code == 503
    assert "administrador" in response.json()["detail"]


def test_forgot_password_emails_a_working_code(mail_on, outbox):
    register_and_login(client, email="a@example.com")

    response = forgot("  A@Example.com ")

    assert response.status_code == 202
    assert len(outbox) == 1
    to, subject, body = outbox[0]
    assert to == "a@example.com"
    assert "recuperar" in subject.lower()

    reset = client.post(
        "/auth/reset-password",
        json={
            "email": "a@example.com",
            "code": extract_code(body),
            "new_password": "otra-contrasena-larga-456",
        },
    )
    assert reset.status_code == 204

    login = client.post(
        "/auth/login",
        json={"email": "a@example.com", "password": "otra-contrasena-larga-456"},
    )
    assert login.status_code == 200


def test_forgot_password_answers_the_same_for_unknown_accounts(mail_on, outbox):
    register_and_login(client, email="a@example.com")

    known = forgot("a@example.com")
    unknown = forgot("nadie@example.com")

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [to for to, _, _ in outbox] == ["a@example.com"]


def test_forgot_password_does_not_email_inactive_accounts(mail_on, outbox):
    register_and_login(client, email="a@example.com")

    with get_connection() as connection:
        connection.execute("UPDATE users SET is_active = 0 WHERE email = ?", ("a@example.com",))

    assert forgot("a@example.com").status_code == 202
    assert outbox == []


def test_a_new_request_invalidates_the_previous_code(mail_on, outbox):
    register_and_login(client, email="a@example.com")

    forgot("a@example.com")
    forgot("a@example.com")
    first, second = (extract_code(body) for _, _, body in outbox)

    def use(code):
        return client.post(
            "/auth/reset-password",
            json={
                "email": "a@example.com",
                "code": code,
                "new_password": "otra-contrasena-larga-456",
            },
        ).status_code

    assert use(first) == 400
    assert use(second) == 204


def test_requests_per_email_are_capped_silently(mail_on, outbox):
    register_and_login(client, email="a@example.com")

    for _ in range(5):
        assert forgot("a@example.com").status_code == 202

    assert len(outbox) == 3


def test_requests_per_ip_are_capped_with_429(mail_on, outbox):
    for index in range(5):
        assert forgot(f"u{index}@example.com").status_code == 202

    response = forgot("otro@example.com")

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_a_failing_mail_server_does_not_change_the_response(mail_on, monkeypatch):
    register_and_login(client, email="a@example.com")

    def boom(*args, **kwargs):
        raise mailer.MailError("No se pudo enviar el correo (OSError).")

    monkeypatch.setattr("app.password_resets.send_email", boom)

    assert forgot("a@example.com").status_code == 202


def test_the_code_is_never_logged(mail_on, outbox, caplog):
    register_and_login(client, email="a@example.com")

    with caplog.at_level("DEBUG"):
        forgot("a@example.com")

    code = extract_code(outbox[0][2])
    assert code not in caplog.text


# --- Mailer ----------------------------------------------------------------


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.context = host, port, context
        self.calls = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        self.calls.append(("send", message))


@pytest.fixture()
def fake_smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


def test_mailer_uses_starttls_on_587_and_logs_in(mail_on, fake_smtp, monkeypatch):
    monkeypatch.setenv(mailer.SMTP_USER_ENV, "resend")
    monkeypatch.setenv(mailer.SMTP_PASSWORD_ENV, "clave")

    mailer.send_email("a@example.com", "Asunto", "Cuerpo")

    server = fake_smtp.instances[0]
    assert server.port == 587
    assert server.calls[0] == "starttls"
    assert server.calls[1] == ("login", "resend", "clave")
    message = server.calls[2][1]
    assert message["To"] == "a@example.com"
    assert message["From"] == SMTP_ENV[mailer.MAIL_FROM_ENV]


def test_mailer_uses_implicit_tls_on_465(mail_on, fake_smtp, monkeypatch):
    monkeypatch.setenv(mailer.SMTP_PORT_ENV, "465")

    mailer.send_email("a@example.com", "Asunto", "Cuerpo")

    assert "starttls" not in fake_smtp.instances[0].calls


def test_mailer_refuses_header_injection(mail_on, fake_smtp):
    with pytest.raises(mailer.MailError):
        mailer.send_email("a@example.com\nBcc: x@example.com", "A", "B")

    assert fake_smtp.instances == []


def test_mailer_errors_do_not_leak_server_details(mail_on, monkeypatch):
    class Broken(FakeSMTP):
        def send_message(self, message):
            raise smtplib.SMTPAuthenticationError(535, b"clave-secreta rechazada")

    monkeypatch.setattr(smtplib, "SMTP", Broken)

    with pytest.raises(mailer.MailError) as error:
        mailer.send_email("a@example.com", "A", "B")

    assert "clave-secreta" not in str(error.value)
    assert "SMTPAuthenticationError" in str(error.value)


def test_mailer_needs_host_and_sender(no_mail, monkeypatch):
    assert not mailer.mail_is_configured()

    monkeypatch.setenv(mailer.SMTP_HOST_ENV, "smtp.example.com")
    assert not mailer.mail_is_configured()

    monkeypatch.setenv(mailer.MAIL_FROM_ENV, "no-reply@example.com")
    assert mailer.mail_is_configured()

    with pytest.raises(mailer.MailError):
        monkeypatch.delenv(mailer.SMTP_HOST_ENV)
        mailer.send_email("a@example.com", "A", "B")


# --- CLI y frontend --------------------------------------------------------


def test_cli_test_email_reports_missing_configuration(no_mail, capsys):
    assert cli_main(["test-email", "--to", "a@example.com"]) == 1
    assert "FITNESS_TRACKER_SMTP_HOST" in capsys.readouterr().err


def test_cli_test_email_sends_when_configured(mail_on, fake_smtp, capsys):
    assert cli_main(["test-email", "--to", "a@example.com"]) == 0
    assert "enviado" in capsys.readouterr().out


def test_login_page_offers_to_email_the_code():
    html = (FRONTEND_DIR / "login" / "index.html").read_text(encoding="utf-8")
    script = (FRONTEND_DIR / "login" / "login.js").read_text(encoding="utf-8")

    assert 'id="send-reset-code-button"' in html
    assert "/auth/forgot-password" in script
