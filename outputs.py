"""Sends results to the outputs the user chose: Apple Reminders/Calendar (Mac) and/or Telegram (any phone)."""
import datetime as dt
import json
import time

import helper
import secrets_store
from telegram_bot import Bot, esc, link

CFG = helper.CFG
OUT = CFG.get("outputs", {"apple_reminders": True})
ICONS = {"exam": "📝", "deadline": "⏰", "payment": "💶", "appointment": "📅", "task": "✅"}
CAT_ICONS = {"uni_admin": "🏛", "course": "📚", "job": "💼", "money": "💶", "account_security": "🔐",
             "personal": "👤", "newsletter": "📰", "promotion": "🏷", "other": "📩"}


def use_apple():
    return secrets_store.IS_MAC and OUT.get("apple_reminders", False)


def use_telegram():
    return OUT.get("telegram", {}).get("enabled", False)


_bot = None


def bot():
    global _bot
    if _bot is None:
        tg = OUT["telegram"]
        _bot = Bot(secrets_store.get_secret(tg.get("keychain", "unimail-telegram")), tg.get("chat_id"))
    return _bot


def apple():
    import apple as a
    return a

# ------------------------------------------------------------------ formatting helpers

def pretty(day, time_=None):
    return dt.date.fromisoformat(day).strftime("%a %d %b %Y") + (" " + time_ if time_ else "")


def at(day, time_, default_hour=9):
    d = dt.date.fromisoformat(day)
    if time_:
        h, m = map(int, time_.split(":"))
        return dt.datetime.combine(d, dt.time(h, m))
    return dt.datetime.combine(d, dt.time(default_hour, 0))


def soon(minutes=2):
    return dt.datetime.now().replace(second=0, microsecond=0) + dt.timedelta(minutes=minutes)


def links_plain(links):
    if not links:
        return ""
    return "\n🔗 LINKS\n" + "\n".join(("%s:\n%s" % (l["label"], l["url"])) if l.get("label") else l["url"] for l in links)


def links_html(links):
    if not links:
        return ""
    return "\n🔗 " + "\n🔗 ".join(link(l["url"], l.get("label") or "Open link") for l in links)


def split_summary(s):
    if s and " || " in s:
        return s.split(" || ", 1)
    return None, s or ""


def ics(title, notes, day, time_, alerts):
    """A calendar file. Opening it on iPhone/Android/Windows/Mac adds the event with alerts."""
    def fold(s):
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    d = dt.date.fromisoformat(day)
    uid = "%s-%s@uni-mail-assistant" % (day, abs(hash(title)))
    if time_:
        start = at(day, time_)
        span = ["DTSTART:%s" % start.strftime("%Y%m%dT%H%M%S"),
                "DTEND:%s" % (start + dt.timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")]
    else:
        span = ["DTSTART;VALUE=DATE:%s" % d.strftime("%Y%m%d"),
                "DTEND;VALUE=DATE:%s" % (d + dt.timedelta(days=1)).strftime("%Y%m%d")]
        alerts = [a - 9 * 60 for a in alerts]  # all-day: ring at 9:00
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Uni Mail Assistant//EN", "BEGIN:VEVENT",
             "UID:" + uid, "DTSTAMP:" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"), *span,
             "SUMMARY:" + fold(title), "DESCRIPTION:" + fold(notes)]
    for a in alerts:
        trigger = "-PT%dM" % a if a >= 0 else "PT%dM" % -a
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + fold(title), "TRIGGER:" + trigger, "END:VALARM"]
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return ("\r\n".join(lines) + "\r\n").encode()

# ------------------------------------------------------------------ 1. important / useful emails

