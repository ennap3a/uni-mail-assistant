#!/bin/bash
# Uni Mail Assistant – guided setup for macOS.
# Run it from this folder:   bash setup.sh
# You can run it again at any time (e.g. to change your password); it never deletes your data.
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"

bold() { printf "\n\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "  ✅ %s\n" "$1"; }
fail() { printf "  ❌ %s\n" "$1"; exit 1; }

bold "🎓 Uni Mail Assistant – setup"
echo "Everything stays on this Mac. Passwords go into the macOS Keychain, never into files."

# ---------------------------------------------------------------- 1. macOS + Python
[ "$(uname)" = "Darwin" ] || fail "This version is for macOS only."

PY=""
for c in /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$c" ] && "$c" -c 'import sys, sqlite3, tkinter; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "  Python 3 is needed. Download the macOS installer from https://www.python.org/downloads/ ,"
  echo "  install it, then run  bash setup.sh  again."
  fail "Python 3 not found."
fi
echo "$PY" > .python-path
ok "Python: $("$PY" --version)"

# ---------------------------------------------------------------- 2. settings file
if [ ! -f config.json ]; then
  cp config.example.json config.json
  ok "Created config.json (your personal settings; never uploaded)"
else
  ok "config.json already exists (kept)"
fi

read_cfg() { "$PY" -c "import json,sys; c=json.load(open('config.json')); print(eval(sys.argv[1]))" "$1"; }
UNI_KC="$(read_cfg "c['accounts'][0]['keychain']")"
GEM_KC="$(read_cfg "c.get('gemini_keychain','unimail-gemini')")"

# ---------------------------------------------------------------- 3. uni mail login
bold "Step 1/3 – your university email login"
echo "Tip: use exactly the username that works at your university's webmail (often NOT the email address)."
SERVER="$(read_cfg "c['accounts'][0]['imap_server']")"
echo "Mail server: $SERVER   (to change it, edit config.json and run setup again)"
if security find-generic-password -s "$UNI_KC" >/dev/null 2>&1; then
  read -r -p "  A uni login is already saved. Replace it? [y/N] " a
  [ "$a" = "y" ] || [ "$a" = "Y" ] && security delete-generic-password -s "$UNI_KC" >/dev/null && SAVE_UNI=1
else
  SAVE_UNI=1
fi
if [ -n "$SAVE_UNI" ]; then
  read -r -p "  Username: " UNI_USER
  echo "  Now type your password (twice). Nothing is shown while typing – that's normal."
  security add-generic-password -s "$UNI_KC" -a "$UNI_USER" -w
  ok "Saved in Keychain"
fi

# ---------------------------------------------------------------- 4. Gemini key
bold "Step 2/3 – your own Gemini API key (free)"
echo "  1. Open https://aistudio.google.com/apikey  and sign in with a Google account"
echo "  2. Click 'Create API key' and copy it"
if security find-generic-password -s "$GEM_KC" >/dev/null 2>&1; then
  read -r -p "  A Gemini key is already saved. Replace it? [y/N] " a
  [ "$a" = "y" ] || [ "$a" = "Y" ] && security delete-generic-password -s "$GEM_KC" >/dev/null && SAVE_GEM=1
else
  SAVE_GEM=1
fi
if [ -n "$SAVE_GEM" ]; then
  echo "  Paste the key (twice). Nothing is shown while pasting – that's normal."
  security add-generic-password -s "$GEM_KC" -a gemini -w
  ok "Saved in Keychain"
fi

# ---------------------------------------------------------------- 5. check
bold "Step 3/3 – checking everything"
echo "macOS will ask whether Terminal may use Reminders and Calendar: click OK / Allow."
"$PY" helper.py check | tee /tmp/unimail-check.$$
if grep -q "❌" /tmp/unimail-check.$$; then rm -f /tmp/unimail-check.$$; fail "Fix the ❌ line above, then run  bash setup.sh  again."; fi
rm -f /tmp/unimail-check.$$

# ---------------------------------------------------------------- 6. first sync + background + shortcut
bold "First check of your inbox (last $(read_cfg "c['first_sync_days']") days) – this can take a few minutes…"
"$PY" helper.py sync || true

bash service.sh on

LAUNCHER="$HOME/Desktop/Uni Mail Assistant.command"
printf '#!/bin/bash\ncd "%s" && exec "%s" app.py\n' "$DIR" "$PY" > "$LAUNCHER"
chmod +x "$LAUNCHER"
ok "Chat window shortcut on your Desktop: 'Uni Mail Assistant'"

bold "🎉 Done!"
echo "• Open the Reminders app on your iPhone: lists 'Uni – reminders', 'Uni – to confirm', 'Daily summary'"
echo "• It checks every 15 minutes while your Mac is awake."
echo "• Gmail / Matrix: see docs/ADD-MORE-ACCOUNTS.md"
echo "• Stop or remove everything: bash uninstall.sh"
