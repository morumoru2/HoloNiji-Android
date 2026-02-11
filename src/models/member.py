from dataclasses import dataclass
from typing import Optional

@dataclass
class Member:
    id: int  # Database ID
    name: str
    group_name: str  # 'hololive' or 'nijisanji'
    generation: str
    channel_id: str
    youtube_url: str
    twitter_url: Optional[str] = None
    is_favorite: bool = False
    icon_url: Optional[str] = None

    def __post_init__(self):
        # Ensure is_favorite is boolean if loaded from integer
        if isinstance(self.is_favorite, int) and not isinstance(self.is_favorite, bool):
            self.is_favorite = bool(self.is_favorite)
