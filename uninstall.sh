#!/bin/bash
# Removes Uni Mail Assistant from this Mac: background service, saved logins, local data.
# Your emails, Reminders and Calendar entries are NOT touched.
cd "$(dirname "$0")"
PY="$(cat .python-path 2>/dev/null || command -v python3)"

echo "This will stop the background service and can delete your saved logins and local data."
read -r -p "Continue? [y/N] " a
[ "$a" = "y" ] || [ "$a" = "Y" ] || exit 0

bash service.sh off
rm -f "$HOME/Desktop/Uni Mail Assistant.command"

read -r -p "Delete saved passwords/keys from the Keychain? [y/N] " a
if [ "$a" = "y" ] || [ "$a" = "Y" ]; then
  if [ -f config.json ]; then
    for kc in $("$PY" -c "import json; c=json.load(open('config.json')); print(' '.join([a['keychain'] for a in c['accounts']] + [c.get('matrix',{}).get('keychain','unimail-matrix'), c.get('gemini_keychain','unimail-gemini')]))"); do
      security delete-generic-password -s "$kc" >/dev/null 2>&1 && echo "  removed $kc"
    done
  fi
fi

read -r -p "Delete local data (mail.db, logs, config.json)? [y/N] " a
if [ "$a" = "y" ] || [ "$a" = "Y" ]; then
  rm -f mail.db mail.db-* activity.log service.log config.json .python-path .sync.lock
  echo "  Local data deleted."
fi
echo "Done. You can now delete this folder."
