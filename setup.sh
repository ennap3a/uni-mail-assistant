#!/bin/bash
# Uni Mail Assistant – setup for macOS.   Run:  bash setup.sh
# Safe to run again any time (change passwords, add Gmail/Telegram/Matrix). Never deletes your data.
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
bold() { printf "\n\033[1m%s\033[0m\n" "$1"; }

bold "🎓 Uni Mail Assistant – setup (macOS)"
echo "Everything stays on this Mac. Passwords go into the macOS Keychain, never into files."

PY=""
for c in /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$c" ] && "$c" -c 'import sys, sqlite3; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "  ❌ Python 3 is needed: install it from https://www.python.org/downloads/ and run  bash setup.sh  again."
  exit 1
fi
echo "$PY" > .python-path
echo "  ✅ $("$PY" --version)"

"$PY" wizard.py

bold "Checking everything"
echo "If macOS asks whether Terminal may use Reminders/Calendar, click OK."
if ! "$PY" helper.py check; then
  echo "  Fix the ❌ line above, then run  bash setup.sh  again."
  exit 1
fi

bold "First check of your inbox – this can take a few minutes…"
"$PY" helper.py sync || true

bash service.sh on

LAUNCHER="$HOME/Desktop/Uni Mail Assistant.command"
printf '#!/bin/bash\ncd "%s" && exec "%s" app.py\n' "$DIR" "$PY" > "$LAUNCHER"
chmod +x "$LAUNCHER"

bold "🎉 Done!"
echo "• It checks every 15 minutes while your Mac is awake (and starts by itself after a restart)."
echo "• Chat window: double-click 'Uni Mail Assistant' on your Desktop."
echo "• Change anything later: run  bash setup.sh  again.   Remove everything:  bash uninstall.sh"
