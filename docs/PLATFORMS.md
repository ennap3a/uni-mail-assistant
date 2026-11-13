# Supported devices

| Your devices | Install on | Notifications | Calendar | Status |
|---|---|---|---|---|
| **Mac + iPhone** | Mac | Apple Reminders and/or Telegram | Apple Calendar (automatic) | ✅ stable |
| **Mac + Android** | Mac | Telegram | calendar file (tap to add) | ✅ stable |
| **Windows + iPhone** | Windows | Telegram | calendar file → iPhone Calendar | 🧪 beta |
| **Windows + Android** | Windows | Telegram | calendar file → Google Calendar | 🧪 beta |
| **Linux** | Linux | Telegram | calendar file | 🧪 works, no installer yet |

## How it works on each system

| | Mac | Windows |
|---|---|---|
| Password safe | macOS Keychain | Windows Credential Manager |
| Background checks | launchd (every 15 min) | Task Scheduler (every 15 min) |
| Telegram buttons/questions | always-on listener | always-on listener (starts at login) |
| Desktop chat window | ✅ | ✅ |

## Why is Windows "beta"?
The code is the same, but it needs more real-world testing on different Windows PCs. If you try it, please report what worked and what didn't (**without** logs or screenshots of your mail).

## Limits
- It only checks **while the computer is on**. It catches up as soon as it's on again.
- **Apple Reminders** can only be written from a Mac (Apple offers no way from Windows). Windows users get Telegram + calendar files instead.
- **Telegram** isn't end-to-end encrypted for bots. See [PRIVACY.md](PRIVACY.md).

## Ideas for later
- An **end-to-end encrypted Matrix bot** as a more private alternative to Telegram
- A **Raspberry Pi / Docker** version that runs 24/7
- Native **Google Tasks / Microsoft To Do** support

Want to help? Open an issue to discuss it first.
