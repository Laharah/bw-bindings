import os
import subprocess
from typing import Union, Optional
from contextlib import ContextDecorator

from pynentry import PynEntry

# generic bitwarden bindings error
class BitwardenError(Exception):
    pass


class BitwardenPasswordError(BitwardenError):
    pass


class BitwardenNotLoggedInError(BitwardenError):
    pass


# decorator for class methods to ensure that session is logged in
def _logged_in(method):
    def wrapper(self, *args, **kwargs):
        if self.key is None:
            raise BitwardenNotLoggedInError(
                (
                    f"Bitwarden cannot execute {method.__name__} "
                    "because session is not currently logged in."
                )
            )
        return method(self, *args, **kwargs)

    return wrapper


# class representing a single bitwarden session
class Session:
    def __init__(self, username: Optional[str] = None):
        self.key = None
        self.username = username

    def login(self, username: Optional[str] = None, passwd: Optional[str] = None):
        if username is None:
            username = self.username
        if username is None:
            raise BitwardenError("No username defined for login operation.")

        if passwd is None:
            with PynEntry() as p:
                p.description = "Enter your Bitwarden Password"
                p.prompt = ">"
                passwd = p.get_pin() + "\n"

        try:
            bw = subprocess.Popen(
                f"bw login {username} --raw".split(), stdin=-1, stdout=-1, stderr=-1
            )
        except FileNotFoundError as e:
            raise BitwardenError("Bitwarden CLI `bw` could not be found.") from e

        passwd: str
        session_key, err = bw.communicate(passwd.encode("utf8"), timeout=40)

        if b"API key client_secret" in err:
            raise BitwardenError(
                (
                    "CLI must be authenticated with API key: "
                    "https://bitwarden.com/help/article/cli-auth-challenges/"
                )
            )
        if b"Username or password is incorrect" in err:
            raise BitwardenPasswordError(
                'Password for "{username}" is incorrect. Try Again.'
            )
        if not session_key or bw.returncode != 0:
            print(f"{session_key=} {err=}")
            raise BitwardenError('Problem logging in for "{username}".')

        self.key = session_key
        return session_key

    @_logged_in
    def logout(self):
        bw = subprocess.Popen(
            f"bw logout --session {self.key}".split(), stdout=-1, stderr=-1
        )
        _, err = bw.communicate(timeout=40)
        if b"not logged in" in err:
            raise BitwardenError(
                "Cannot logout, Bitwaren session is not currently logged in."
            )
        if bw.returncode != 0:
            raise BitwardenError("Problem with logging out of session.")
        self.key = None
