# 🎓 Uni Mail Assistant

**Never miss an exam registration, deadline or important uni message again, without opening your inbox.**

Uni Mail Assistant checks your **university webmail**, **Gmail** and **Matrix / Element groups** in the background, finds what matters (deadlines, exams, payments, replies you owe) and sends it to your phone, with all details and links:

- **🍎 Apple Reminders + Calendar** (Mac + iPhone): most private
- **✈️ Telegram** (any phone: iPhone or Android, from Mac or Windows)

> ### 🔒 Privacy first
> - **Runs only on your own computer.** There's no server, no account and no cloud service of ours. Nobody but you can see your mail.
> - **Passwords stay in your system's password safe** (macOS Keychain / Windows Credential Manager). They're never written to a file.
> - **Read-only.** It never deletes, moves, sends or marks emails as read, and never posts in your groups.
> - **Bank numbers, amounts, ID numbers, PINs and links are removed** *before* any text is sent to the AI.
> - **You use your own AI key** (Google Gemini, free). The only things that leave your computer are that filtered text (to Google) and, if you choose Telegram, your notifications (to Telegram).
> - **No tracking, no analytics.** It's open source: every line is in this repository for you to check.
>
> Details: [docs/PRIVACY.md](docs/PRIVACY.md)

---

## Which version is for me?

| Your devices | Install on | You get |
|---|---|---|
| **Mac + iPhone** | Mac | Apple Reminders + Calendar (and/or Telegram) |
| **Mac + Android** | Mac | Telegram |
| **Windows + iPhone** | Windows *(beta)* | Telegram + calendar files for your iPhone Calendar |
| **Windows + Android** | Windows *(beta)* | Telegram + calendar files |

More details: [docs/PLATFORMS.md](docs/PLATFORMS.md)

## What you get

- **Every important or useful message** (who, when, short summary, **👉 what you must do**, deadline, links). ❗️ = important, and you get notified right away.
- **Dates** (exams, deadlines, appointments, payments) with **✓ Add to calendar / ✗ Ignore**:
  - Apple: tick it in the *Uni – to confirm* list
  - Telegram: tap the button and you get a calendar file; tap it to add the event with alerts
- **Deadline reminders** 3 days and 1 day before
- **↩️ "You haven't replied yet"** after 2 days, when someone is waiting for your answer
- **☀️ Morning summary** at 8:00: everything since yesterday, your week, what waits for your OK
- **💬 Ask questions:** in Telegram (`/yesterday`, `/week`, `/todo` or any question) or in the chat window on your computer. Answers use **only** your real messages and say which ones.

Calendar alerts: exams and appointments 1 day and 2 hours before, deadlines and payments 3 days and 1 day before.

---

## What you need
- A **Mac** (macOS 12+) or a **Windows 10/11 PC** *(beta)*
- **Python 3**: the setup checks for it and tells you how to install it if needed
- Your **university email** login (IMAP). Default: OVGU Magdeburg; any university works
- A free **Gemini API key**: [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (setup shows you how)
- Optional: **Telegram** on your phone, **Gmail**, a **Matrix/Element** account

## Install

### 🍎 Mac (about 5 minutes)
1. Click the green **Code** button above → **Download ZIP**. Unzip it and move the folder to a permanent place, e.g. **Documents**.
2. Open **Terminal** (`Cmd + Space`, type *Terminal*, Enter).
3. Type `cd ` (with a space), **drag the folder into the Terminal window**, press Enter.
4. Run:
   ```bash
   bash setup.sh
   ```
5. Answer the questions. When macOS asks whether Terminal may use **Reminders** and **Calendar**, click **OK**.

### 🪟 Windows *(beta, feedback welcome)*
1. Install **Python** from [python.org/downloads](https://www.python.org/downloads/). ⚠️ In the installer, tick **"Add python.exe to PATH"**.
2. Download this project (**Code → Download ZIP**), unzip it, and move the folder to e.g. **Documents**.
3. Open the folder and **double-click `setup.bat`**. If Windows shows "Windows protected your PC", click **More info → Run anyway**.
4. Answer the questions and choose **Telegram** for your notifications.

### The setup asks you, step by step
1. **University webmail:** server and your login
2. **Gemini key**
3. **Where to send reminders:** Apple Reminders (Mac) and/or Telegram
4. *(optional)* **Gmail** accounts
5. *(optional)* **Matrix / Element** groups
6. *(optional)* **Other email** (GMX, WEB.DE, iCloud, Yahoo, any IMAP)

Every step has its own guide: [docs/ADD-MORE-ACCOUNTS.md](docs/ADD-MORE-ACCOUNTS.md)

When it's done, it checks **every 15 minutes while your computer is on** and starts again by itself after a restart. **Run the setup again any time** to change passwords or add accounts; it keeps your data.

## Everyday use
Just look at your **phone** (Reminders or Telegram). That's it.

## Commands (in the project folder)
| Mac | Windows | What it does |
|---|---|---|
| `bash setup.sh` | double-click `setup.bat` | Setup, or change settings/passwords, add accounts |
| `bash service.sh status` | `powershell -File windows\service.ps1 status` | Is it running? Last activity |
| `bash service.sh off` / `on` | `… service.ps1 off` / `on` | Pause / resume |
| `python3 helper.py sync` | `python helper.py sync` | Check right now |
| `python3 helper.py check` | `python helper.py check` | Test logins and outputs |
| `bash uninstall.sh` | double-click `windows\uninstall.bat` | Remove everything |

## Settings (`config.json`, created by setup)
- `remind_for_importance`: `["high","medium"]`, or `["high"]` for fewer messages
- `skip_ai_for_senders`: senders that are never sent to the AI (ads, shops)
- `alerts_minutes`: when calendar alerts ring (1440 = 1 day)
- `digest_hour`: time of the morning summary

## FAQ
**Does it cost anything?** No. The free Gemini plan is enough for most students. If the daily free limit is reached, nothing is lost; remaining messages are analysed later. A paid Gemini plan costs cents per month, and then Google doesn't use your data to improve its products.

**Does it work when my computer is off?** It pauses and catches up when the computer is on again. Mac with the lid closed: plug in, then System Settings → Battery → Options → *Prevent automatic sleeping on power adapter when the display is off*.

**Is Telegram private?** Your bot only answers **you**; messages from anyone else are ignored. But Telegram bot chats aren't end-to-end encrypted, so Telegram's servers could technically read them. For maximum privacy on Mac + iPhone, use Apple Reminders.

**Something doesn't work?** Run `helper.py check`; it tells you what's wrong. **Never post your config, logs, tokens or passwords in an issue.**

## License
MIT. Free to use, change and share. See [LICENSE](LICENSE).

*Independent student project, not an official service of any university.*
