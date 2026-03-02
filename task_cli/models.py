"""Task data model."""

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime


def generate_id(message: str, created_at: datetime) -> str:
    """Generate a 7-character SHA-256 hash from timestamp + message."""
    raw = f"{created_at.isoformat()}:{message}"
    return hashlib.sha256(raw.encode()).hexdigest()[:7]


@dataclass
class Task:
    """A single task."""

    message: str
    id: str = ""
    created_at: str = ""
    completed: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = generate_id(self.message, datetime.fromisoformat(self.created_at))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            message=data["message"],
            id=data.get("id", ""),
            created_at=data.get("created_at", ""),
            completed=data.get("completed", False),
        )
