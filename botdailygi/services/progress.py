from __future__ import annotations

from dataclasses import dataclass, field

from botdailygi.clients.telegram import edit_text, send_chat_action, send_text
from botdailygi.runtime.state import progress_lock_for
from botdailygi.ui_constants import SPINNER_FRAMES, PREFIX_SUCCESS, PREFIX_ERROR


_FRAMES = SPINNER_FRAMES


@dataclass
class ProgressMessage:
    chat_id: str | int
    message_id: int | None
    frame_index: int = field(default=0)

    def _framed(self, text: str) -> str:
        frame = _FRAMES[self.frame_index % len(_FRAMES)]
        self.frame_index += 1
        return f"{text}\n\n{frame} Đang xử lý..."

    @classmethod
    def start(cls, chat_id, text: str, *, action: str = "typing") -> "ProgressMessage":
        send_chat_action(chat_id, action)
        progress = cls(chat_id=chat_id, message_id=None)
        progress.message_id = send_text(chat_id, progress._framed(text))
        return progress

    def update(self, text: str, *, action: str = "typing") -> None:
        send_chat_action(self.chat_id, action)
        lock = progress_lock_for(self.chat_id)
        framed = self._framed(text)
        with lock:
            if self.message_id and edit_text(self.chat_id, self.message_id, framed):
                return
            self.message_id = send_text(self.chat_id, framed)

    def done(self, text: str, *, action: str = "typing") -> None:
        send_chat_action(self.chat_id, action)
        lock = progress_lock_for(self.chat_id)
        final_text = f"{PREFIX_SUCCESS} Hoàn tất\n\n{text}"
        with lock:
            if self.message_id and edit_text(self.chat_id, self.message_id, final_text):
                return
            self.message_id = send_text(self.chat_id, final_text)

    def fail(self, text: str, *, action: str = "typing") -> None:
        send_chat_action(self.chat_id, action)
        lock = progress_lock_for(self.chat_id)
        final_text = f"{PREFIX_ERROR} Có lỗi xảy ra\n\n{text}"
        with lock:
            if self.message_id and edit_text(self.chat_id, self.message_id, final_text):
                return
            self.message_id = send_text(self.chat_id, final_text)
