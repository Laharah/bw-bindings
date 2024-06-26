import json
import os
import shutil
import subprocess
from functools import wraps
from typing import Any, Dict, Literal, Optional, Union

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

BWTemplates = Literal[
    "item",
    "item.field",
    "item.login",
    "item.login.uri",
    "item.card",
    "item.identity",
    "item.securenote",
    "folder",
    "collection",
    "item-collections",
    "org-collection",
]


def _logged_in(method):
    "decorator for class methods to ensure that session is logged in"

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

    def __init__(
        self,
        username: str,
        passwd: Optional[str] = None,
        executable: Optional[os.PathLike] = None,
        timeout=40,
    ):
        self.key = None
        self.username = username
        self.passwd = passwd
        if executable is None:
            _exe = shutil.which("bw")
        else:
            _exe = executable
        if not _exe:
            raise BitwardenError("Bitwarden CLI executable `bw` could not be found.")
        self.executable = str(_exe)
        self.timeout = timeout

    def login(self, passwd: Optional[str] = None) -> str:
        """Log into bitwarden and save the session key for use.
        If no password has been supplied, prompt user with Pinentry"""

        if passwd is None:
            passwd = self.passwd
        if passwd is None:
            with PynEntry() as p:
                p.description = "Enter your Bitwarden Password"
                p.prompt = ">"
                passwd = p.get_pin() + "\n"  # type: ignore

        args = f"login {self.username} --raw".split()
        try:
            bw = subprocess.Popen(
                [self.executable] + args,
                stdin=-1,
                stdout=-1,
                stderr=-1,
            )
        except FileNotFoundError as e:
            raise BitwardenError(
                f"Bitwarden CLI `{self.executable}` could not be found."
            ) from e

        session_key, err = bw.communicate(passwd.encode("utf8"), timeout=self.timeout)  # type: ignore
        del passwd  # Don't let sensitive info hang around
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
        "Logout of BitWarden session and delete the session key"

        bw = subprocess.Popen(
            [self.executable] + f"logout --session {self.key}".split(),
            stdout=-1,
            stderr=-1,
        )
        _, err = bw.communicate(timeout=self.timeout)
        if b"not logged in" in err:
            self.key = None
            return
        if bw.returncode != 0:
            raise BitwardenError("Problem with logging out of session.")
        self.key = None

    def _call(self, args):
        "Helper method for adding session key and making Bitwarden CLI call."

        args = [self.executable] + args
        args.extend(["--session", self.key])
        bw = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "BW_SESSION": str(self.key)},
        )
        try:
            reply, err = bw.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            bw.kill()
            raise
        if bw.returncode != 0:
            err = err.decode("utf8", "ignore")
            raise BitwardenError(f'Command: "{args}"\nStdErr: "{err}"')
        return reply

    @_logged_in
    def get(self, obj: BWObject, ident: str) -> Union[Dict[str, Any], str]:
        """Bitwarden `get` call. Supply CLI with the passed arguments and
        decode any json replies"""

        args = f"get {obj} {ident}".split()
        reply = self._call(args)
        reply = reply.decode("utf8")
        try:
            reply = json.loads(reply)
        except json.decoder.JSONDecodeError:
            pass
        return reply

    @_logged_in
    def get_item(self, ident: str) -> dict[str, Any]:
        "Convieninece method for `get`ing items. Equivalent to s.get('item', ident)."
        reply = self.get("item", ident)
        assert isinstance(reply, dict)
        return reply

    @_logged_in
    def get_template(self, ident: BWTemplates) -> dict[str, Any]:
        "Convieninece metod for `get`ing templates for editing/creation."

        reply = self.get("template", ident)
        assert isinstance(reply, dict)
        return reply

    @_logged_in
    def list(
        self,
        obj: Literal[
            "items",
            "folders",
            "collections",
            "organization",
            "org-collections",
            "org-members",
        ],
        search: Optional[str] = None,
        *,
        trash: bool = False,
        **kwargs,
    ) -> list[dict[str, Any]]:
        "Make BitwardenCLI `list` call. Accepts CLI flags as key-word arguments."

        kwargs["search"] = search
        kwargs["trash"] = trash

        flags = []
        for key, value in kwargs.items():
            if not value:
                continue
            flags.extend([f"--{key}", value])
        args = f"list {obj}".split() + flags
        reply = json.loads(self._call(args))
        assert isinstance(reply, list)
        return reply

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, type, value, traceback):
        self.logout()
