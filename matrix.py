"""Matrix / Element groups -> the same reminders as your email.

Reads new messages in the rooms you joined (read-only; it never posts anything),
asks Gemini what matters for you, and stores those as items, so they become iPhone
reminders, appear in the morning summary and in the chat window.
Note: end-to-end ENCRYPTED rooms cannot be read by this program (only unencrypted ones).
"""
import datetime as dt
import json
import re
import urllib.parse
import urllib.request

import helper

MCFG = helper.CFG.get("matrix", {})


def token():
    import secrets_store
    return secrets_store.get_secret(MCFG.get("keychain", "unimail-matrix"))


def base_url(con):
    cached = helper.get_state(con, "matrix_base")
    if cached:
        return cached
    server = MCFG["server"].replace("https://", "").replace("http://", "").strip("/")
    base = "https://" + server
    try:
        with urllib.request.urlopen(base + "/.well-known/matrix/client", timeout=20) as r:
            base = json.load(r)["m.homeserver"]["base_url"].rstrip("/")
    except Exception:
        pass
    helper.set_state(con, "matrix_base", base)
    return base


def api(con, path, params=None):
    url = base_url(con) + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token()})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except Exception as e:
        import net
        if net.is_cert_error(e):
            raise RuntimeError("Matrix: " + net.CERT_HELP)
        raise


def whoami(con=None):
    con = con or helper.db()
    return api(con, "/_matrix/client/v3/account/whoami")["user_id"]


def room_name(con, room_id, state_events):
    for ev in state_events:
        if ev.get("type") == "m.room.name" and ev.get("content", {}).get("name"):
            helper.set_state(con, "room:" + room_id, ev["content"]["name"])
    name = helper.get_state(con, "room:" + room_id)
    if not name:
        try:
            name = api(con, "/_matrix/client/v3/rooms/%s/state/m.room.name" % urllib.parse.quote(room_id))["name"]
        except Exception:
            name = room_id
        helper.set_state(con, "room:" + room_id, name)
    return name


PROMPT = """You help a university student at """ + helper.CFG.get("university", "a university") + """ who rarely reads the group chat "{room}".
Today is {today}. The student's Matrix user is {me}. Below are NEW messages from that group.
Find only what matters to the student: announcements, deadlines, dates, events, tasks, changes,
questions addressed to the student, and anything that mentions them. Ignore small talk.
Answer ONLY with JSON: {{"items": [{{
  "importance": "high" (must act / deadline / addressed to student) or "medium" (good to know),
  "title": "max 70 chars",
  "summary": "2-3 sentences with all concrete details (what, when, where, who)",
  "action": "what the student must do, or null",
  "deadline": "YYYY-MM-DD or null", "deadline_time": "HH:MM or null",
  "dates": [{{"kind": "exam|deadline|payment|appointment|task", "title": "max 60 chars", "date": "YYYY-MM-DD", "time": "HH:MM or null"}}],
  "message_numbers": [numbers of the messages this is based on]
}}]}}
Return {{"items": []}} if nothing matters. Links appear as [link]; numbers as [HIDDEN-...] were removed.

MESSAGES:
{messages}"""


def sync(con):
    me = whoami(con)
    since = helper.get_state(con, "matrix_since")
    params = {"timeout": "0", "filter": json.dumps({"room": {"timeline": {"limit": 100}}})}
    if since:
        params["since"] = since
    data = api(con, "/_matrix/client/v3/sync", params)
    cutoff = dt.datetime.now() - dt.timedelta(days=helper.CFG["first_sync_days"])
    skipped_encrypted = 0
    for room_id, room in (data.get("rooms", {}).get("join") or {}).items():
        name = room_name(con, room_id, room.get("state", {}).get("events", []) + room.get("timeline", {}).get("events", []))
        if MCFG.get("rooms") and name not in MCFG["rooms"] and room_id not in MCFG["rooms"]:
            continue
        msgs = []
        for ev in room.get("timeline", {}).get("events", []):
            when = dt.datetime.fromtimestamp(ev.get("origin_server_ts", 0) / 1000)
            if ev.get("type") == "m.room.encrypted":
                skipped_encrypted += 1
            if ev.get("type") != "m.room.message" or when < cutoff or ev.get("sender") == me:
                continue
            body = ev.get("content", {}).get("body", "")
            if body:
                msgs.append({"id": ev["event_id"], "sender": ev["sender"], "when": when, "body": body})
        if not msgs:
            continue
        text = "\n".join("[%d] %s %s: %s" % (i, m["when"].strftime("%a %d %b %H:%M"), m["sender"],
                                             helper.redact(m["body"])[:1500]) for i, m in enumerate(msgs, 1))
        result = helper.gemini(PROMPT.format(room=name, today=dt.date.today().isoformat(), me=me, messages=text[:20000]))
        for it in result.get("items") or []:
            nums = [n for n in it.get("message_numbers") or [] if isinstance(n, int) and 1 <= n <= len(msgs)] or [len(msgs)]
            src = msgs[nums[0] - 1]
            links = [{"url": "https://matrix.to/#/%s/%s" % (room_id, src["id"]), "label": "Open message in Element"}]
            for n in nums:
                links += [{"url": u, "label": ""} for u in helper.URL_RE.findall(msgs[n - 1]["body"])]
            deadline = it.get("deadline") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(it.get("deadline"))) else None
            if deadline and re.fullmatch(r"\d{1,2}:\d{2}", str(it.get("deadline_time") or "")):
                deadline += "T" + it["deadline_time"]
            quote = "\n".join("» %s: %s" % (msgs[n - 1]["sender"], helper.redact(msgs[n - 1]["body"])[:400]) for n in nums)
            row = {"msg_id": "matrix:" + src["id"], "account": "Matrix: " + name, "received": src["when"].isoformat(timespec="minutes"),
                   "sender": src["sender"], "sender_addr": src["sender"], "subject": "Group: " + name,
                   "body": quote, "links": json.dumps(links[:6])}
            con.execute("""INSERT OR IGNORE INTO emails (msg_id, account, received, sender, sender_addr, subject, body, links,
                           analysed, category, importance, summary, action, deadline)
                           VALUES (?,?,?,?,?,?,?,?,1,'course',?,?,?,?)""",
                        (row["msg_id"], row["account"], row["received"], row["sender"], row["sender_addr"], row["subject"],
                         row["body"], row["links"], it.get("importance", "medium"),
                         "%s || %s\n\n%s" % (it.get("title", ""), it.get("summary", ""), quote),
                         it.get("action"), deadline))
            con.commit()
            helper.suggest_dates(con, row, it.get("dates") or [])
        helper.log("Matrix '%s': %d new message(s), %d item(s)" % (name, len(msgs), len(result.get("items") or [])))
    helper.set_state(con, "matrix_since", data["next_batch"])
    if skipped_encrypted:
        helper.log("Matrix: %d encrypted message(s) could not be read." % skipped_encrypted)
