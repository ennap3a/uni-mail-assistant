#!/usr/bin/env python3
"""Uni Mail Assistant – background engine (macOS, Windows, Linux).

  python helper.py check    -> test logins, Gemini and your outputs
  python helper.py sync     -> fetch + analyse new mail/messages and send results (the service runs this every 15 min)
  python helper.py listen   -> Telegram: answer buttons and questions right away (the service keeps this running)
  python helper.py status   -> show what is stored

Rules: mail is read-only; only real messages are stored; bank numbers, amounts, IDs, PINs and links are
removed before anything is stored or sent to Gemini.
"""
import datetime as dt
import email
import email.header
import email.utils
import html
import imaplib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

import secrets_store

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
DB_PATH = os.path.join(HERE, "mail.db")
LOG_PATH = os.path.join(HERE, "activity.log")
LOCK_PATH = os.path.join(HERE, ".sync.lock")

if not os.path.exists(CONFIG_PATH):
    sys.exit("No config.json yet. Run the setup first (Mac: bash setup.sh · Windows: double-click setup.bat).")
with open(CONFIG_PATH, encoding="utf-8") as _f:
    CFG = json.load(_f)


def log(msg):
    line = "%s  %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def accounts():
    return [a for a in CFG["accounts"] if a.get("enabled", True)]

# ------------------------------------------------------------------ database

def db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript("""
    CREATE TABLE IF NOT EXISTS emails (
        msg_id TEXT PRIMARY KEY, received TEXT, sender TEXT, sender_addr TEXT, subject TEXT,
        body TEXT, category TEXT, importance TEXT, summary TEXT, action TEXT,
        needs_reply INTEGER DEFAULT 0, replied INTEGER DEFAULT 0, reply_reminded INTEGER DEFAULT 0,
        analysed INTEGER DEFAULT 0, notified INTEGER DEFAULT 0, error TEXT);
    CREATE INDEX IF NOT EXISTS idx_received ON emails(received);
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY, msg_id TEXT, kind TEXT, title TEXT, day TEXT, time TEXT,
        status TEXT, reminder_id TEXT, created TEXT, UNIQUE(kind, title, day));
    CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);
    """)
    for table, col in (("emails", "account TEXT DEFAULT 'Uni'"), ("emails", "links TEXT"), ("emails", "deadline TEXT"),
                       ("emails", "reminder_id TEXT"), ("items", "tg_msg INTEGER")):
        try:
            con.execute("ALTER TABLE %s ADD COLUMN %s" % (table, col))
        except sqlite3.OperationalError:
            pass
    return con


def get_state(con, key):
    r = con.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return r[0] if r else None


def set_state(con, key, value):
    con.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (key, value))
    con.commit()

# ------------------------------------------------------------------ privacy filter

REDACTIONS = [
    (re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,4})?\b"), "[HIDDEN-IBAN]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[HIDDEN-NUMBER]"),
    (re.compile(r"(?:€|EUR)\s?\d[\d.,]*|\d[\d.,]*\s?(?:€|(?:EUR|Euro)\b)", re.I), "[HIDDEN-AMOUNT]"),
    (re.compile(r"\b\d{6,9}\b"), "[HIDDEN-ID]"),
    (re.compile(r"(?i)\b(passwor[td]|kennwort|pin|tan|code)\s*[:=]\s*\S+"), r"\1: [HIDDEN]"),
]
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")


def redact(text):
    text = URL_RE.sub("[link]", text or "")  # links never go to the AI
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text

# ------------------------------------------------------------------ mail

def decode(value):
    out = []
    for text, enc in email.header.decode_header(value or ""):
        if isinstance(text, bytes):
            try:
                text = text.decode(enc or "utf-8", errors="replace")
            except LookupError:
                text = text.decode("utf-8", errors="replace")
        out.append(text)
    return re.sub(r"\s+", " ", "".join(out)).strip()


SKIP_LINK = re.compile(r"unsubscribe|abmelden|abbestellen|optout|opt-out|/track|click\.|pixel|\.png|\.jpg|\.gif|"
                       r"mailto:|facebook\.com|instagram\.com|twitter\.com|x\.com/|linkedin\.com/(?:company|shareArticle)|"
                       r"youtube\.com|privacy|datenschutz|impressum|imprint", re.I)


