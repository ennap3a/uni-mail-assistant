#!/bin/bash
# Background service: checks your mail every 15 minutes whenever the Mac is awake.
#   bash service.sh on      -> start (also starts automatically after every login/restart)
#   bash service.sh off     -> stop
#   bash service.sh status  -> is it running? + last log lines
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(cat "$DIR/.python-path" 2>/dev/null || command -v python3)"
LABEL="local.unimail.assistant"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

case "$1" in
on)
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$DIR/helper.py</string><string>sync</string></array>
  <key>StartInterval</key><integer>900</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$DIR/service.log</string>
  <key>StandardErrorPath</key><string>$DIR/service.log</string>
</dict></plist>
EOF
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  launchctl bootstrap "$DOMAIN" "$PLIST"
  echo "  ✅ Running in the background: checks every 15 minutes while your Mac is awake."
  ;;
off)
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "  Stopped."
  ;;
status)
  launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 && echo "✅ Service is on." || echo "❌ Service is off."
  tail -n 5 "$DIR/activity.log" 2>/dev/null || true
  ;;
*) echo "Use: bash service.sh on | off | status" ;;
esac
