import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List
from models.member import Member
from models.video import Video
from core.database import DatabaseManager
from core.scraper import Scraper
from core.rss import RSSParser

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, db_path="data/app.db"):
        self.db = DatabaseManager(db_path)
        self.scraper = Scraper()
        self.rss = RSSParser()
        self.api_key = None  # YouTube API key (optional)

    async def update_all_data(self):
        logger.info("Starting full data update...")
        await self.update_members()
        await self.update_recent_videos()
        logger.info("Full data update complete.")

    async def update_members(self):
        # Check last update date
        last_update_str = self.db.get_setting("last_member_update")
        # If DB is empty, always update regardless of last_update
        existing_members = self.db.get_all_members()
        # If either group is missing, force update even if last update is recent
        missing_group = False
        if existing_members:
            try:
                missing_group = (len(self.db.get_members_by_group("hololive")) == 0) or (len(self.db.get_members_by_group("nijisanji")) == 0)
            except Exception:
                missing_group = False

        if last_update_str and existing_members and not missing_group:
            try:
                last_update = datetime.fromisoformat(last_update_str)
                if datetime.now() - last_update < timedelta(days=7):
                    logger.info("Skipping members update (less than 7 days since last update).")
                    return
            except ValueError:
                logger.warning(f"Invalid last_member_update format: {last_update_str}. Proceeding with update.")

        logger.info("Updating members...")
        # Hololive
        try:
            holo_members_data = await self.scraper.scrape_hololive()
            for m_data in holo_members_data:
                member = Member(
                    id=0, # Auto-increment handled by DB upsert logic
                    name=m_data["name"],
                    group_name=m_data["group_name"],
                    generation=m_data["generation"],
                    channel_id=m_data["channel_id"],
                    youtube_url=m_data["youtube_url"],
                    twitter_url=m_data.get("twitter_url"),
                    icon_url=m_data.get("icon_url"),
                    is_favorite=False # Default
                )
                self.db.upsert_member(member)
        except Exception as e:
            logger.error(f"Failed to update Hololive members: {e}")

        # Nijisanji
        try:
            niji_members_data = await self.scraper.scrape_nijisanji()
            for m_data in niji_members_data:
                member = Member(
                    id=0,
                    name=m_data["name"],
                    group_name=m_data["group_name"],
                    generation=m_data.get("generation", "Unknown"),
                    channel_id=m_data["channel_id"],
                    youtube_url=m_data["youtube_url"],
                    twitter_url=m_data.get("twitter_url"),
                    icon_url=m_data.get("icon_url"),
                    is_favorite=False
                )
                self.db.upsert_member(member)
        except Exception as e:
            logger.error(f"Failed to update Nijisanji members: {e}")
        
        # Update last update timestamp
        self.db.set_setting("last_member_update", datetime.now().isoformat())

    async def update_recent_videos(self, group_filter: str = None):
        logger.info(f"Updating videos... (Group: {group_filter})")
        
        if group_filter:
            members = self.db.get_members_by_group(group_filter)
        else:
            members = self.db.get_all_members()
            
        # process in chunks to avoid rate limits? RSS is per channel.
        # Async gather for all?
        # Maybe batches of 10.
        
        chunk_size = 5
        for i in range(0, len(members), chunk_size):
            chunk = members[i:i + chunk_size]
            tasks = [self._update_member_video(m) for m in chunk]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _update_member_video(self, member: Member):
        if not member.channel_id:
            return
            
        # Resolve Nijisanji Channel ID if needed (legacy niji_ IDs)
        if not member.channel_id.startswith('UC') and member.channel_id.startswith('niji_'):
            slug = member.channel_id.replace('niji_', '')
            logger.info(f"Resolving channel ID for {member.name} ({slug})...")
            
            # Add delay to be gentle to the server
            await asyncio.sleep(1.0)
            
            real_id = await self.scraper.resolve_nijisanji_channel_id(slug)
            if real_id and real_id.startswith('UC'):
                logger.info(f"Resolved {member.name}: {real_id}")
                # Update Member object and DB
                old_id = member.channel_id
                member.channel_id = real_id
                
                # Update DB directly here
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE members SET channel_id = ? WHERE channel_id = ?', (real_id, old_id))
                cursor.execute('UPDATE videos SET channel_id = ? WHERE channel_id = ?', (real_id, old_id))
                conn.commit()
                conn.close()
            else:
                logger.warning(f"Could not resolve channel ID for {member.name}")
                return
        elif not member.channel_id.startswith('UC'):
            # Enforce UC-only channel IDs
            return

        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={member.channel_id}"
        
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                xml = await self.scraper.fetch_page(session, url)
                if not xml:
                    return
                
                videos_data = self.rss.parse_feed(xml)
                
                # Get all member names for collab detection
                # Optimization: Cache names mapping or pass it in
                all_members = self.db.get_all_members()
                # Create a set of names/aliases
                # Heuristic: Name must be at least 2 chars to avoid false positives (though most JP names are)
                # Filter out the owner of the video
                other_members = [m.name for m in all_members if m.channel_id != member.channel_id]

                for v_data in videos_data:
                    title = v_data["title"]
                    description = v_data.get("description", "")
                    
                    is_collab = False
                    # Simple string matching
                    # Better: Regex or specialized tokenizer
                    combined_text = (title + " " + description)
                    
                    for name in other_members:
                        if name in combined_text:
                            is_collab = True
                            break
                    
                    video = Video(
                        video_id=v_data["video_id"],
                        title=title,
                        url=v_data["url"],
                        channel_id=member.channel_id,
                        published_at=v_data["published_at"],
                        thumbnail_url=v_data["thumbnail_url"],
                        description=description,
                        is_collab=is_collab
                    )
                    self.db.upsert_video(video)
            except Exception as e:
                logger.error(f"Error updating videos for {member.name}: {e}")

