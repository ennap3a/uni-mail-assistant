"""Telegram output: works on every phone (iPhone, Android) and computer.

The bot only talks to YOUR chat (the chat id saved during setup). Messages from anyone else are ignored.
Privacy note: Telegram bot chats are not end-to-end encrypted, so Telegram's servers can technically
read these messages.
"""
import json
import uuid
import urllib.error
import urllib.parse
import urllib.request

import net

API = "https://api.telegram.org/bot%s/%s"
MAX_LEN = 4000


class Bot:
    def __init__(self, token, chat_id=None):
        self.token = token
        self.chat_id = chat_id

    # ------------------------------------------------------------ low level
    def call(self, method, params=None, timeout=30):
        data = json.dumps(params or {}).encode()
        req = urllib.request.Request(API % (self.token, method), data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                res = json.load(r)
        except urllib.error.HTTPError as e:
            try:
                desc = json.load(e).get("description", "")
            except Exception:
                desc = ""
            if e.code == 401:
                raise RuntimeError("Telegram rejected the bot token (run setup again).")
            raise RuntimeError("Telegram error %s %s" % (e.code, desc))
        except Exception as e:
            if net.is_cert_error(e):
                raise RuntimeError("Telegram: " + net.CERT_HELP)
            raise RuntimeError("Telegram not reachable: %s" % getattr(e, "reason", e))
        if not res.get("ok"):
            raise RuntimeError("Telegram error: %s" % res.get("description"))
        return res["result"]

    def me(self):
        return self.call("getMe")

    # ------------------------------------------------------------ sending
    def send(self, text, buttons=None, silent=False):
        """text: HTML. buttons: [[(label, callback_data), ...], ...]. Returns message_id of the last part."""
        chunks = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)] or [""]
        mid = None
        for i, chunk in enumerate(chunks):
            p = {"chat_id": self.chat_id, "text": chunk, "parse_mode": "HTML",
                 "disable_web_page_preview": True, "disable_notification": silent}
            if buttons and i == len(chunks) - 1:
                p["reply_markup"] = {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row]
                                                         for row in buttons]}
            mid = self.call("sendMessage", p)["message_id"]
        return mid

    def edit_buttons(self, message_id, note):
        """Replaces the buttons of a message with a short note like '✅ Added'."""
        try:
            self.call("editMessageReplyMarkup", {"chat_id": self.chat_id, "message_id": message_id,
                                                 "reply_markup": {"inline_keyboard": [[{"text": note, "callback_data": "noop"}]]}})
        except Exception:
            pass

    def answer_button(self, callback_id, text=""):
        try:
            self.call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})
        except Exception:
            pass

    def send_file(self, filename, content_bytes, caption=""):
        """Sends a file (e.g. an .ics calendar event). Tapping it on the phone adds it to the calendar."""
        boundary = uuid.uuid4().hex
        parts = []
        for name, value in (("chat_id", str(self.chat_id)), ("caption", caption)):
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, name, value)).encode())
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"document\"; filename=\"%s\"\r\n"
                      "Content-Type: text/calendar\r\n\r\n" % (boundary, filename)).encode() + content_bytes + b"\r\n")
        parts.append(("--%s--\r\n" % boundary).encode())
        req = urllib.request.Request(API % (self.token, "sendDocument"), data=b"".join(parts),
                                     headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            if net.is_cert_error(e):
                raise RuntimeError("Telegram: " + net.CERT_HELP)
            raise

    # ------------------------------------------------------------ receiving
    def updates(self, offset=None, timeout=0):
        p = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            p["offset"] = offset
        return self.call("getUpdates", p, timeout=timeout + 15)

    def is_owner(self, update):
        """True only for updates from the chat saved during setup."""
        if "callback_query" in update:
            chat = update["callback_query"].get("message", {}).get("chat", {})
        else:
            chat = update.get("message", {}).get("chat", {})
        return self.chat_id is not None and str(chat.get("id")) == str(self.chat_id)


def esc(text):
    """Escape text for Telegram HTML."""
    return (str(text or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def link(url, label):
    return '<a href="%s">%s</a>' % (esc(url).replace('"', "&quot;"), esc(label or url[:60]))
