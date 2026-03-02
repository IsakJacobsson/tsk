"""Task data model."""

import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


def generate_id(message: str, created_at: datetime) -> str:
    """Generate a 7-character SHA-256 hash from timestamp + message."""
    raw = f"{created_at.isoformat()}:{message}"
    return hashlib.sha256(raw.encode()).hexdigest()[:7]


class TaskStatus(str, Enum):
    """Allowed states for a task."""

    OPEN = "open"
    DONE = "done"
    WONTDO = "wontdo"


@dataclass
class Task:
    """A single task."""

    message: str
    id: str = ""
    created_at: str = ""
    status: TaskStatus = TaskStatus.OPEN

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = generate_id(self.message, datetime.fromisoformat(self.created_at))
        if not isinstance(self.status, TaskStatus):
            try:
                self.status = TaskStatus((self.status or TaskStatus.OPEN.value).strip().lower())
            except ValueError:
                self.status = TaskStatus.OPEN

    @property
    def completed(self) -> bool:
        return self.status == TaskStatus.DONE

    @completed.setter
    def completed(self, value: bool) -> None:
        self.status = TaskStatus.DONE if value else TaskStatus.OPEN

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        raw_status = data.get("status", "")
        if raw_status:
            try:
                status = raw_status if isinstance(raw_status, TaskStatus) else TaskStatus(str(raw_status).strip().lower())
            except ValueError:
                status = TaskStatus.OPEN
        else:
            status = TaskStatus.DONE if data.get("completed", False) else TaskStatus.OPEN
        return cls(
            message=data["message"],
            id=data.get("id", ""),
            created_at=data.get("created_at", ""),
            status=status,
        )
