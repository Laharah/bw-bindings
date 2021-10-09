# pyright: reportUnusedFunction=false

from unittest import mock

import pytest

import bw_bindings as bw
import os


@pytest.fixture()
def mock_popen(monkeypatch):
    m_popen = mock.Mock(spec=bw.subprocess.Popen)
    m_popen.return_value.communicate.return_value = (b"session_key", b"")
    m_popen.return_value.returncode = 0
    monkeypatch.setattr(bw.subprocess, "Popen", m_popen)
    return m_popen


def test_login(mock_popen):

    session = bw.Session()
    session.login("username")

    assert mock_popen.call_args is not None
    assert "username" in mock_popen.call_args.args[0]

    assert session.key == b"session_key"


def test_no_bitwarden(mock_popen):
    def fnf(*_, **kwargs):
        del kwargs
        raise FileNotFoundError("No such file or directory bw")

    mock_popen.side_effect = fnf

    session = bw.Session()
    with pytest.raises(bw.BitwardenError):
        session.login("username")


def test_no_api_key(mock_popen):
    mock_popen().communicate.return_value = (
        b"",
        b"Master password: [hidden]\x1b[27D\x1b[27C\n? Additional authentication required.\nAPI key client_secret: \x1b[23D\x1b[23C",
    )
    session = bw.Session()
    with pytest.raises(bw.BitwardenError):
        session.login("username")


def test_wrong_password(mock_popen):
    mock_popen().communicate.return_value = (
        b"",
        b"blahblah Username or password is incorrect. Try again.",
    )
    mock_popen().returncode = 1
    session = bw.Session()
    with pytest.raises(bw.BitwardenPasswordError):
        session.login("username")


def test_other_error(mock_popen):
    mock_popen().communicate.return_value = (
        b"",
        b"Some Other Unexpected Error.",
    )
    mock_popen().returncode = 1
    session = bw.Session()
    with pytest.raises(bw.BitwardenError):
        session.login("username")


def test_optional_username(mock_popen):
    session = bw.Session("my_username")
    session.login()
    assert session.key == b"session_key"
    assert "my_username" in mock_popen.call_args.args[0]

def test_no_username_error(mock_popen):
    session = bw.Session()
    with pytest.raises(bw.BitwardenError):
        session.login()
    assert not mock_popen.called

