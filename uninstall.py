"""Deletes saved logins and local data (asks first). Used by uninstall.sh (Mac) and windows/uninstall.bat."""
import json
import os

import secrets_store

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)


def yes(q):
    return input("%s [y/N] " % q).strip().lower() in ("y", "yes", "j", "ja")


if os.path.exists("config.json") and yes("Delete saved passwords, keys and tokens?"):
    c = json.load(open("config.json", encoding="utf-8"))
    services = [a["keychain"] for a in c["accounts"]] + [
        c.get("matrix", {}).get("keychain", "unimail-matrix"),
        c.get("gemini_keychain", "unimail-gemini"),
        c.get("outputs", {}).get("telegram", {}).get("keychain", "unimail-telegram")]
    for s in services:
        secrets_store.delete(s)
    print("  Removed.")

if yes("Delete local data (mail.db, logs, config.json)?"):
    for f in os.listdir("."):
        if f.startswith("mail.db") or f.endswith(".log") or f in ("config.json", ".python-path", ".sync.lock"):
            os.remove(f)
    print("  Local data deleted.")
print("Done. You can now delete this folder.")