def email_alert(con, r):
    title, summary = split_summary(r["summary"])
    title = title or r["subject"][:80]
    high = r["importance"] == "high"
    links = json.loads(r["links"] or "[]")
    received = dt.datetime.fromisoformat(r["received"]).strftime("%a %d %b %Y, %H:%M")
    fresh = r["received"] >= (dt.datetime.now() - dt.timedelta(days=2)).isoformat()
    deadline_txt = pretty(r["deadline"][:10], r["deadline"][11:] or None) if r["deadline"] else None

    if use_apple():
        notes = ["📨 %s · %s <%s>" % (r["account"], r["sender"], r["sender_addr"]), "🕒 Received: " + received,
                 "✉️ Subject: " + r["subject"], "", summary]
        if r["action"]:
            notes += ["", "👉 TO DO: " + r["action"]]
        if deadline_txt:
            notes.append("⏳ Deadline: " + deadline_txt)
        if r["needs_reply"]:
            notes.append("↩️ This person is waiting for your reply.")
        notes.append(links_plain(links))
        due = alarm = None
        if r["deadline"] and r["deadline"][:10] >= dt.date.today().isoformat():
            due = at(r["deadline"][:10], r["deadline"][11:] or None)
        if high and fresh:
            alarm = soon()
        elif due:
            alarm = max(due - dt.timedelta(days=1), soon())
        lists = {a["name"]: a["reminders_list"] for a in CFG["accounts"]}
        lists["Matrix"] = CFG.get("matrix", {}).get("reminders_list", "Matrix – reminders")
        target = lists.get(r["account"].split(":")[0], CFG["accounts"][0]["reminders_list"])
        rid = apple().add_reminder(target, "%s%s %s" % ("❗️" if high else "", CAT_ICONS.get(r["category"], "📩"), title),
                                   "\n".join(notes), due, alarm, 1 if high else 5)
        con.execute("UPDATE emails SET reminder_id=? WHERE msg_id=?", (rid, r["msg_id"]))
        if high and fresh:
            apple().notify("Important: " + r["account"], "%s – %s" % (r["sender"], title))

    if use_telegram():
        msg = ["%s%s <b>%s</b>" % ("❗️" if high else "", CAT_ICONS.get(r["category"], "📩"), esc(title)),
               "📨 %s · %s" % (esc(r["account"]), esc(r["sender"])), "🕒 " + received, "", esc(summary)]
        if r["action"]:
            msg += ["", "👉 <b>To do:</b> " + esc(r["action"])]
        if deadline_txt:
            msg.append("⏳ <b>Deadline:</b> " + deadline_txt)
        if r["needs_reply"]:
            msg.append("↩️ Waiting for your reply")
        msg.append(links_html(links))
        bot().send("\n".join(msg), silent=not (high and fresh))
    con.execute("UPDATE emails SET notified=1 WHERE msg_id=?", (r["msg_id"],))
    con.commit()

# ------------------------------------------------------------------ 2. dates that need your OK

def suggest(con, row, kind, title, day, time_):
    links = json.loads(row["links"] or "[]")
    con.execute("INSERT INTO items (msg_id,kind,title,day,time,status,created) VALUES (?,?,?,?,?,?,?)",
                (row["msg_id"], kind, title, day, time_, "pending", dt.datetime.now().isoformat()))
    item_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    name = "%s %s – %s" % (ICONS[kind], title, pretty(day, time_))
    if use_apple():
        notes = "✓ Tick = add to your calendar (with alerts).   Delete = ignore.\n\n📨 %s · %s\nSubject: %s\nReceived: %s%s" % (
            row["account"], row["sender"], row["subject"], row["received"].replace("T", " "), links_plain(links))
        rid = apple().add_reminder(CFG["confirm_list"], name, notes)
        con.execute("UPDATE items SET reminder_id=? WHERE id=?", (rid, item_id))
    if use_telegram():
        text = "📌 <b>New date found</b>\n%s <b>%s</b>\n🗓 %s\n📨 %s · %s%s" % (
            ICONS[kind], esc(title), pretty(day, time_), esc(row["account"]), esc(row["sender"]), links_html(links[:2]))
        mid = bot().send(text, buttons=[[("✓ Add to calendar", "add:%d" % item_id), ("✗ Ignore", "ign:%d" % item_id)]])
        con.execute("UPDATE items SET tg_msg=? WHERE id=?", (mid, item_id))
    con.commit()
    helper.log("Suggested: " + name)


