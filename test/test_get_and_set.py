from unittest import mock
import json
from pathlib import Path

import pytest

import bw_bindings as bw

p = Path(__file__).parent.resolve()
with open(p / "sample_data.json") as fin:
    VAULT = json.load(fin)


@pytest.fixture(autouse=True)
def mock_bw(monkeypatch):

    m_popen = mock.Mock(spec=bw.subprocess.Popen)
    m_popen.return_value.returncode = 0
    m_popen.return_value.communicate.return_value = (b"", b"")
    monkeypatch.setattr(bw.subprocess, "Popen", m_popen)
    return m_popen


@pytest.fixture
def mock_comm(mock_bw):
    return mock_bw.return_value.communicate


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
