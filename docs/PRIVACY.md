# 🔒 Privacy & security

Short version: **your data stays on your Mac, except filtered email text that goes directly to Google Gemini for sorting. You can check every line of code.**

## Where your data is

| Data | Where it is stored | Who can see it |
|---|---|---|
| Uni / Gmail password, Gemini key, Matrix token | macOS **Keychain** (encrypted) | only you |
| Downloaded emails (text with bank numbers etc. removed) | `mail.db` in the project folder | only you |
| Reminders and calendar entries | your iCloud Reminders / Calendar | you (and anyone you share those lists with) |
| Text sent for sorting | Google Gemini API, using **your own** key | Google (see below) |

There's **no server** run by this project, **no account**, **no analytics** and **no tracking**. The program only connects to:
1. your mail server(s) (IMAP over SSL, read-only)
2. `generativelanguage.googleapis.com` (Gemini)
3. your Matrix server, only if you turn it on

## What is removed before text goes to the AI
- IBANs and bank/card numbers → `[HIDDEN-IBAN]`, `[HIDDEN-NUMBER]`
- Money amounts → `[HIDDEN-AMOUNT]`
- Long number sequences (student/customer IDs) → `[HIDDEN-ID]`
- "Password: …", "PIN: …", "TAN: …", "Code: …" → `[HIDDEN]`
- **All links** → `[link]`. Links (which can contain personal tokens) are only put into *your* reminders.
- Emails from senders in `skip_ai_for_senders` are **never sent at all**.

The filter is a safety net, not a guarantee: names, subjects and normal text are still sent so the AI can understand the email.

## Google Gemini: free vs. paid
- **Free plan:** Google may use the text you send to improve its products.
- **Paid plan** (costs cents per month for this use): Google does **not** use it for that.
If your inbox has sensitive content, consider the paid plan. Check Google's current terms at ai.google.dev.

## What it never does
- never sends, deletes, moves or marks emails as read
- never posts in Matrix/Element groups
- never uploads your config, database or logs anywhere

## Your files: keep them private
`config.json`, `mail.db`, `*.log` contain personal information. They're listed in `.gitignore`, so they're never uploaded if you fork this project. **Never post them in GitHub issues.**

## Remove everything
`bash uninstall.sh` stops the service and (if you confirm) deletes the saved logins from the Keychain and all local data.

## Found a security problem?
Please don't open a public issue with details. Use GitHub's **"Report a vulnerability"** (Security tab of this repository).
