import os
import subprocess
from typing import Union, Optional

from pynentry import PynEntry

# generic bitwarden bindings error
class BitwardenError(Exception):
    pass


class BitwardenPasswordError(BitwardenError):
    pass


# class representing a single bitwarden session
class Session:
    def __init__(self, username: Optional[str]=None):
        self.key = None
        self.username = username

    def login(self, username: Optional[str]=None, passwd: Optional[str]=None):
        if username is None:
            username = self.username
        if username is None:
            raise BitwardenError("No username defined for login operation.")

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

        session_key, err = bw.communicate(passwd.encode("utf8"), timeout=20)

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
            raise BitwardenError('Problem logging in for "{username}".')
        self.key = session_key
