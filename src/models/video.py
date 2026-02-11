from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Video:
    video_id: str
    title: str
    url: str
    channel_id: str
    published_at: datetime
    thumbnail_url: str
    description: Optional[str] = None
    is_collab: bool = False

    def __post_init__(self):
        # Ensure published_at is a datetime
        if isinstance(self.published_at, str):
            try:
                self.published_at = datetime.fromisoformat(self.published_at)
            except ValueError:
                # Fallback for common SQLite string format
                try:
                    self.published_at = datetime.strptime(self.published_at, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Last resort: use current time to avoid crashes downstream
                    self.published_at = datetime.now()
        # Ensure is_collab is boolean
        if isinstance(self.is_collab, int) and not isinstance(self.is_collab, bool):
            self.is_collab = bool(self.is_collab)
