import subprocess
import json
from typing import Union, Optional, Any, Dict, Literal
from functools import wraps

from pynentry import PynEntry

# generic bitwarden bindings error
class BitwardenError(Exception):
    pass


class BitwardenPasswordError(BitwardenError):
    pass


class BitwardenNotLoggedInError(BitwardenError):
    pass


BWObject = Literal[
    "item",
    "username",
    "password",
    "uri",
    "totp",
    "exposed",
    "attachement",
    "folder",
    "collection",
    "organization",
    "org_collection",
    "template",
    "fingerprint",
]

# decorator for class methods to ensure that session is logged in
def _logged_in(method):
    @wraps(method)
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


class Session:
    "class representing a single bitwarden session"

    def __init__(self, username: str, passwd: Optional[str] = None):
        self.key = None
        self.username = username
        self.passwd = passwd

    def login(self, passwd: Optional[str] = None) -> str:

        if passwd is None:
            passwd = self.passwd
        if passwd is None:
            with PynEntry() as p:
                p.description = "Enter your Bitwarden Password"
                p.prompt = ">"
                passwd = p.get_pin() + "\n"  # type: ignore

        try:
            bw = subprocess.Popen(
                f"bw login {self.username} --raw".split(),
                stdin=-1,
                stdout=-1,
                stderr=-1,
            )
        except FileNotFoundError as e:
            raise BitwardenError("Bitwarden CLI `bw` could not be found.") from e

        session_key, err = bw.communicate(passwd.encode("utf8"), timeout=40)  # type: ignore
        err = err.decode("utf8")

        if "API key client_secret" in err:
            raise BitwardenError(
                (
                    "CLI must be authenticated with API key: "
                    "https://bitwarden.com/help/article/cli-auth-challenges/"
                )
            )
        if "Username or password is incorrect" in err:
            raise BitwardenPasswordError(
                'Password for "{username}" is incorrect. Try Again.'
            )
        if not session_key or bw.returncode != 0:
            raise BitwardenError(f"Problem logging in: {err}")

        session_key = session_key.decode("utf8")
        self.key = session_key
        return session_key

    def logout(self):
        bw = subprocess.Popen(
            f"bw logout --session {self.key}".split(), stdout=-1, stderr=-1
        )
        _, err = bw.communicate(timeout=40)
        if b"not logged in" in err:
            self.key = None
            return
        if bw.returncode != 0:
            raise BitwardenError("Problem with logging out of session.")
        self.key = None

    def _call(self, args):
        args.extend(["--session", self.key])
        bw = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        reply, err = bw.communicate()
        if bw.returncode != 0:
            raise BitwardenError(f'Command: "{args}" StdErr: "{err}"')
        return reply

    @_logged_in
    def get(self, obj: BWObject, ident: str) -> Union[Dict[str, Any], str]:
        args = f"bw get {obj} {ident}".split()
        reply = self._call(args)
        print(type(reply))
        reply = reply.decode("utf8")
        try:
            reply = json.loads(reply)
        except json.decoder.JSONDecodeError:
            pass
        return reply

    @_logged_in
    def get_item(self, ident: str) -> dict[str, Any]:
        reply = self.get("item", ident)
        assert isinstance(reply, dict)
        return reply
