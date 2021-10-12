# pyright: reportUnusedFunction=false

from unittest import mock

import pytest

import bw_bindings as bw


@pytest.fixture(autouse=True)
def mock_bw(monkeypatch):
    m_popen = mock.Mock(spec=bw.subprocess.Popen)
    m_popen.return_value.communicate.return_value = (b"session_key", b"")
    m_popen.return_value.returncode = 0
    monkeypatch.setattr(bw.subprocess, "Popen", m_popen)
    return m_popen


def test_login(mock_bw):

    session = bw.Session("username")
    session.login()

    assert mock_bw.call_args is not None
    assert "username" in mock_bw.call_args.args[0]

    assert session.key == "session_key"


def test_no_bitwarden(mock_bw):
    def fnf(*_, **kwargs):
        del kwargs
        raise FileNotFoundError("No such file or directory bw")

    mock_bw.side_effect = fnf

    session = bw.Session("user")
    with pytest.raises(bw.BitwardenError):
        session.login("password")


def test_no_api_key(mock_bw):
    mock_bw().communicate.return_value = (
        b"",
        b"Master password: [hidden]\x1b[27D\x1b[27C\n? Additional authentication required.\nAPI key client_secret: \x1b[23D\x1b[23C",
    )
    session = bw.Session("user")
    with pytest.raises(bw.BitwardenError):
        session.login("username")


def test_wrong_password(mock_bw):
    mock_bw().communicate.return_value = (
        b"",
        b"blahblah Username or password is incorrect. Try again.",
    )
    mock_bw().returncode = 1
    session = bw.Session("user")
    with pytest.raises(bw.BitwardenPasswordError):
        session.login("username")


def test_other_login_error(mock_bw):
    mock_bw().communicate.return_value = (
        b"",
        b"Some Other Unexpected Error.",
    )
    mock_bw().returncode = 1
    session = bw.Session("user")
    with pytest.raises(bw.BitwardenError):
        session.login("username")


def test_optional_username(mock_bw):
    session = bw.Session("my_username")
    session.login()
    assert session.key == "session_key"
    assert "my_username" in mock_bw.call_args.args[0]


def test_optional_passwd(mock_pynentry):
    session = bw.Session("user")
    session.login(passwd="my_password")
    assert session.key == "session_key"
    assert not mock_pynentry.called


def test_optional_constructor_password(mock_pynentry):
    session = bw.Session("user@email.com", passwd="abc123")
    session.login()
    assert session.key == "session_key"
    assert not mock_pynentry.called


def test_returns_session_key():
    session = bw.Session("user")
    assert session.login("passwd") == "session_key"


def test_logout(mock_bw):
    session = bw.Session("user")
    session.login("mypass")
    assert session.key == "session_key"
    session.logout()
    assert session.key is None
    assert "logout" in mock_bw.call_args.args[0]


def test_other_error(mock_bw):
    session = bw.Session("user")
    session.login("pass")
    mock_bw.return_value.returncode = 1
    with pytest.raises(bw.BitwardenError):
        session.logout()

def test_session_context(mock_bw):
    with bw.Session("user", "pass") as session:
        assert session.key == "session_key"
    assert mock_bw.call_count == 2
    calls_args = [call.args[0] for call in mock_bw.call_args_list]
    assert "login" in calls_args[0]
    assert "logout" in calls_args[1]
