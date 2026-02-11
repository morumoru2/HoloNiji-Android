import feedparser
from datetime import datetime
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

def parse_rfc3339(date_string: str) -> datetime:
    """Parse RFC 3339 / ISO 8601 date string without external dependencies."""
    # YouTube RSS feeds use format like: 2024-01-15T12:30:00+00:00
    # Remove timezone for simplicity (assume UTC)
    date_string = re.sub(r'[+-]\d{2}:\d{2}$', '', date_string)
    date_string = date_string.replace('Z', '')
    
    try:
        return datetime.fromisoformat(date_string)
    except ValueError:
        # Fallback: try strptime
        try:
            return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            return datetime.now()

class RSSParser:
    def parse_feed(self, xml_content: str) -> List[Dict]:
        feed = feedparser.parse(xml_content)
        videos = []
        
        if feed.bozo:
             logger.warning("Feed parsing error")
        
        for entry in feed.entries:
            try:
                # Video ID is usually in <yt:videoId> -> entry.yt_videoid
                # OR extracted from entry.link or entry.id
                video_id = getattr(entry, 'yt_videoid', None)
                if not video_id:
                     # Try extract from id "yt:video:VIDEO_ID"
                     if entry.id.startswith('yt:video:'):
                         video_id = entry.id.split(':')[-1]
                
                if not video_id:
                    continue

                title = entry.title
                link = entry.link
                published = parse_rfc3339(entry.published)
                
                thumbnail = ""
                # Media group
                if 'media_group' in entry and 'media_thumbnail' in entry.media_group:
                     thumbnail = entry.media_group.media_thumbnail[0]['url']
                
                # Fallback: constructive thumbnail URL from video_id
                if not thumbnail and video_id:
                    thumbnail = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
                
                description = entry.summary if 'summary' in entry else ""
                
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "url": link,
                    "published_at": published,
                    "thumbnail_url": thumbnail,
                    "description": description,
                    "channel_id": getattr(entry, 'yt_channelid', "")
                })
            except Exception as e:
                logger.warning(f"Error parsing entry: {e} (skipping)")
                continue
                
        return videos