def approve(con, item_id):
    it = con.execute("SELECT i.*, e.sender, e.subject, e.account, e.links FROM items i LEFT JOIN emails e USING(msg_id) "
                     "WHERE id=?", (item_id,)).fetchone()
    if not it or it["status"] != "pending":
        return False
    title = "%s %s" % (ICONS.get(it["kind"], ""), it["title"])
    notes = "From: %s (%s)\nSubject: %s%s" % (it["sender"], it["account"], it["subject"], links_plain(json.loads(it["links"] or "[]")))
    alerts = CFG["alerts_minutes"].get(it["kind"], [1440])
    if use_apple():
        apple().add_event(CFG["calendars"].get(it["kind"], CFG["calendars"]["task"]), title, notes, it["day"], it["time"], alerts)
        if it["reminder_id"]:
            apple().complete_reminder(it["reminder_id"])
    if use_telegram():
        if it["tg_msg"]:
            bot().edit_buttons(it["tg_msg"], "✅ Added to calendar")
        if not use_apple():  # no Mac calendar -> send a calendar file to tap
            bot().send_file("%s.ics" % it["day"], ics(title, notes, it["day"], it["time"], alerts),
                            "📅 Tap this file to add it to your calendar (with alerts).")
    con.execute("UPDATE items SET status='added' WHERE id=?", (item_id,))
    con.commit()
    helper.log("Added to calendar: %s (%s)" % (it["title"], it["day"]))
    return True


def reject(con, item_id):
    it = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not it or it["status"] != "pending":
        return
    con.execute("UPDATE items SET status='rejected' WHERE id=?", (item_id,))
    con.commit()
    if use_telegram() and it["tg_msg"]:
        bot().edit_buttons(it["tg_msg"], "✗ Ignored")
    if use_apple() and it["reminder_id"]:
        try:
            apple().osa('on run argv\n tell application "Reminders" to delete (reminder id (item 1 of argv))\nend run',
                        it["reminder_id"])
        except Exception:
            pass


def check_apple_approvals(con):
    if not use_apple():
        return
    for it in con.execute("SELECT id, reminder_id FROM items WHERE status='pending' AND reminder_id IS NOT NULL").fetchall():
        st = apple().reminder_status(it["reminder_id"])
        if st == "done":
            approve(con, it["id"])
        elif st == "gone":
            reject(con, it["id"])

# ------------------------------------------------------------------ 3. replies, deadline nudges, summary, problems

def reply_reminder(con, r):
    _, summary = split_summary(r["summary"])
    if use_apple():
        acc = next((a for a in CFG["accounts"] if a["name"] == r["account"]), CFG["accounts"][0])
        apple().add_reminder(acc["reminders_list"], "↩️ Reply to %s: %s" % (r["sender"], r["subject"][:60]),
                             "📨 %s · %s <%s>\n🕒 Received: %s\n\n%s\n\nYou haven't replied yet." % (
                                 r["account"], r["sender"], r["sender_addr"], r["received"].replace("T", " "), summary),
                             None, soon(), 1)
    if use_telegram():
        bot().send("↩️ <b>You haven't replied yet</b>\n📨 %s · %s\n✉️ %s\n🕒 %s\n\n%s" % (
            esc(r["account"]), esc(r["sender"]), esc(r["subject"]), r["received"].replace("T", " "), esc(summary)))


