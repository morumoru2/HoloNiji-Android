import sqlite3
import os
from datetime import datetime
from typing import List, Optional
from models.member import Member
from models.video import Video

def _adapt_datetime(dt: datetime) -> str:
    return dt.isoformat()

def _convert_datetime(value: bytes) -> datetime:
    return datetime.fromisoformat(value.decode())

# Ensure stable datetime handling across Python versions
sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_converter("TIMESTAMP", _convert_datetime)

class DatabaseManager:
    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self):
        return sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    def _init_db(self):
        conn = self._get_connection()
        conn.execute('PRAGMA journal_mode=WAL;')
        cursor = conn.cursor()
        
        # Members Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                group_name TEXT NOT NULL,
                generation TEXT NOT NULL,
                channel_id TEXT NOT NULL UNIQUE,
                youtube_url TEXT NOT NULL,
                twitter_url TEXT,
                is_favorite INTEGER DEFAULT 0,
                icon_url TEXT
            )
        ''')

        # Videos Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                published_at TIMESTAMP NOT NULL,
                thumbnail_url TEXT NOT NULL,
                description TEXT,
                is_collab INTEGER DEFAULT 0,
                FOREIGN KEY(channel_id) REFERENCES members(channel_id)
            )
        ''')

        # Settings Table (for app metadata like last update dates)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        conn.commit()
        conn.close()

    # --- Settings ---
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        ''', (key, value))
        conn.commit()
        conn.close()

    # --- Members ---
    def upsert_member(self, member: Member):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO members (name, group_name, generation, channel_id, youtube_url, twitter_url, icon_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                name=excluded.name,
                group_name=excluded.group_name,
                generation=excluded.generation,
                youtube_url=excluded.youtube_url,
                twitter_url=excluded.twitter_url,
                icon_url=excluded.icon_url
        ''', (member.name, member.group_name, member.generation, member.channel_id, 
              member.youtube_url, member.twitter_url, member.icon_url))
        conn.commit()
        conn.close()

    def get_all_members(self) -> List[Member]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM members ORDER BY group_name, generation, name')
        rows = cursor.fetchall()
        conn.close()
        return [Member(*row) for row in rows]

    def toggle_favorite(self, channel_id: str, is_favorite: bool):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE members SET is_favorite = ? WHERE channel_id = ?', (1 if is_favorite else 0, channel_id))
        conn.commit()
        conn.close()

    # --- Videos ---
    def upsert_video(self, video: Video):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO videos (video_id, title, url, channel_id, published_at, thumbnail_url, description, is_collab)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                title=excluded.title,
                thumbnail_url=excluded.thumbnail_url,
                description=excluded.description,
                is_collab=excluded.is_collab
        ''', (video.video_id, video.title, video.url, video.channel_id, video.published_at, 
              video.thumbnail_url, video.description, 1 if video.is_collab else 0))
        conn.commit()
        conn.close()

    def get_videos(self, limit: int = 50, offset: int = 0) -> List[Video]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM videos ORDER BY published_at DESC LIMIT ? OFFSET ?', (limit, offset))
        rows = cursor.fetchall()
        conn.close()
        return [Video(*row) for row in rows]
    
    def get_videos_by_channel(self, channel_id: str, limit: int = 20) -> List[Video]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM videos WHERE channel_id = ? ORDER BY published_at DESC LIMIT ?', (channel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [Video(*row) for row in rows]

    # --- Group-based queries ---
    def get_members_by_group(self, group_name: str) -> List[Member]:
        """Get all members from a specific group (hololive or nijisanji)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM members WHERE group_name = ? ORDER BY generation, name', (group_name,))
        rows = cursor.fetchall()
        conn.close()
        return [Member(*row) for row in rows]

    def get_videos_by_group(self, group_name: str, limit: int = 50, offset: int = 0) -> List[Video]:
        """Get videos from members of a specific group"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.* FROM videos v
            JOIN members m ON v.channel_id = m.channel_id
            WHERE m.group_name = ?
            ORDER BY v.published_at DESC
            LIMIT ? OFFSET ?
        ''', (group_name, limit, offset))
        rows = cursor.fetchall()
        conn.close()
        return [Video(*row) for row in rows]

    def get_collabs_by_group(self, group_name: str, limit: int = 50) -> List[Video]:
        """Get collaboration videos from members of a specific group"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.* FROM videos v
            JOIN members m ON v.channel_id = m.channel_id
            WHERE m.group_name = ? AND v.is_collab = 1
            ORDER BY v.published_at DESC
            LIMIT ?
        ''', (group_name, limit))
        rows = cursor.fetchall()
        conn.close()
        return [Video(*row) for row in rows]

    def get_favorites_by_group(self, group_name: str, limit: int = 50) -> List[Video]:
        """Get videos from favorite members of a specific group"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT v.* FROM videos v
            JOIN members m ON v.channel_id = m.channel_id
            WHERE m.group_name = ? AND m.is_favorite = 1
            ORDER BY v.published_at DESC
            LIMIT ?
        ''', (group_name, limit))
        rows = cursor.fetchall()
        conn.close()
        return [Video(*row) for row in rows]

