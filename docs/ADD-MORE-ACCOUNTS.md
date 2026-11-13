# Step-by-step guides

The setup (`bash setup.sh` on Mac, `setup.bat` on Windows) walks you through everything below. This page explains each step in more detail. **Run the setup again any time to add something**; your existing settings are kept.

Passwords, keys and tokens are saved in the **Keychain** (Mac) or **Credential Manager** (Windows), never in a file.

- [1. University webmail](#1-university-webmail)
- [2. Gemini key](#2-gemini-key)
- [3. Telegram](#3-telegram)
- [4. Gmail](#4-gmail)
- [5. Matrix / Element groups](#5-matrix--element-groups)
- [6. Other email (optional)](#6-other-email-optional)

---

## 1. University webmail
1. Find your university's **IMAP server** on its IT help pages (search: *"<your university> IMAP server"*). OVGU: `cyrus.ovgu.de`.
2. Find your **username**: use exactly the one that works when you log in to your university **webmail** in the browser. ⚠️ At many universities it is **not** your email address. This is the most common setup mistake.
3. In the setup, enter the server, the username, and then your password (hidden while typing).

If the check says *"login was rejected"*, log in to the webmail in your browser with the same username and password to confirm they're right, then run the setup again.

## 2. Gemini key
1. Open **aistudio.google.com/apikey** and sign in with any Google account.
2. Click **Create API key** → copy it → paste it in the setup.
The free plan is enough. If the daily limit is reached, messages just wait until later.

## 3. Telegram
Works on **every phone**. You create your own private bot (takes 2 minutes):
1. Install **Telegram** on your phone and log in.
2. Open **@BotFather** (https://t.me/BotFather) → send `/newbot`.
3. Choose a name (e.g. *My Uni Mail*) and a username ending in `bot` (e.g. *my_uni_mail_2026_bot*).
4. BotFather replies with a **token** like `123456789:AA...`. Copy it. ⚠️ Never share it.
5. Paste it in the setup. The setup opens your bot; press **START** on your phone.
6. Confirm in the setup that the message came from you. Done: you get a "✅ Connected" message.

**Using it:** tap **✓ Add to calendar** on a date, then tap the calendar file you receive to add it with alerts. Ask anything, or use `/yesterday`, `/today`, `/week`, `/todo`, `/help`.
Your bot ignores everyone except you.

## 4. Gmail
Google doesn't allow your normal password here. You create an **app password** that only works for this and can be deleted any time:
1. Open **myaccount.google.com/security** → turn on **2-Step Verification**.
2. Open **myaccount.google.com/apppasswords** → name it `Uni Mail Assistant` → **Create** → copy the 16 letters.
3. In the setup: answer **y** at "Add Gmail account?", enter your Gmail address, then paste the app password.
4. Second Gmail account: answer **y** at "Add Gmail 2 account?" and repeat steps 2–3 for that account.

Tip: Gmail has many ads. Add shop/newsletter senders to `skip_ai_for_senders` in `config.json`, so they're never sent to the AI.

## 5. Matrix / Element groups
For course and student groups on Element. The assistant **only reads** (never posts). It keeps announcements, deadlines, events and anything addressed to you, and sends each with a link that opens the message in Element.
1. Log in at **app.element.io** in your browser. If your group uses its own server, click **Edit** next to the server name and enter it (e.g. your university's Matrix server).
2. Click your avatar → **All settings** → **Help & About** → scroll to **Advanced** → **Access Token** → click to copy.
   ⚠️ This token works like your password. Never share it or post it anywhere.
3. In the setup: answer **y** at "Read your Matrix/Element groups?", enter the server, and paste the token.
4. Optional: list only some groups by name, or press Enter for all.

Notes:
- Don't press **Sign out** in that browser session later; it makes the token stop working. Just close the tab. If it stops working, repeat steps 1–3 (run the setup again).
- **Encrypted** groups (🔒 shield in Element) can't be read; the log will say so. Most announcement groups aren't encrypted.

## 6. Other email (optional)
In the setup, step 6 "Add another email account?" offers ready-made settings:

| Provider | Server (filled in for you) | What you need |
|---|---|---|
| **GMX** | `imap.gmx.net` | In GMX web: Settings → POP3 & IMAP → allow access. Normal password. |
| **WEB.DE** | `imap.web.de` | In WEB.DE: Settings → POP3 & IMAP → allow access. Normal password. |
| **iCloud Mail** | `imap.mail.me.com` | An **app-specific password**: account.apple.com → Sign-In and Security → App-Specific Passwords. Username = your iCloud address. |
| **Yahoo** | `imap.mail.yahoo.com` | An **app password**: Yahoo Account Security → Generate app password. |
| **Other** | you type it | Search *"<provider> IMAP server"*. Most use port 993. |
| **Outlook / Hotmail** | not supported | Microsoft blocks password logins. In Outlook.com → Settings → Mail → **Forwarding**, forward to your Gmail; it's then covered by step 4. |

Each extra account gets its own reminders list (Apple) or label (Telegram), and you can add as many as you want.
