"""Where passwords and keys are kept – never in a file.

macOS   -> the macOS Keychain (built in, via the `security` tool)
Windows -> Windows Credential Manager (via the `keyring` package, installed by setup)
Linux   -> the system keyring (via `keyring`)
"""
import re
import subprocess
import sys

IS_MAC = sys.platform == "darwin"


class MissingSecret(RuntimeError):
    pass


# ------------------------------------------------------------------ macOS

def _security(*args, interactive=False):
    if interactive:
        return subprocess.run(["/usr/bin/security", *args])
    return subprocess.run(["/usr/bin/security", *args], capture_output=True, text=True)


# ------------------------------------------------------------------ public API

def get_login(service):
    """-> (username, password) for a mail account."""
    if IS_MAC:
        r = _security("find-generic-password", "-s", service)
        m = re.search(r'"acct"<blob>="([^"]*)"', r.stdout)
        pw = _security("find-generic-password", "-s", service, "-w").stdout.strip()
        if m and pw:
            return m.group(1), pw
    else:
        import keyring
        user = keyring.get_password(service, "username")
        pw = keyring.get_password(service, "password")
        if user and pw:
            return user, pw
    raise MissingSecret("Login '%s' is not saved yet (run setup again)." % service)


def get_secret(service):
    """-> a single secret (API key, token)."""
    if IS_MAC:
        v = _security("find-generic-password", "-s", service, "-w").stdout.strip()
    else:
        import keyring
        v = keyring.get_password(service, "secret") or ""
    if not v:
        raise MissingSecret("'%s' is not saved yet (run setup again)." % service)
    return v


def exists(service):
    if IS_MAC:
        return _security("find-generic-password", "-s", service).returncode == 0
    import keyring
    return bool(keyring.get_password(service, "secret") or keyring.get_password(service, "password"))


def delete(service):
    if IS_MAC:
        while _security("delete-generic-password", "-s", service).returncode == 0:
            pass
        return
    import keyring
    for key in ("secret", "username", "password"):
        try:
            keyring.delete_password(service, key)
        except Exception:
            pass


def ask_and_save_login(service, username):
    """Asks for the password (hidden) and saves it."""
    delete(service)
    if IS_MAC:  # macOS asks for the password itself, so it never passes through this program
        print("  Type the password (twice). Nothing is shown while typing – that's normal.")
        if _security("add-generic-password", "-s", service, "-a", username, "-w", interactive=True).returncode != 0:
            raise RuntimeError("Saving failed – please try again.")
        return
    import getpass
    import keyring
    pw = getpass.getpass("  Password (hidden while typing): ")
    keyring.set_password(service, "username", username)
    keyring.set_password(service, "password", pw)


def ask_and_save_secret(service, label):
    delete(service)
    if IS_MAC:
        print("  Paste the %s (twice). Nothing is shown while pasting – that's normal." % label)
        if _security("add-generic-password", "-s", service, "-a", "unimail", "-w", interactive=True).returncode != 0:
            raise RuntimeError("Saving failed – please try again.")
        return
    import getpass
    import keyring
    keyring.set_password(service, "secret", getpass.getpass("  Paste the %s (hidden): " % label).strip())
