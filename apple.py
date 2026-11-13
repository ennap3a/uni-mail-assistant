"""Apple Reminders, Calendar and notifications (macOS only).
All values are passed to AppleScript as arguments, never pasted into the script code."""
import subprocess

def _start_hidden(script):
    """macOS sometimes refuses to start Calendar/Reminders from a script (error -600).
    Starting them hidden in the background first avoids that."""
    import time
    for app in ("Calendar", "Reminders"):
        if 'application "%s"' % app in script and \
                subprocess.run(["/usr/bin/pgrep", "-x", app], capture_output=True).returncode != 0:
            subprocess.run(["/usr/bin/open", "-g", "-j", "-a", app], capture_output=True)
            time.sleep(3)


def osa(script, *args):
    _start_hidden(script)
    for attempt in range(2):
        r = subprocess.run(["/usr/bin/osascript", "-", *[str(a) for a in args]],
                           input=script, capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            return r.stdout.strip()
        if "(-600)" not in r.stderr or attempt:
            break
        _start_hidden(script)  # app quit in between: start it again and retry once
    raise RuntimeError("AppleScript: " + r.stderr.strip())


MKDATE = """
on mkdate(y, mo, d, hh, mi)
    set t to current date
    set day of t to 1
    set year of t to (y as integer)
    set month of t to (mo as integer)
    set day of t to (d as integer)
    set hours of t to (hh as integer)
    set minutes of t to (mi as integer)
    set seconds of t to 0
    return t
end mkdate
"""


def add_reminder(list_name, title, notes, due=None, alarm=None, priority=0):
    """due/alarm: datetime or None. priority: 0 none, 1 high, 5 medium, 9 low (Apple's scale)."""
    d = due or alarm
    a = alarm
    args = [list_name, title, notes, priority,
            "1" if due else "0", *(d.strftime("%Y %m %d %H %M").split() if d else ["0"] * 5),
            "1" if a else "0", *(a.strftime("%Y %m %d %H %M").split() if a else ["0"] * 5)]
    return osa(MKDATE + """on run argv
    tell application "Reminders"
        set r to make new reminder at end of reminders of list (item 1 of argv) with properties {name:(item 2 of argv), body:(item 3 of argv), priority:((item 4 of argv) as integer)}
        if (item 5 of argv) is "1" then set due date of r to my mkdate(item 6 of argv, item 7 of argv, item 8 of argv, item 9 of argv, item 10 of argv)
        if (item 11 of argv) is "1" then set remind me date of r to my mkdate(item 12 of argv, item 13 of argv, item 14 of argv, item 15 of argv, item 16 of argv)
        return id of r
    end tell
end run""", *args)


def reminder_status(rid):
    return osa("""on run argv
    tell application "Reminders"
        try
            if completed of (reminder id (item 1 of argv)) then return "done"
            return "open"
        on error
            return "gone"
        end try
    end tell
end run""", rid)


def add_event(calendar, title, notes, day, time_, alerts):
    y, mo, d = day.split("-")
    hh, mi = (time_.split(":") if time_ else ("0", "0"))
    allday = "false" if time_ else "true"
    if not time_:
        alerts = [a - 9 * 60 for a in alerts]
    osa(MKDATE + """on run argv
    set s to my mkdate(item 3 of argv, item 4 of argv, item 5 of argv, item 6 of argv, item 7 of argv)
    if (item 8 of argv) is "true" then
        set e to s + (1 * days)
    else
        set e to s + (1 * hours)
    end if
    tell application "Calendar"
        tell calendar (item 1 of argv)
            set ev to make new event at end with properties {summary:(item 2 of argv), start date:s, end date:e, allday event:((item 8 of argv) is "true"), description:(item 9 of argv)}
            repeat with i from 10 to count of argv
                make new display alarm at end of display alarms of ev with properties {trigger interval:-((item i of argv) as integer)}
            end repeat
        end tell
    end tell
end run""", calendar, title, y, mo, d, hh, mi, allday, notes, *alerts)


def notify(title, text):
    try:
        osa('on run argv\n display notification (item 2 of argv) with title (item 1 of argv) sound name "Glass"\nend run',
            title, text[:200])
    except Exception:
        pass


def complete_reminder(rid):
    try:
        osa("""on run argv
    tell application "Reminders"
        set completed of (reminder id (item 1 of argv)) to true
    end tell
end run""", rid)
    except Exception:
        pass


def ensure(lists, calendars):
    for name in lists:
        osa("""on run argv
    tell application "Reminders"
        if not (exists list (item 1 of argv)) then make new list with properties {name:(item 1 of argv)}
    end tell
end run""", name)
    for name in calendars:
        osa("""on run argv
    tell application "Calendar"
        if not (exists calendar (item 1 of argv)) then make new calendar with properties {name:(item 1 of argv)}
    end tell
end run""", name)
