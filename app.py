#!/usr/bin/env python3
"""Uni Mail Assistant – chat window. Answers ONLY from emails really downloaded from your inbox."""
import datetime as dt
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext

import helper

BG, CARD, BLUE, GREY, TEXT = "#F5F5F7", "#FFFFFF", "#0071E3", "#86868B", "#1D1D1F"


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
                "Press 'Sync emails' to check now.)" % (label, last))
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Uni Mail Assistant")
        self.geometry("860x680")
        self.configure(bg=BG)
        tk.Label(self, text="🎓 Uni Mail Assistant", font=("Helvetica Neue", 20, "bold"), bg=BG, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 0))
        self.status = tk.Label(self, text="", font=("Helvetica Neue", 12), bg=BG, fg=GREY)
        self.status.pack(anchor="w", padx=16)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=12, pady=8)
        for label, q in [("📅 Yesterday", "What emails did I receive yesterday? Summarize all of them."),
                         ("📊 Last week", "Summarize last week's emails. What do I need to do?"),
                         ("⚠️ To do & deadlines", "What must I do and what are my upcoming deadlines? (last 30 days)")]:
            tk.Button(bar, text=label, command=lambda q=q: self.ask(q), font=("Helvetica Neue", 13)).pack(side="left", padx=4)
        tk.Button(bar, text="🔄 Sync emails", command=self.sync, font=("Helvetica Neue", 13)).pack(side="left", padx=4)
        self.out = scrolledtext.ScrolledText(self, wrap="word", font=("Helvetica Neue", 14), bg=CARD, fg=TEXT,
                                             relief="flat", padx=12, pady=10)
        self.out.pack(fill="both", expand=True, padx=16)
        self.out.tag_config("you", foreground=BLUE, font=("Helvetica Neue", 14, "bold"))
        self.out.tag_config("note", foreground=GREY)
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", padx=16, pady=12)
        self.entry = tk.Entry(row, font=("Helvetica Neue", 14))
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda e: self.ask(self.entry.get()))
        tk.Button(row, text="Ask", command=lambda: self.ask(self.entry.get()), font=("Helvetica Neue", 13)).pack(side="left", padx=6)
        self.refresh_status()

    def refresh_status(self):
        con = helper.db()
        last = helper.get_state(con, "last_sync")
        n = con.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        self.status.config(text="%d real emails stored · last mailbox check: %s" % (n, (last or "never").replace("T", " ")))

    def write(self, text, tag=None):
        self.out.insert("end", text, tag)
        self.out.see("end")

    def ask(self, q):
        q = q.strip()
        if not q:
            return
        self.entry.delete(0, "end")
        self.write("\nYou: ", "you")
        self.write(q + "\n")
        self.write("Reading your emails…\n", "note")
        def work():
            try:
                res = answer(q)
            except Exception as e:
                res = "Problem: %s" % e
            self.after(0, lambda: self.write(res + "\n"))
        threading.Thread(target=work, daemon=True).start()

    def sync(self):
        self.write("\nChecking your mailbox…\n", "note")
        def work():
            r = subprocess.run([sys.executable, helper.__file__, "sync"], capture_output=True, text=True)
            msg = (r.stdout.strip().splitlines() or ["done"])[-1]
            self.after(0, lambda: (self.write(msg + "\n", "note"), self.refresh_status()))
        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
