# pyright: reportUnusedFunction=false

import bw_bindings as bw


def test_get_password():
    assert bw.get_password() == "abc123"
