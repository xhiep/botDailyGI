from __future__ import annotations

from dataclasses import dataclass

from botdailygi.clients.telegram import edit_text, send_chat_action, send_text
from botdailygi.runtime.state import progress_lock_for


@dataclass
class ProgressMessage:
    chat_id: str | int
    message_id: int | None

    @classmethod
    def start(cls, chat_id, text: str, *, action: str = "typing") -> "ProgressMessage":
        send_chat_action(chat_id, action)
        return cls(chat_id=chat_id, message_id=send_text(chat_id, text))

    def update(self, text: str, *, action: str = "typing") -> None:
        send_chat_action(self.chat_id, action)
        lock = progress_lock_for(self.chat_id)
        with lock:
            if self.message_id and edit_text(self.chat_id, self.message_id, text):
                return
            self.message_id = send_text(self.chat_id, text)

    def done(self, text: str, *, action: str = "typing") -> None:
        self.update(text, action=action)

    def fail(self, text: str, *, action: str = "typing") -> None:
        self.update(text, action=action)
