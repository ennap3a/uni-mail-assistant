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
from qa import answer

BG, CARD, BLUE, GREY, TEXT = "#F5F5F7", "#FFFFFF", "#0071E3", "#86868B", "#1D1D1F"


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
