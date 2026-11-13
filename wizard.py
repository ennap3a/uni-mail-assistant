"""Interactive setup (Mac and Windows). Started by setup.sh / setup.bat – you don't need to run it yourself.
Passwords and keys go straight into the Keychain / Credential Manager; config.json only gets non-secret settings."""
import json
import os
import sys
import time
import webbrowser

import net  # noqa: F401  (secure certificate checking)
import secrets_store

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
EXAMPLE = os.path.join(HERE, "config.example.json")

OTHER_PROVIDERS = {
    "1": ("GMX", "imap.gmx.net", "Turn on IMAP: GMX web → Settings → POP3 & IMAP → allow access. Use your normal password."),
    "2": ("WEB.DE", "imap.web.de", "Turn on IMAP: WEB.DE → Settings → POP3 & IMAP → allow access. Use your normal password."),
    "3": ("iCloud Mail", "imap.mail.me.com", "Create an app-specific password: account.apple.com → Sign-In and Security → App-Specific Passwords. Username = your iCloud email address."),
    "4": ("Yahoo", "imap.mail.yahoo.com", "Create an app password: Yahoo Account Security → Generate app password."),
    "5": ("Other", None, "Find the IMAP server on your provider's help pages (search: '<provider> IMAP server')."),
}


if os.name == "nt":
    os.system("")  # turns on colours/bold text in the Windows console


def title(t):
    print("\n\033[1m%s\033[0m" % t)


def ask(q, default=""):
    a = input("  %s%s: " % (q, " [%s]" % default if default else "")).strip()
    return a or default


def yes(q, default=False):
    a = input("  %s [%s] " % (q, "Y/n" if default else "y/N")).strip().lower()
    return default if not a else a in ("y", "yes", "j", "ja")


def save(cfg):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def setup_login(service, username_hint):
    if secrets_store.exists(service) and not yes("A login is already saved. Replace it?"):
        return
    user = ask(username_hint)
    secrets_store.ask_and_save_login(service, user)
    print("  ✅ Saved securely")


def telegram_setup(cfg):
    from telegram_bot import Bot
    tg = cfg["outputs"]["telegram"]
    print("""  1. In Telegram, open  @BotFather  (https://t.me/BotFather)
  2. Send  /newbot  , choose a name and a username ending in 'bot'
  3. BotFather replies with a TOKEN (looks like 123456:ABC-...). Copy it.
  ⚠️  The token controls your bot – never share it.""")
    if not (secrets_store.exists(tg["keychain"]) and not yes("A bot token is already saved. Replace it?")):
        secrets_store.ask_and_save_secret(tg["keychain"], "bot token")
    bot = Bot(secrets_store.get_secret(tg["keychain"]))
    me = bot.me()
    print("  ✅ Bot found: @%s" % me["username"])
    url = "https://t.me/%s" % me["username"]
    print("  4. Now open %s on your phone and press START (or send 'hi')." % url)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("  Waiting for your message (up to 3 minutes)…")
    offset, deadline = None, time.time() + 180
    while time.time() < deadline:
        for u in bot.updates(offset, timeout=20):
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            chat = msg.get("chat", {})
            if chat.get("type") == "private":
                who = chat.get("first_name") or chat.get("username") or "?"
                if yes("Message received from '%s'. Is that you?" % who, True):
                    bot.updates(offset)  # mark as read
                    tg["chat_id"] = chat["id"]
                    tg["enabled"] = True
                    bot.chat_id = chat["id"]
                    bot.send("✅ Connected! You'll get your important uni messages here.\nSend /help to see what I can do.")
                    print("  ✅ Telegram connected – check your phone.")
                    return
    print("  ❌ No message arrived. Run setup again to retry Telegram.")


