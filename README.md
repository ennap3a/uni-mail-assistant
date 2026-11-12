# 🎓 Uni Mail Assistant

**Never miss an exam registration, deadline or important uni email again.** And you don't have to open your inbox to stay on top of things.

Uni Mail Assistant reads your university inbox in the background, finds what matters (deadlines, exams, payments, replies you owe) and puts it straight into the **Reminders** and **Calendar** apps on your iPhone and Mac, with all details and links.

> ### 🔒 Privacy first
> - **Runs only on your own Mac.** There's no server, no account and no cloud service of ours. Nobody but you can see your mail.
> - **Your passwords stay in the macOS Keychain** (the same place Safari keeps them). They're never written to a file.
> - **Read-only.** It never deletes, moves, sends or marks emails as read.
> - **Bank numbers, amounts, ID numbers, PINs and links are removed** *before* any text is sent to the AI.
> - **You use your own AI key** (Google Gemini, free). The only thing that leaves your Mac is that filtered text, sent directly to Google.
> - **No tracking, no analytics, no telemetry.** It's open source: every line is in this repository for you to check.
>
> Details: [docs/PRIVACY.md](docs/PRIVACY.md)

---

## What you get

| On your iPhone (Reminders app) | What's in it |
|---|---|
| **Uni – reminders** | One reminder per important or useful email: who, when, a short summary, **👉 what you must do**, the deadline as the due date, and the links. ❗️ = important, rings right away. |
| **Uni – to confirm** | Dates found in your mail (exams, deadlines, appointments, payments). ✓ **Tick** = added to your Calendar with alerts. **Delete** = ignored. |
| **Daily summary** | Every morning at 8:00: everything since yesterday, including the unimportant mail, plus your week. |

Also:
- ↩️ A reminder if someone is waiting for your reply for more than 2 days
- 💬 A **chat window** on your Mac: *"What happened yesterday?"*, *"What do I have to do this week?"*. It answers **only** from your real emails and shows which ones it used.
- 📬 Optional: **Gmail** accounts and **Matrix / Element** group chats ([docs/ADD-MORE-ACCOUNTS.md](docs/ADD-MORE-ACCOUNTS.md))

Calendar alerts: exams and appointments 1 day and 2 hours before, deadlines and payments 3 days and 1 day before.

---

## Requirements
- A **Mac** (macOS 12 or newer). Reminders sync to your **iPhone** through iCloud.
- **Python 3**. Most Macs already have it; the setup checks and tells you if not.
- A university email account with **IMAP** (default: OVGU Magdeburg, `cyrus.ovgu.de`)
- A free **Gemini API key** from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- iCloud **Reminders** and **Calendar** turned on (System Settings → your name → iCloud)

## Install (about 5 minutes)

1. Click the green **Code** button above → **Download ZIP**. Unzip it and move the folder somewhere permanent, e.g. your **Documents** folder.
2. Open the **Terminal** app (press `Cmd + Space`, type *Terminal*, press Enter).
3. Type `cd ` (with a space), **drag the folder into the Terminal window**, and press Enter.
4. Run:
   ```bash
   bash setup.sh
   ```
5. Answer the questions: your uni username and password, and your Gemini key. When macOS asks whether Terminal may use **Reminders** and **Calendar**, click **OK**.

That's it. It now checks your mail **every 15 minutes while your Mac is awake** and starts again by itself after a restart. Double-click **Uni Mail Assistant** on your Desktop to open the chat.

> **Not at OVGU?** Open `config.example.json` *before* running setup and change `"university"` and `"imap_server"` to your university's values (your university's IT help pages list the IMAP server).

## Everyday use
- Look at **Reminders** on your phone. That's it.
- Tick items in **Uni – to confirm** to put them in your calendar.
- Optional: open the chat window on your Mac and ask anything about your mail.

## Commands (in the project folder)
| Command | What it does |
|---|---|
| `bash setup.sh` | First setup, or change your password/key |
| `bash service.sh status` | Is it running? Last activity |
| `bash service.sh off` / `on` | Pause / resume background checking |
| `python3 helper.py sync` | Check mail right now |
| `python3 helper.py check` | Test logins and permissions |
| `bash uninstall.sh` | Remove everything (service, saved logins, local data) |

## Settings (`config.json`, created by setup)
- `alerts_minutes`: when calendar alerts ring (1440 = 1 day)
- `remind_for_importance`: `["high","medium"]`, or `["high"]` for fewer reminders
- `skip_ai_for_senders`: senders that are never sent to the AI (ads, shops)
- `digest_hour`: time of the morning summary

## FAQ
**Does it cost anything?** No. The free Gemini plan is enough for most students. If the daily free limit is reached, nothing is lost: remaining mail is analysed at a later check. A paid Gemini plan costs only cents per month and Google then doesn't use your data to improve its products ([docs/PRIVACY.md](docs/PRIVACY.md)).

**Does it work when my Mac is off?** It pauses and catches up as soon as the Mac is awake. To keep it running with the lid closed: plug in, then System Settings → Battery → Options → *Prevent automatic sleeping on power adapter when the display is off*.

**Windows / Android?** Not yet. See [docs/PLATFORMS.md](docs/PLATFORMS.md).

**Something doesn't work?** Run `python3 helper.py check`; it tells you what's wrong. Your `activity.log` shows what it did. **Never post your config, logs or passwords in an issue.**

## License
MIT. Free to use, change and share. See [LICENSE](LICENSE).

*This is an independent student project, not an official service of any university.*
