from unittest import mock
import json
from pathlib import Path

import pytest

import bw_bindings as bw

p = Path(__file__).parent.resolve()
with open(p / "sample_data.json") as fin:
    VAULT = json.load(fin)

ALL_PASS = {obj["name"]: obj["login"]["password"] for obj in VAULT["items"]}


@pytest.fixture(autouse=True)
def mock_bw(monkeypatch):

    m_popen = mock.Mock(spec=bw.subprocess.Popen)
    m_popen.return_value.returncode = 0

    def bw_emu_wrapper(*args, **_):
        return bw_emulator(*args, mock_obj=m_popen)

    m_popen.return_value.communicate.side_effect = bw_emu_wrapper
    monkeypatch.setattr(bw.subprocess, "Popen", m_popen)
    return m_popen


@pytest.fixture
def mock_comm(mock_bw):
    return mock_bw.return_value.communicate


def bw_emulator(*args, mock_obj=None, **_):
    if mock_obj is None:
        return b"", b""
    command = mock_obj.call_args.args[0]
    assert command[0] == "bw"
    args = command[1:]
    if args[0] == "get":
        assert 'session_key' in command
        obj, key = args[1:3]
        if obj == "password":
            try:
                return ALL_PASS[key].encode("utf8"), b""
            except KeyError:
                pass
        if obj == "item":
            canidates = [item for item in VAULT["items"] if item["name"] == key]
            if len(canidates) == 1:
                return json.dumps(canidates[0]), b""
    if args[0] == "login":
        return b"session_key", b""

    mock_obj.return_value.returncode = 1
    return b"", b"error"


def test_get(mock_comm):
    mock_comm.return_value = (
        VAULT["items"][-2]["login"]["password"].encode("utf8"),
        b"",
    )
    session = bw.Session("user@email.com")
    session.login()
    assert session.get("password", "xbox.com") == "aijee9Ee"


def test_get_err_with_no_login():
    session = bw.Session()
    with pytest.raises(bw.BitwardenNotLoggedInError):
        session.get("password", "xbox.com")


def test_get_not_found():
    session = bw.Session("user")
    session.login()
    with pytest.raises(bw.BitwardenError):
        session.get("password", "does_not_exsist")


def test_get_item():
    session = bw.Session("user")
    session.login()
    item = session.get_item("xbox.com")
    assert item["name"] == "xbox.com"
    assert item["login"]["username"] == "user@email.com"