def parts(msg):
    plain = htm = None
    for part in msg.walk():
        if part.get_content_maintype() == "multipart" or part.get_filename():
            continue
        try:
            payload = part.get_payload(decode=True)
            text = payload.decode(part.get_content_charset() or "utf-8", errors="replace") if payload else ""
        except (LookupError, AttributeError):
            continue
        if part.get_content_type() == "text/plain" and plain is None:
            plain = text
        elif part.get_content_type() == "text/html" and htm is None:
            htm = text
    return plain, htm


def extract_links(plain, htm, limit=6):
    """Useful links (with their label when available). Tracking/unsubscribe/social links are dropped."""
    found = []
    if htm:
        for href, label in re.findall(r'(?is)<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', htm):
            label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", label))).strip()
            found.append((html.unescape(href), label))
    for u in URL_RE.findall(plain or ""):
        found.append((u, ""))
    out, seen = [], set()
    for url, label in found:
        url = url.rstrip(".,;")
        if not url.startswith("http") or SKIP_LINK.search(url) or SKIP_LINK.search(label or "") or url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "label": label[:60]})
        if len(out) >= limit:
            break
    return out


def body_text(plain, htm):
    if not plain and htm:
        h = re.sub(r"(?is)<(script|style).*?</\1>", " ", htm)
        h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", h)
        plain = html.unescape(re.sub(r"<[^>]+>", " ", h))
    text = re.split(r"\n(?:>|Am .{5,80} schrieb|On .{5,80} wrote)", plain or "")[0]
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()[:5000]


def imap_connect(acc):
    user, pw = secrets_store.get_login(acc["keychain"])
    m = imaplib.IMAP4_SSL(acc["imap_server"], acc.get("imap_port", 993), timeout=60)
    try:
        m.login(user, pw)
    except imaplib.IMAP4.error:
        raise RuntimeError("%s: login was rejected. Check the username/password (README)." % acc["name"])
    return m


def sent_folder(m):
    names = []
    for raw in m.list()[1] or []:
        line = raw.decode(errors="replace")
        name = line.rsplit(' "', 1)[-1].rstrip('"') if line.endswith('"') else line.split()[-1]
        if "\\Sent" in line:
            return name
        names.append(name)
    for guess in ("Sent", "INBOX.Sent", "Gesendet", "INBOX.Gesendet", "Sent Items", "Gesendete Objekte"):
        if guess in names:
            return guess
    return None


def fetch(m, folder, since_days, known=None, headers_only=None):
    """Yields messages since N days. Downloads only small headers first; full emails only
    for messages whose Message-ID is not in `known`. headers_only='IN-REPLY-TO REFERENCES' etc. = never full."""
    typ, _ = m.select('"%s"' % folder, readonly=True)
    if typ != "OK":
        return
    since = (dt.date.today() - dt.timedelta(days=since_days)).strftime("%d-%b-%Y")
    typ, data = m.search(None, "SINCE", since)
    nums = data[0].split() if typ == "OK" and data[0] else []
    if not nums:
        return
    fields = headers_only or "MESSAGE-ID"
    typ, hdrs = m.fetch(b",".join(nums), "(BODY.PEEK[HEADER.FIELDS (%s)])" % fields)
    heads = [email.message_from_bytes(h[1]) for h in hdrs or [] if isinstance(h, tuple)]
    if headers_only:
        yield from heads
        return
    for num, h in zip(nums, heads):
        if known is not None and (h.get("Message-ID") or "").strip() in known:
            continue
        typ, msgdata = m.fetch(num, "(BODY.PEEK[])")
        if typ == "OK" and msgdata and isinstance(msgdata[0], tuple):
            yield email.message_from_bytes(msgdata[0][1])


def received_time(msg):
    try:
        return email.utils.parsedate_to_datetime(msg.get("Date")).astimezone().replace(tzinfo=None)
    except Exception:
        return dt.datetime.now()

# ------------------------------------------------------------------ Gemini

class QuotaError(RuntimeError):
    """Free Gemini limit reached. Unanalysed mail simply waits for the next run."""


