# Adding Gmail and Matrix / Element groups

Everything is built in. You only add your private login (stored in the **Keychain**, never in a file) and switch the account on in `config.json`.
Afterwards, run this in the project folder:
```bash
python3 helper.py check
```

---

## Gmail (once per account)

Google doesn't allow your normal password here. You create an **app password**: it can only be used for this and you can delete it at any time.

1. Open **myaccount.google.com/security** and make sure **2-Step Verification** is on.
2. Open **myaccount.google.com/apppasswords** → name it `Uni Mail Assistant` → **Create** → copy the 16-letter password.
3. Save it in the Keychain. Use your Gmail address, then paste the app password when asked:
   ```bash
   security add-generic-password -s unimail-gmail-1 -a YOUR_ADDRESS@gmail.com -w
   ```
   For a second account, use `unimail-gmail-2` instead.
4. In `config.json`, set `"enabled": true` for "Gmail" (and "Gmail 2").
5. Run `python3 helper.py check`, then `python3 helper.py sync`.

Tip: add shop/newsletter senders to `skip_ai_for_senders`, so they're never sent to the AI.

### Outlook / Hotmail
Microsoft no longer allows simple passwords for outlook.com. The easiest way: in Outlook.com → Settings → Mail → **Forwarding**, forward to one of your Gmail accounts.

---

## Matrix / Element groups (e.g. course or student groups)

The assistant reads new messages in your groups (**read-only, it never posts**), keeps only announcements, deadlines, events and anything addressed to you, and turns them into reminders with a link that opens the message in Element.

1. Log in to your Matrix account at **app.element.io** (Element Web). If your group uses its own server, choose that server when logging in.
2. Avatar → **All settings** → **Help & About** → **Advanced** → **Access Token** → copy it.
   ⚠️ This token works like your password. **Never share it or post it anywhere.**
3. Save it in the Keychain and paste the token when asked:
   ```bash
   security add-generic-password -s unimail-matrix -a matrix -w
   ```
4. In `config.json`, under `"matrix"`:
   - `"enabled": true`
   - `"server"`: your Matrix server (e.g. `matrix.org` or your university's server)
   - `"rooms": []` reads all your groups. To limit it, list room names: `["My Course Group"]`
5. Run `python3 helper.py check`, then `python3 helper.py sync`.

Notes:
- **Don't click "Sign out"** in that Element Web session. Signing out makes the token stop working; just close the tab. If it stops working, delete the old one (`security delete-generic-password -s unimail-matrix`) and repeat steps 2–3.
- **End-to-end encrypted** rooms (🔒) can't be read; the log will say so. Most announcement groups aren't encrypted.
