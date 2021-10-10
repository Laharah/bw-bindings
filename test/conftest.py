from unittest import mock

import pytest

import bw_bindings as bw


@pytest.fixture(autouse=True)
def mock_pynentry(monkeypatch):
    m_pynentry = mock.MagicMock()
    m_pynentry.get_pin.return_value = "abc123"
    # make sure that the mock's context manager get_pin function also always returns abc123
    m_pynentry.return_value.__enter__.return_value.get_pin.return_value = "abc123"

    monkeypatch.setattr(bw, "PynEntry", m_pynentry)
    return m_pynentry