def gemini(prompt, want_json=True):
    key = secrets_store.get_secret(CFG.get("gemini_keychain", "unimail-gemini"))
    last = None
    quota_hits = 0
    for model in CFG["gemini_models"]:
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model
        gcfg = {"temperature": 0}
        if want_json:
            gcfg["responseMimeType"] = "application/json"
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gcfg}).encode()
        for attempt in range(2):
            req = urllib.request.Request(url, data=body, method="POST",
                                         headers={"Content-Type": "application/json", "x-goog-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    resp = json.load(r)
                text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
                if not want_json:
                    return text
                return json.loads(re.sub(r"^```(?:json)?|```$", "", text).strip())
            except urllib.error.HTTPError as e:
                last = "%s: HTTP %s %s" % (model, e.code, e.read().decode(errors="replace")[:200])
                if e.code in (400, 401, 403):
                    raise RuntimeError("Gemini rejected the request: " + last)
                if e.code == 404:
                    break
                if e.code == 429:  # limit of this model reached -> try the next model
                    quota_hits += 1
                    break
            except Exception as e:
                last = "%s: %s" % (model, e)
            time.sleep(5 * (attempt + 1))
    if quota_hits == len(CFG["gemini_models"]):
        raise QuotaError("Free Gemini limit reached for now (%s)" % last)
    raise RuntimeError("Gemini not reachable (%s)" % last)


ANALYSE_PROMPT = """You sort messages for a university student at """ + CFG.get("university", "a university") + """ who rarely
checks email and must not miss anything important. Today is {today} ({weekday}).
The message was received {received} in the student's "{account}" inbox. Answer ONLY with JSON:
{{
 "category": one of "uni_admin" (Studienbüro, Prüfungsamt, Rückmeldung, enrolment, fees, official uni, IT/URZ rules),
             "course" (lectures, exercises, Moodle/LSF, lecturers, labs, exams of a course),
             "job" (applications, employers, internships, HiWi),
             "money" (bills, payments, grants, Stadt/Amt, bank, BAföG),
             "account_security" (logins, new apps on account, password resets),
             "personal" (a real person writing to the student),
             "newsletter" (mailing lists, StuRa newsletter, studierende-l),
             "promotion" (ads, deals, marketing),
             "other",
 "importance": "high" (student must act or decide, has a deadline, a reply from an employer/authority/lecturer,
                       or a security alert),
               "medium" (useful to know, no action needed),
               "low" (ads, routine notifications, newsletters without anything relevant for the student),
 "title": "short reminder title, max 70 chars, says what it is about (e.g. 'Register for exams in LSF')",
 "summary": "2-3 sentences in English with ALL concrete details: what, who, where, when, how.",
 "action": "exactly what the student must do (and where/how), or null",
 "deadline": "YYYY-MM-DD of the most important deadline/date for the student, or null",
 "deadline_time": "HH:MM or null",
 "needs_reply": true only if a real person expects an answer,
 "dates": [{{"kind": "exam|deadline|payment|appointment|task", "title": "max 60 chars",
            "date": "YYYY-MM-DD", "time": "HH:MM or null"}}]   (only concrete FUTURE dates the student must act on/attend)
}}
Resolve relative dates ("next Monday", "bis Freitag") using the received date.
Numbers shown as [HIDDEN-...] and links shown as [link] were removed for privacy.

From: {sender}
Subject: {subject}
Text:
{body}"""


_SCHEMA = ANALYSE_PROMPT[ANALYSE_PROMPT.index("{{\n"):ANALYSE_PROMPT.index("\n}}") + 3]

BATCH_PROMPT = """You sort messages for a university student at """ + CFG.get("university", "a university") + """ who rarely
checks email and must not miss anything important. Today is {today} ({weekday}).
Below are {n} separate messages, each starting with ### MESSAGE <number>.
Judge EACH message on its own. Answer ONLY with JSON: {{"results": [ one object per message ]}}
Each object has "n" (the message number) plus these fields:
""" + _SCHEMA + """
Resolve relative dates ("next Monday", "bis Freitag") using each message's received date.
Numbers shown as [HIDDEN-...] and links shown as [link] were removed for privacy.

{messages}"""


def analyse_batch(rows):
    """One Gemini request for several emails -> {msg_id: analysis}."""
    per_mail = max(1200, 24000 // len(rows))
    blocks = []
    for i, r in enumerate(rows, 1):
        rec = dt.datetime.fromisoformat(r["received"])
        blocks.append("### MESSAGE %d\nInbox: %s\nReceived: %s\nFrom: %s <%s>\nSubject: %s\nText:\n%s" % (
            i, r["account"], rec.strftime("%A %Y-%m-%d %H:%M"), r["sender"], r["sender_addr"],
            redact(r["subject"]), (r["body"] or "")[:per_mail]))
    res = gemini(BATCH_PROMPT.format(today=dt.date.today().isoformat(), weekday=dt.date.today().strftime("%A"),
                                     n=len(rows), messages="\n\n".join(blocks)))
    out = {}
    for item in (res.get("results") if isinstance(res, dict) else res) or []:
        try:
            out[rows[int(item["n"]) - 1]["msg_id"]] = item
        except (KeyError, ValueError, IndexError, TypeError):
            continue
    return out


# ------------------------------------------------------------------ small helpers

def pretty(day, time_=None):
    return dt.date.fromisoformat(day).strftime("%a %d %b %Y") + (" " + time_ if time_ else "")


class Lock:
    """Makes sure only one sync runs at a time (works on Mac, Windows and Linux)."""
    def __init__(self, path):
        self.f = open(path, "a+")

    def acquire(self):
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

# ------------------------------------------------------------------ sync steps

def download_new(con, acc, m):
    key = "first_sync:" + acc["name"]
    days = CFG["first_sync_days"] if get_state(con, key) is None else CFG["resync_days"]
    known = {r[0] for r in con.execute("SELECT msg_id FROM emails")}
    new = 0
    for msg in fetch(m, "INBOX", days, known=known):
        rec = received_time(msg)
        mid = (msg.get("Message-ID") or "").strip() or "%s|%s" % (rec.isoformat(), decode(msg.get("Subject")))
        if mid in known:
            continue
        plain, htm = parts(msg)
        name, addr = email.utils.parseaddr(decode(msg.get("From")))
        con.execute("INSERT OR IGNORE INTO emails (msg_id, account, received, sender, sender_addr, subject, body, links) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (mid, acc["name"], rec.isoformat(timespec="minutes"), name or addr, addr.lower(),
                     decode(msg.get("Subject")), redact(body_text(plain, htm)), json.dumps(extract_links(plain, htm))))
        known.add(mid)
        new += 1
    con.commit()
    set_state(con, key, "done")
    return new


def analyse_pending(con):
    """Newest mail first, several emails per Gemini request (fast, and uses little of the free limit)."""
    import outputs
    rows = con.execute("SELECT * FROM emails WHERE analysed=0 ORDER BY received DESC").fetchall()
    todo = []
    for row in rows:
        if any(s in (row["sender_addr"] or "") for s in CFG.get("skip_ai_for_senders", [])):
            con.execute("UPDATE emails SET analysed=1, category='promotion', importance='low', "
                        "summary='Advertising (not sent to AI).' WHERE msg_id=?", (row["msg_id"],))
        else:
            todo.append(row)
    con.commit()
    size = CFG.get("batch_size", 10)
    done = 0
    for start in range(0, len(todo), size):
        batch = todo[start:start + size]
        try:
            results = analyse_batch(batch)
        except QuotaError as e:
            log("%s – %d email(s) wait for the next run." % (e, len(todo) - done))
            if get_state(con, "quota_note") != dt.date.today().isoformat():
                outputs.problem("Gemini free limit reached", "Remaining emails will be analysed automatically later.")
                set_state(con, "quota_note", dt.date.today().isoformat())
            break
        except Exception as e:
            log("Could not analyse %d email(s) yet: %s" % (len(todo) - done, e))
            if "rejected" in str(e):
                raise
            break  # e.g. no internet: try again next run
        for row in batch:
            if row["msg_id"] in results:
                save_analysis(con, row, results[row["msg_id"]])
                done += 1
        log("Analysed %d/%d" % (done, len(todo)))
    return done


def save_analysis(con, row, a):
    deadline = a.get("deadline") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(a.get("deadline"))) else None
    if deadline and re.fullmatch(r"\d{1,2}:\d{2}", str(a.get("deadline_time") or "")):
        deadline += "T" + a["deadline_time"]
    title = (a.get("title") or "").strip()
    con.execute("""UPDATE emails SET analysed=1, error=NULL, category=?, importance=?, summary=?, action=?,
                   needs_reply=?, deadline=? WHERE msg_id=?""",
                (a.get("category", "other"), a.get("importance", "medium"),
                 (title + " || " if title else "") + (a.get("summary") or ""),
                 a.get("action"), 1 if a.get("needs_reply") else 0, deadline, row["msg_id"]))
    con.commit()
    suggest_dates(con, row, a.get("dates") or [])


DATE_KINDS = ("exam", "deadline", "payment", "appointment", "task")


def suggest_dates(con, row, dates):
    import outputs
    today = dt.date.today()
    for it in dates:
        kind = it.get("kind") if it.get("kind") in DATE_KINDS else "task"
        try:
            day = dt.date.fromisoformat(str(it.get("date")))
        except ValueError:
            continue
        if day < today:
            continue
        t = it.get("time") if re.fullmatch(r"\d{1,2}:\d{2}", str(it.get("time") or "")) else None
        title = (it.get("title") or row["subject"])[:80]
        # same kind of thing on the same day/time = same event (e.g. German + English copy of one email)
        if con.execute("SELECT 1 FROM items WHERE kind=? AND day=? AND IFNULL(time,'')=IFNULL(?,'') "
                       "AND status IN ('pending','added')", (kind, day.isoformat(), t)).fetchone() or \
           con.execute("SELECT 1 FROM items WHERE kind=? AND title=? AND day=?", (kind, title, day.isoformat())).fetchone():
            continue
        outputs.suggest(con, row, kind, title, day.isoformat(), t)


def send_alerts(con):
    """Every important/useful message is sent once, with all details and links."""
    import outputs
    wanted = CFG.get("remind_for_importance", ["high", "medium"])
    since = (dt.datetime.now() - dt.timedelta(days=CFG["first_sync_days"])).isoformat()
    rows = con.execute("SELECT * FROM emails WHERE analysed=1 AND notified=0 AND received>=? ORDER BY received",
                       (since,)).fetchall()
    for r in rows:
        if r["importance"] in wanted:
            outputs.email_alert(con, r)
            log("Sent: %s" % r["subject"][:70])
        else:
            con.execute("UPDATE emails SET notified=1 WHERE msg_id=?", (r["msg_id"],))
    con.commit()


def check_replies(con, acc, m):
    import outputs
    waiting = con.execute("SELECT * FROM emails WHERE account=? AND needs_reply=1 AND replied=0 AND reply_reminded=0",
                          (acc["name"],)).fetchall()
    if not waiting:
        return
    folder = sent_folder(m)
    answered = set()
    if folder:
        for msg in fetch(m, folder, 30, headers_only="IN-REPLY-TO REFERENCES"):
            for h in ("In-Reply-To", "References"):
                answered.update(re.findall(r"<[^>]+>", msg.get(h) or ""))
    limit = dt.timedelta(days=CFG["reply_reminder_after_days"])
    for r in waiting:
        if r["msg_id"] in answered:
            con.execute("UPDATE emails SET replied=1 WHERE msg_id=?", (r["msg_id"],))
        elif dt.datetime.now() - dt.datetime.fromisoformat(r["received"]) > limit:
            outputs.reply_reminder(con, r)
            con.execute("UPDATE emails SET reply_reminded=1 WHERE msg_id=?", (r["msg_id"],))
            log("Reply reminder: " + r["subject"][:60])
    con.commit()


def daily_digest(con):
    """Every morning: everything since yesterday (incl. unimportant mail), your week, and what waits for your OK."""
    import outputs
    from telegram_bot import esc
    now = dt.datetime.now()
    today = now.date().isoformat()
    if now.hour < CFG["digest_hour"] or get_state(con, "digest") == today:
        return
    since = (now - dt.timedelta(days=1)).replace(hour=0, minute=0).isoformat()
    rows = con.execute("SELECT * FROM emails WHERE received>=? ORDER BY received", (since,)).fetchall()
    waiting = con.execute("SELECT kind,title,day,time FROM items WHERE status='pending' ORDER BY day").fetchall()
    upcoming = con.execute("SELECT kind,title,day,time FROM items WHERE status='added' AND day BETWEEN ? AND ? ORDER BY day",
                           (today, (now.date() + dt.timedelta(days=7)).isoformat())).fetchall()
    plain, rich = [], []
    for label, imp in (("❗️ IMPORTANT", "high"), ("ℹ️ GOOD TO KNOW", "medium"), ("💤 NOT IMPORTANT", "low")):
        sel = [r for r in rows if r["importance"] == imp]
        if sel:
            plain.append("%s (%d)" % (label, len(sel)))
            rich.append("<b>%s (%d)</b>" % (label, len(sel)))
            for r in sel:
                t, _ = outputs.split_summary(r["summary"])
                line = "• [%s] %s – %s" % (r["account"], r["sender"], t or r["subject"])
                plain.append(line)
                rich.append(esc(line))
            plain.append("")
            rich.append("")
    for label, items in (("🗓 IN YOUR CALENDAR THIS WEEK", upcoming), ("⏳ WAITING FOR YOUR OK", waiting)):
        if items:
            plain.append(label)
            rich.append("<b>%s</b>" % label)
            for i in items:
                line = "• %s %s – %s" % (outputs.ICONS.get(i["kind"], ""), i["title"], pretty(i["day"], i["time"]))
                plain.append(line)
                rich.append(esc(line))
            plain.append("")
            rich.append("")
    hi = sum(r["importance"] == "high" for r in rows)
    outputs.digest(con, "☀️ %s: %d new, %d important" % (now.strftime("%a %d %b"), len(rows), hi), plain, rich)
    set_state(con, "digest", today)


def sync():
    import outputs
    lock = Lock(LOCK_PATH)
    if not lock.acquire():
        log("Sync already running.")
        return
    con = db()
    outputs.check_apple_approvals(con)
    if outputs.use_telegram() and not outputs.OUT["telegram"].get("listen", True):
        outputs.handle_updates(con)  # no listener running: handle buttons/questions now
    total, errors = 0, []
    for acc in accounts():
        try:
            m = imap_connect(acc)
            try:
                total += download_new(con, acc, m)
                check_replies(con, acc, m)
            finally:
                try:
                    m.logout()
                except Exception:
                    pass
        except secrets_store.MissingSecret:
            log("Skipping %s: not set up yet." % acc["name"])
        except Exception as e:
            errors.append("%s: %s" % (acc["name"], e))
            log("ERROR %s: %s" % (acc["name"], e))
    analysed = analyse_pending(con)
    if CFG.get("matrix", {}).get("enabled"):
        try:
            import matrix
            matrix.sync(con)
        except Exception as e:
            errors.append("Matrix: %s" % e)
            log("ERROR Matrix: %s" % e)
    send_alerts(con)
    outputs.deadline_nudges(con)
    daily_digest(con)
    set_state(con, "last_sync", dt.datetime.now().isoformat(timespec="minutes"))
    log("Sync done: %d new message(s), %d analysed." % (total, analysed))
    if errors:
        raise RuntimeError("; ".join(errors))


def status():
    con = db()
    print("Last sync:", get_state(con, "last_sync"))
    for r in con.execute("SELECT account, substr(received,1,10) day, COUNT(*) n, SUM(importance='high') hi, "
                         "SUM(analysed=0) todo FROM emails GROUP BY account, day ORDER BY day DESC LIMIT 20"):
        print("  %-12s %s  %3d messages  (%d important, %d not analysed yet)" % (
            r["account"][:12], r["day"], r["n"], r["hi"] or 0, r["todo"] or 0))


def check():
    import outputs
    ok = True

    def step(name, fn):
        nonlocal ok
        try:
            fn()
            print("  ✅", name)
        except QuotaError:
            print("  ⚠️  %s → key works, but today's free Gemini limit is used up. Mail is analysed later automatically." % name)
        except Exception as e:
            ok = False
            print("  ❌ %s → %s" % (name, str(e)[:300]))

    print("Checking:")
    for acc in accounts():
        step("%s: login works" % acc["name"], lambda acc=acc: imap_connect(acc).logout())
    step("Gemini answers", lambda: gemini('Reply with JSON {"ok": true}'))
    if outputs.use_apple():
        lists = {CFG["confirm_list"], CFG["digest_list"]} | {a["reminders_list"] for a in accounts()}
        if CFG.get("matrix", {}).get("enabled"):
            lists.add(CFG["matrix"]["reminders_list"])
        step("Apple Reminders + Calendar", lambda: outputs.apple().ensure(sorted(lists), sorted(set(CFG["calendars"].values()))))
    if outputs.use_telegram():
        step("Telegram bot", lambda: outputs.bot().me())
    if CFG.get("matrix", {}).get("enabled"):
        import matrix
        step("Matrix login works", matrix.whoami)
    if not outputs.use_apple() and not outputs.use_telegram():
        ok = False
        print("  ❌ No output chosen: turn on Apple Reminders (Mac) or Telegram (run setup again).")
    print("\nAll good." if ok else "\nFix the ❌ lines (see README), then run check again.")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if cmd == "check":
        sys.exit(0 if check() else 1)
    elif cmd == "status":
        status()
    elif cmd == "listen":
        import outputs
        outputs.listen()
    elif cmd == "sync":
        try:
            sync()
        except Exception as e:
            log("ERROR: %s" % e)
            try:
                import outputs
                outputs.problem("Uni Mail Assistant problem", str(e))
            except Exception:
                pass
            sys.exit(1)
    else:
        print(__doc__)
