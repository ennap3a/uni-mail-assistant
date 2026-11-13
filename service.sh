#!/bin/bash
# Background service (macOS).
#   bash service.sh on      -> check mail every 15 min while the Mac is awake (+ Telegram listener if Telegram is on)
#   bash service.sh off     -> stop
#   bash service.sh status  -> is it running? + last log lines
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(cat "$DIR/.python-path" 2>/dev/null || command -v python3)"
DOMAIN="gui/$(id -u)"
AGENTS="$HOME/Library/LaunchAgents"
SYNC="local.unimail.assistant"
LISTEN="local.unimail.telegram"

write_plist() { # label, args, extra keys
  cat > "$AGENTS/$1.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$1</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$DIR/helper.py</string><string>$2</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  $3
  <key>StandardOutPath</key><string>$DIR/service.log</string>
  <key>StandardErrorPath</key><string>$DIR/service.log</string>
</dict></plist>
EOF
  launchctl bootout "$DOMAIN/$1" 2>/dev/null || true
  launchctl bootstrap "$DOMAIN" "$AGENTS/$1.plist"
}

telegram_on() {
  "$PY" -c "import json,sys; c=json.load(open('$DIR/config.json')); t=c.get('outputs',{}).get('telegram',{}); sys.exit(0 if t.get('enabled') and t.get('listen',True) else 1)" 2>/dev/null
}

case "$1" in
on)
  mkdir -p "$AGENTS"
  write_plist "$SYNC" sync "<key>StartInterval</key><integer>900</integer><key>RunAtLoad</key><true/>"
  echo "  ✅ Checks every 15 minutes while your Mac is awake."
  if telegram_on; then
    write_plist "$LISTEN" listen "<key>KeepAlive</key><true/><key>RunAtLoad</key><true/>"
    echo "  ✅ Telegram: buttons and questions are answered right away."
  else
    launchctl bootout "$DOMAIN/$LISTEN" 2>/dev/null || true; rm -f "$AGENTS/$LISTEN.plist"
  fi
  ;;
off)
  for l in "$SYNC" "$LISTEN"; do launchctl bootout "$DOMAIN/$l" 2>/dev/null || true; rm -f "$AGENTS/$l.plist"; done
  echo "  Stopped."
  ;;
status)
  launchctl print "$DOMAIN/$SYNC" >/dev/null 2>&1 && echo "✅ Mail checking is on." || echo "❌ Mail checking is off."
  telegram_on && { launchctl print "$DOMAIN/$LISTEN" >/dev/null 2>&1 && echo "✅ Telegram listener is on." || echo "❌ Telegram listener is off."; }
  tail -n 5 "$DIR/activity.log" 2>/dev/null || true
  ;;
*) echo "Use: bash service.sh on | off | status" ;;
esac
