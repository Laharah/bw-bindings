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

    def __init__(self, username: str, passwd: Optional[str] = None):
        self.key = None
        self.username = username
        self.passwd = passwd

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
        "Logout of BitWarden session and delete the session key"

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
        "Helper method for adding session key and making Bitwarden CLI call."

        args.extend(["--session", self.key])
        bw = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        reply, err = bw.communicate()
        if bw.returncode != 0:
            err = err.decode("utf8", "ignore")
            raise BitwardenError(f'Command: "{args}"\nStdErr: "{err}"')
        return reply

    @_logged_in
    def get(self, obj: BWObject, ident: str) -> Union[Dict[str, Any], str]:
        """Bitwarden `get` call. Supply CLI with the passed arguments and
        decode any json replies"""

        args = f"bw get {obj} {ident}".split()
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
        args = f"bw list {obj}".split() + flags
        reply = json.loads(self._call(args))
        assert isinstance(reply, list)
        return reply

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, type, value, traceback):
        self.logout()