def main():
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        print("  Existing settings found – they will be kept unless you change them.")
    else:
        with open(EXAMPLE, encoding="utf-8") as f:
            cfg = json.load(f)
    cfg.setdefault("outputs", {"apple_reminders": secrets_store.IS_MAC,
                               "telegram": {"enabled": False, "keychain": "unimail-telegram", "chat_id": None, "listen": True}})
    uni = cfg["accounts"][0]

    title("Step 1 – your university email (webmail)")
    cfg["university"] = ask("University name", cfg.get("university", ""))
    uni["imap_server"] = ask("Mail server (IMAP) – see your university's IT help pages", uni["imap_server"])
    print("  Tip: use exactly the username that works at your university webmail (often NOT the email address).")
    setup_login(uni["keychain"], "Username")
    save(cfg)

    title("Step 2 – your own Gemini AI key (free)")
    gk = cfg.get("gemini_keychain", "unimail-gemini")
    print("  Open https://aistudio.google.com/apikey → sign in with Google → 'Create API key' → copy it.")
    if not (secrets_store.exists(gk) and not yes("A Gemini key is already saved. Replace it?")):
        secrets_store.ask_and_save_secret(gk, "Gemini key")
        print("  ✅ Saved securely")

    title("Step 3 – where do you want your reminders?")
    out = cfg["outputs"]
    if secrets_store.IS_MAC:
        out["apple_reminders"] = yes("Apple Reminders + Calendar (iPhone/Mac, most private)?", out.get("apple_reminders", True))
    else:
        out["apple_reminders"] = False
        print("  (Apple Reminders needs a Mac – using Telegram.)")
    print("  Telegram works on every phone (iPhone + Android). Note: Telegram can technically read bot messages.")
    if yes("Use Telegram?", out["telegram"].get("enabled") or not secrets_store.IS_MAC):
        try:
            telegram_setup(cfg)
        except Exception as e:
            out["telegram"]["enabled"] = False
            print("  ❌ Telegram could not be set up: %s" % e)
            print("  Telegram stays off for now – fix the problem and run the setup again. Continuing…")
    else:
        out["telegram"]["enabled"] = False
    save(cfg)

    title("Step 4 (optional) – Gmail")
    for acc in [a for a in cfg["accounts"] if a["imap_server"] == "imap.gmail.com"]:
        if not yes("Add %s account%s?" % (acc["name"], " (currently ON)" if acc.get("enabled") else ""), acc.get("enabled", False)):
            acc["enabled"] = False
            continue
        print("""  Gmail needs an APP PASSWORD (not your normal password):
   a) myaccount.google.com/security → turn on 2-Step Verification
   b) myaccount.google.com/apppasswords → name it 'Uni Mail Assistant' → Create → copy the 16 letters""")
        setup_login(acc["keychain"], "Gmail address")
        acc["enabled"] = True
    save(cfg)

    title("Step 5 (optional) – Matrix / Element group chats")
    mx = cfg["matrix"]
    if yes("Read your Matrix/Element groups?", mx.get("enabled", False)):
        mx["server"] = ask("Matrix server (e.g. matrix.org or your university's)", mx.get("server", ""))
        print("""  Get your access token: log in at app.element.io (choose that server) →
   avatar → All settings → Help & About → Advanced → Access Token → copy.
  ⚠️  It works like a password – never share it. Don't press 'Sign out' in that browser session later.""")
        if not (secrets_store.exists(mx["keychain"]) and not yes("A Matrix token is already saved. Replace it?")):
            secrets_store.ask_and_save_secret(mx["keychain"], "Matrix access token")
        rooms = ask("Only these groups (comma-separated names), or Enter for all", ", ".join(mx.get("rooms", [])))
        mx["rooms"] = [r.strip() for r in rooms.split(",") if r.strip()]
        mx["enabled"] = True
    else:
        mx["enabled"] = False
    save(cfg)

    title("Step 6 (optional) – other email accounts")
    while yes("Add another email account (GMX, WEB.DE, iCloud, Yahoo, other)?"):
        for k, (name, _, _) in OTHER_PROVIDERS.items():
            print("   %s) %s" % (k, name))
        name, server, hint = OTHER_PROVIDERS.get(ask("Choose", "5"), OTHER_PROVIDERS["5"])
        print("  " + hint)
        server = ask("IMAP server", server or "")
        label = ask("Name for this account", name)
        service = "unimail-" + "".join(c for c in label.lower() if c.isalnum())
        setup_login(service, "Username / email address")
        cfg["accounts"] = [a for a in cfg["accounts"] if a["keychain"] != service]
        cfg["accounts"].append({"name": label, "enabled": True, "imap_server": server, "imap_port": 993,
                                "keychain": service, "reminders_list": "%s – reminders" % label})
        save(cfg)
        print("  ✅ Added %s" % label)
    print("  (Outlook/Hotmail: Microsoft blocks this – forward it to your Gmail instead.)")
    save(cfg)
    print("\n  ✅ Settings saved.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nCancelled. Run setup again any time.")
    except Exception as e:  # show a clear message, not a Python error dump
        sys.exit("\n❌ Setup stopped: %s\nYour answers so far are saved – run the setup again to continue." % e)
