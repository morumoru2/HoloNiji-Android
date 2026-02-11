"""
Export utilities for backing up and exporting data from the application.
"""

import csv
import json
from datetime import datetime
from typing import List
from models.member import Member
from models.video import Video
from core.database import DatabaseManager


class ExportManager:
    """Manager for exporting application data"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def export_members_csv(self, filepath: str, group_filter: str = None):
        """
        Export members to CSV file.
        
        Args:
            filepath: Path to save the CSV file
            group_filter: Optional group filter ('hololive' or 'nijisanji')
        """
        if group_filter:
            members = self.db.get_members_by_group(group_filter)
        else:
            members = self.db.get_all_members()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'group_name', 'generation', 'channel_id', 
                         'youtube_url', 'twitter_url', 'is_favorite']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for m in members:
                writer.writerow({
                    'name': m.name,
                    'group_name': m.group_name,
                    'generation': m.generation,
                    'channel_id': m.channel_id,
                    'youtube_url': m.youtube_url,
                    'twitter_url': m.twitter_url or '',
                    'is_favorite': '1' if m.is_favorite else '0'
                })
    
    def export_videos_csv(self, filepath: str, group_filter: str = None, limit: int = 500):
        """
        Export videos to CSV file.
        
        Args:
            filepath: Path to save the CSV file
            group_filter: Optional group filter
            limit: Maximum number of videos to export
        """
        if group_filter:
            videos = self.db.get_videos_by_group(group_filter, limit=limit)
        else:
            videos = self.db.get_videos(limit=limit)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['video_id', 'title', 'url', 'channel_id', 
                         'published_at', 'is_collab']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for v in videos:
                writer.writerow({
                    'video_id': v.video_id,
                    'title': v.title,
                    'url': v.url,
                    'channel_id': v.channel_id,
                    'published_at': v.published_at.isoformat(),
                    'is_collab': '1' if v.is_collab else '0'
                })
    
    def export_favorites_json(self, filepath: str):
        """
        Export favorite members to JSON for backup.
        
        Args:
            filepath: Path to save the JSON file
        """
        members = self.db.get_all_members()
        favorites = [
            {
                'name': m.name,
                'channel_id': m.channel_id,
                'group_name': m.group_name
            }
            for m in members if m.is_favorite
        ]
        
        backup_data = {
            'export_date': datetime.now().isoformat(),
            'favorites': favorites
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    def import_favorites_json(self, filepath: str):
        """
        Import favorite members from JSON backup.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Number of favorites restored
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        favorites = backup_data.get('favorites', [])
        restored = 0
        
        for fav in favorites:
            channel_id = fav.get('channel_id')
            if channel_id:
                try:
                    self.db.toggle_favorite(channel_id, True)
                    restored += 1
                except Exception:
                    pass  # Skip if member doesn't exist
        
        return restored
