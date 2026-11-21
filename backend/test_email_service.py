"""The email service over real SMTP, against a tiny fake server on this machine. Nothing leaves the computer."""
import socketserver
import threading

import pytest

import config
from services import email_service


class _FakeSMTP(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self):
        self.messages, self.recipients = [], []
        super().__init__(("127.0.0.1", 0), _FakeSMTPSession)


class _FakeSMTPSession(socketserver.StreamRequestHandler):
    """Just enough of SMTP. It never offers STARTTLS."""

    def handle(self):
        server, body, receiving = self.server, [], False
        self.wfile.write(b"220 fake\r\n")
        for raw in self.rfile:
            if receiving:
                if raw in (b".\r\n", b".\n"):
                    receiving = False
                    server.messages.append(b"".join(body).decode("utf-8", "replace"))
                    self.wfile.write(b"250 queued\r\n")
                else:
                    body.append(raw)
                continue
            line = raw.decode("utf-8", "replace").strip()
            if line.upper().startswith("RCPT TO"):
                server.recipients.append(line.split(":", 1)[1])
            if line.upper() == "DATA":
                receiving = True
                self.wfile.write(b"354 go\r\n")
            elif line.upper() == "QUIT":
                self.wfile.write(b"221 bye\r\n")
                return
            else:
                self.wfile.write(b"250 ok\r\n")


@pytest.fixture()
def fake_smtp(monkeypatch):
    server = _FakeSMTP()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(config, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(config, "SMTP_PORT", server.server_address[1])
    monkeypatch.setattr(config, "SMTP_USERNAME", "")
    yield server
    server.shutdown()
    server.server_close()


def test_smtp_delivers_one_message_to_one_recipient(fake_smtp, monkeypatch):
    monkeypatch.setattr(config, "SMTP_SECURITY", "none")
    assert email_service.send_email("teacher@example.test", "Subject", "Link: https://x.test/reset-password#token=abc") is True
    assert fake_smtp.recipients == ["<teacher@example.test>"]
    assert len(fake_smtp.messages) == 1 and "reset-password#token=" in fake_smtp.messages[0].replace("=3D", "=")


def test_starttls_that_the_server_does_not_offer_never_falls_back_to_plaintext(fake_smtp, monkeypatch):
    monkeypatch.setattr(config, "SMTP_SECURITY", "starttls")
    assert email_service.send_email("teacher@example.test", "Subject", "SECRET-LINK-BODY") is False
    assert fake_smtp.messages == []


def test_a_mail_server_that_is_down_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(config, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(config, "SMTP_PORT", 1)  # nothing listens here
    monkeypatch.setattr(config, "SMTP_SECURITY", "none")
    assert email_service.send_email("teacher@example.test", "Subject", "Body") is False


def test_a_gmail_app_password_pasted_with_its_display_spaces_still_works():
    shown = "abcd efgh ijkl mnop"  # how Google displays it
    assert config.normalise_smtp_password("smtp.gmail.com", shown) == "abcdefghijklmnop"
    assert config.normalise_smtp_password("SMTP.GMAIL.COM", " abcd efgh\tijkl\nmnop ") == "abcdefghijklmnop"
    # Other mail servers keep the password exactly as given.
    assert config.normalise_smtp_password("smtp.hostinger.com", "pass word 1") == "pass word 1"
    assert config.normalise_smtp_password("smtp.gmail.com", "") == ""
