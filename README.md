# BitWarden Bindings
### A pythonic wrapper the bitwarden cli

***Requires [pinentry](https://gnupg.org/related_software/pinentry/index.html) and [bitwarden cli](https://bitwarden.com/help/article/cli/) to be installed***

### Usage

The module consists of mostly one class: `Session`. This represents a single session
coresponding to a bitwarden session with it's own session key. It is best used as a
context manager like so:

```python
from bw_bindings as bw

with bw.Session("username", "password") as session:
	json_data = session.get_item("github")
	user, passwd = json_data['login']["username"], json_data['login']['password']

	amazon_user = session.get("username", "amazon.com")
	amazon_passwd = session.get("password", "amazon.com")

post_wishlist_gist(user, passwd, amazon_user, amazon_passwd)
```

If you want to use the session object directly, you will have to call login and logout
manually:
```python
from pprint import pprint
import bw_bindings as bw

session = bw.Session("username")
session.login("password")

pprint(session.list("items", url="github.com"))
session.logout()
```

#### Password Prompting

If the `Session` object is not supplied with a password argument, either when insanciated
or during the `Session.login()` call, a
[pinentry](https://gnupg.org/related_software/pinentry/index.html) prompt will be launched
during the `login` call. **This will require user interaction and may hang headless use
cases.** If you are using this module in a headless session, you should supply the Session
with a password either at construction or as an argument to the `Session.login()` method.
