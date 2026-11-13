# 🔒 Privacy & security

Short version: **your data stays on your computer, except (1) filtered message text that goes directly to Google Gemini for sorting and (2) your notifications, if you choose Telegram. You can check every line of code.**

## Where your data is

| Data | Where it is stored | Who can see it |
|---|---|---|
| Passwords, Gemini key, Telegram bot token, Matrix token | **macOS Keychain** / **Windows Credential Manager** (encrypted by your system) | only you |
| Downloaded messages (bank numbers etc. removed) | `mail.db` in the project folder | only you |
| Apple Reminders and Calendar entries | your iCloud | you |
| Telegram notifications | your private bot chat | you, and technically Telegram's servers (see below) |
| Text sent for sorting | Google Gemini API, with **your own** key | Google (see below) |

There's **no server** run by this project, **no account**, **no analytics** and **no tracking**. The program only connects to:
1. your mail server(s) (IMAP over SSL, read-only)
2. `generativelanguage.googleapis.com` (Gemini)
3. `api.telegram.org`, only if you turn on Telegram
4. your Matrix server, only if you turn on Matrix

## What is removed before text goes to the AI
- IBANs and bank/card numbers → `[HIDDEN-IBAN]`, `[HIDDEN-NUMBER]`
- Money amounts → `[HIDDEN-AMOUNT]`
- Long number sequences (student/customer IDs) → `[HIDDEN-ID]`
- "Password: …", "PIN: …", "TAN: …", "Code: …" → `[HIDDEN]`
- **All links** → `[link]`. Links (which can contain personal tokens) only go to *your* reminders/Telegram.
- Senders in `skip_ai_for_senders` are **never sent at all**.

The filter is a safety net, not a guarantee: names, subjects and normal text are still sent so the AI can understand the message.

## Google Gemini: free vs. paid
- **Free plan:** Google may use the text you send to improve its products.
- **Paid plan** (cents per month for this use): Google does **not** use it for that.
If your inbox has sensitive content, consider the paid plan. Check Google's current terms at ai.google.dev.

## Telegram
- Your bot answers **only your own chat** (saved during setup). Messages and button taps from anyone else are ignored.
- Telegram **bot chats are not end-to-end encrypted**: Telegram's servers can technically read the notifications (summaries, sender names, links).
- For the most privacy on Mac + iPhone, use **Apple Reminders** instead (or both).
- Keep your bot token secret. If it ever leaks: in @BotFather send `/revoke`, then run the setup again with the new token.

## What it never does
- never sends, deletes, moves or marks emails as read
- never posts in Matrix/Element groups
- never uploads your config, database or logs anywhere

## Your files: keep them private
`config.json`, `mail.db`, `*.log` contain personal information. They're in `.gitignore`, so they're never uploaded if you fork this project. **Never post them, or screenshots of them, in GitHub issues.**

## Remove everything
Mac: `bash uninstall.sh` · Windows: `windows\uninstall.bat`. This stops the background service and, if you confirm, deletes the saved logins and all local data.

## Found a security problem?
Please don't open a public issue. Use **"Report a vulnerability"** in the **Security** tab of this repository.
