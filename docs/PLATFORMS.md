# Which devices are supported?

| Setup | Status |
|---|---|
| **Mac + iPhone** | ✅ Fully supported. Reminders and Calendar sync through iCloud |
| **Mac only** | ✅ Works (Reminders/Calendar on the Mac) |
| **Mac + Android phone** | ⚠️ Partly. See below |
| **Windows** | ❌ Not yet |
| **Linux** | ❌ Not yet |

## Why Mac first?
The program puts everything into **Apple Reminders and Calendar** (via AppleScript) and stores passwords in the **macOS Keychain**. That's what makes it easy and private on a Mac + iPhone: no extra accounts, no server.

## What a Windows version would need
The email reading, AI sorting, privacy filter and chat window are plain Python and work on Windows. Three parts are Mac-only and need replacing:
1. **Reminders/Calendar** → use **Microsoft To Do / Outlook Calendar** (Microsoft Graph API; needs a Microsoft app registration and sign-in, which is more setup for users), or **Google Tasks / Google Calendar** (needs a Google Cloud project), or an `.ics` calendar file.
2. **Keychain** → **Windows Credential Manager** (Python package `keyring`).
3. **Background service** → **Windows Task Scheduler**.
Main difficulty: every user would have to create their own Microsoft or Google API app to write reminders. That's the hard part to make simple.

## Android users
Apple Reminders can't be used on Android. Options:
- **Google Tasks + Google Calendar** (best fit on Android; the same API work as above)
- **Matrix/Element or Telegram messages:** the assistant sends you a chat message instead of a reminder. That works on every phone and is easy to set up, so it's the most likely next step.

## Contributions welcome
If you'd like to build the Windows/Android version, open an issue to discuss it first.
