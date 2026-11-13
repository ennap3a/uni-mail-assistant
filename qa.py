"""Answers questions about your mail. Used by the chat window and by Telegram.
It only uses messages really downloaded from your inboxes and lists which ones it used."""
import datetime as dt
import re

import helper


def day_start(d):
    return dt.datetime.combine(d, dt.time())


def pick_range(question):
    """Turns the question into an exact time window, so the AI can't 'guess' dates."""
    q = question.lower()
    today = dt.date.today()
    if re.search(r"yesterday|gestern", q):
        return day_start(today - dt.timedelta(days=1)), day_start(today), "yesterday (%s)" % (today - dt.timedelta(days=1)).strftime("%a %d %b")
    if re.search(r"\btoday\b|heute", q):
        return day_start(today), day_start(today + dt.timedelta(days=1)), "today"
    if re.search(r"last week|letzte woche|this week|diese woche|7 days", q):
        return day_start(today - dt.timedelta(days=7)), day_start(today + dt.timedelta(days=1)), "the last 7 days"
    if re.search(r"month|monat|30 days", q):
        return day_start(today - dt.timedelta(days=30)), day_start(today + dt.timedelta(days=1)), "the last 30 days"
    return day_start(today - dt.timedelta(days=14)), day_start(today + dt.timedelta(days=1)), "the last 14 days"


ANSWER_PROMPT = """You are the student's university email assistant. Today is {now}.
Below is the COMPLETE list of emails received in {label}, taken directly from their real inbox.
Each has a number like [#3].

STRICT RULES:
- Use ONLY these emails. Never invent emails, senders, dates or deadlines.
- Mention every email with importance "high" or "medium". Group "low" ones (ads, newsletters) in one short line with a count.
- Put things the student must do first, with their deadline, then useful info, then the rest.
- After each point, add the email number, e.g. [#3].
- Write plain text (no markdown symbols like ** or ###). Use "•" for bullets and CAPITAL headings.
- Answer in the language of the question.

Question: {question}

EMAILS ({count}):
{emails}

Dates already waiting for confirmation / in calendar:
{items}"""


def answer(question):
    con = helper.db()
    start, end, label = pick_range(question)
    rows = con.execute("SELECT * FROM emails WHERE received>=? AND received<? ORDER BY received",
                       (start.isoformat(), end.isoformat())).fetchall()
    last = helper.get_state(con, "last_sync") or "never"
    if not rows:
        return ("No uni emails found for %s.\n(Last check of your mailbox: %s. "
                "It checks again automatically every 15 minutes.)" % (label, last))
    lines = []
    for i, r in enumerate(rows, 1):
        lines.append("[#%d] %s | from: %s <%s> | subject: %s | importance: %s | category: %s\n     summary: %s%s%s" % (
            i, r["received"].replace("T", " "), r["sender"], r["sender_addr"], r["subject"],
            r["importance"] or "not analysed", r["category"] or "-",
            (r["summary"] or "").replace(" || ", ": ") or (r["body"] or "")[:300],
            ("\n     to do: " + r["action"]) if r["action"] else "",
            "\n     needs a reply (not replied yet)" if r["needs_reply"] and not r["replied"] else ""))
    items = con.execute("SELECT kind,title,day,time,status FROM items WHERE day>=? AND status IN ('pending','added') ORDER BY day",
                        (dt.date.today().isoformat(),)).fetchall()
    items_txt = "\n".join("- %s: %s on %s (%s)" % (i["kind"], i["title"], helper.pretty(i["day"], i["time"]),
                          "waiting for you to confirm" if i["status"] == "pending" else "in calendar") for i in items) or "none"
    text = helper.gemini(ANSWER_PROMPT.format(now=dt.datetime.now().strftime("%A %Y-%m-%d %H:%M"), label=label,
                                              question=question, count=len(rows), emails="\n".join(lines),
                                              items=items_txt), want_json=False)
    text = re.sub(r"\*\*|__|^#+\s*", "", text, flags=re.M)
    sources = "\n".join("  #%d  %s  %s – %s" % (i, r["received"][5:16].replace("T", " "), r["sender"][:28], r["subject"][:70])
                        for i, r in enumerate(rows, 1))
    return "%s\n\n— Based on all %d emails from %s (last mailbox check: %s):\n%s" % (
        text, len(rows), label, last.replace("T", " "), sources)