def deadline_nudges(con):
    """Telegram has no alarms, so it sends a message 3 days and 1 day before each deadline."""
    if not use_telegram():
        return
    today = dt.date.today()
    rows = con.execute("SELECT * FROM emails WHERE deadline IS NOT NULL AND importance='high' AND substr(deadline,1,10) BETWEEN ? AND ?",
                       (today.isoformat(), (today + dt.timedelta(days=3)).isoformat())).fetchall()
    for r in rows:
        left = (dt.date.fromisoformat(r["deadline"][:10]) - today).days
        step = "1" if left <= 1 else "3"
        key = "nudge:%s:%s" % (r["msg_id"], step)
        if helper.get_state(con, key):
            continue
        title, _ = split_summary(r["summary"])
        when = "TODAY" if left == 0 else "tomorrow" if left == 1 else "in %d days" % left
        bot().send("⏳ <b>Deadline %s</b>: %s\n🗓 %s\n👉 %s%s" % (
            when, esc(title or r["subject"]), pretty(r["deadline"][:10], r["deadline"][11:] or None),
            esc(r["action"] or "see email"), links_html(json.loads(r["links"] or "[]")[:2])))
        helper.set_state(con, key, "sent")


def digest(con, title, lines_plain, lines_html):
    if use_apple():
        apple().add_reminder(CFG["digest_list"], title, "\n".join(lines_plain) or "Nothing new. 🎉", None, soon(), 0)
    if use_telegram():
        bot().send("<b>%s</b>\n\n%s" % (esc(title), "\n".join(lines_html) or "Nothing new. 🎉"), silent=True)


def problem(title, text):
    if use_apple():
        apple().notify(title, text)
    if use_telegram():
        try:
            bot().send("⚠️ <b>%s</b>\n%s" % (esc(title), esc(text)))
        except Exception:
            pass

# ------------------------------------------------------------------ 4. Telegram buttons and questions

HELP = ("🎓 <b>Uni Mail Assistant</b>\n"
        "I send you important emails and group messages, and dates to add to your calendar.\n\n"
        "Ask me anything about your mail, or use:\n"
        "/yesterday – everything from yesterday\n/today – today so far\n/week – the last 7 days\n"
        "/todo – what you must do + deadlines\n/help – this message")
COMMANDS = {"/yesterday": "What did I receive yesterday? Summarize all of it.",
            "/today": "What did I receive today?",
            "/week": "Summarize the last 7 days. What do I need to do?",
            "/todo": "What must I do and what are my upcoming deadlines? (last 30 days)"}


def handle_updates(con, wait=0):
    """Processes button taps and questions sent to the bot. Returns number of updates handled."""
    if not use_telegram():
        return 0
    b = bot()
    offset = helper.get_state(con, "tg_offset")
    ups = b.updates(int(offset) if offset else None, timeout=wait)
    for u in ups:
        helper.set_state(con, "tg_offset", str(u["update_id"] + 1))
        if not b.is_owner(u):
            continue  # someone else found the bot: ignore completely
        if "callback_query" in u:
            cq = u["callback_query"]
            action, _, item = (cq.get("data") or "").partition(":")
            if action == "add" and item.isdigit():
                b.answer_button(cq["id"], "Adding to calendar…")
                approve(con, int(item))
            elif action == "ign" and item.isdigit():
                b.answer_button(cq["id"], "Ignored")
                reject(con, int(item))
            else:
                b.answer_button(cq["id"])
            continue
        text = (u.get("message", {}).get("text") or "").strip()
        if not text:
            continue
        cmd = text.split()[0].split("@")[0].lower()
        if cmd in ("/start", "/help"):
            b.send(HELP)
            continue
        question = COMMANDS.get(cmd, text)
        b.send("🔎 Reading your messages…", silent=True)
        try:
            import qa
            b.send(esc(qa.answer(question)))
        except Exception as e:
            b.send("⚠️ " + esc(str(e)[:300]))
    return len(ups)


def listen():
    """Runs all the time (started by the service) so buttons and questions get answered within seconds."""
    helper.log("Telegram listener started.")
    while True:
        try:
            con = helper.db()
            handle_updates(con, wait=50)
            con.close()
        except Exception as e:
            helper.log("Telegram listener: %s" % e)
            time.sleep(30)
