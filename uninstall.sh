#!/bin/bash
# Removes Uni Mail Assistant from this Mac: background service, saved logins (optional), local data (optional).
# Your emails, Reminders and Calendar entries are NOT touched.
cd "$(dirname "$0")"
PY="$(cat .python-path 2>/dev/null || command -v python3)"
read -r -p "Stop Uni Mail Assistant and remove it from this Mac? [y/N] " a
[ "$a" = "y" ] || [ "$a" = "Y" ] || exit 0
bash service.sh off
rm -f "$HOME/Desktop/Uni Mail Assistant.command"
"$PY" uninstall.py
