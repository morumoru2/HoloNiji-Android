import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> str:
        try:
            # Respect session timeout if set, else rely on outer session config or default
            # But here we pass session in. Ideally session should be created with timeout.
            # Let's enforce timeout on the get call if possible or just rely on session.
            # Actually, scrape_hololive creates session without timeout.
            # Let's change how sessions are created in the calling methods.
            async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""

    async def scrape_hololive(self) -> List[Dict]:
        url = "https://hololive.hololivepro.com/talents"
        members = []
        
        async with aiohttp.ClientSession() as session:
            html = await self.fetch_page(session, url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Simplified Logic: Find all talent lists and their preceding headers
            talent_lists = soup.select('ul.talent_list')
            
            # If no lists found via class, try finding all ULs following h3/h4 headers
            if not talent_lists:
                headers = soup.find_all(['h3', 'h4'])
                for h in headers:
                    next_ul = h.find_next_sibling('ul')
                    if next_ul:
                        talent_lists.append(next_ul)

            for ul in talent_lists:
                # Determine generation from preceding header
                # Try immediate previous sibling first
                header = ul.find_previous_sibling(['h3', 'h4'])
                
                # If not found immediately, maybe iterate back a few steps or look at parent's previous
                if not header:
                    # Some structures wrap headers in divs
                    parent = ul.parent
                    if parent:
                        header = parent.find_previous_sibling(['h3', 'h4'])
                
                gen_name = header.get_text(strip=True) if header else "hololive"
                
                # Iterate items
                for li in ul.find_all('li'):
                    a = li.find('a')
                    if not a: continue
                    
                    profile_url = a.get('href', '')
                    if not profile_url: continue
                    
                    # Fetch profile details
                    member_data = await self._scrape_hololive_profile(session, profile_url)
                    if member_data:
                        member_data['generation'] = gen_name
                        member_data['group_name'] = 'hololive'
                        members.append(member_data)
        
        return members

        return members

    async def _scrape_hololive_profile(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        html = await self.fetch_page(session, url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Name
            name = ""
            # Some pages have empty H1s at the top. Find the one with text.
            h1s = soup.find_all('h1')
            for h in h1s:
                txt = h.get_text(strip=True)
                if txt:
                    name = txt
                    break
            
            if not name: return None

            # Links
            youtube_url = ""
            twitter_url = ""
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'youtube.com' in href and not youtube_url:
                    if '/channel/' in href or '/@' in href or '/c/' in href or '/user/' in href:
                        youtube_url = href
                if ('twitter.com' in href or 'x.com' in href) and not twitter_url:
                    if '/status/' not in href:
                        twitter_url = href
            
            # Icon - Robust Extraction
            icon_url = ""
            
            # Use name from title meta if h1 is missing
            if not name:
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    name = meta_title.get('content', '').split('|')[0].strip()

            # Strategy 1: .talent_main_img img (Original)
            img_el = soup.select_one('.talent_main_img img')
            if img_el:
                icon_url = img_el.get('src', '')
            
            # Strategy 2: .main_image img (New)
            if not icon_url:
                img_el = soup.select_one('.main_image img')
                if img_el:
                     icon_url = img_el.get('src', '')

            # Strategy 3: Right Side or Top Figure (New)
            if not icon_url:
                figures = soup.find_all('figure')
                for fig in figures:
                    img = fig.find('img')
                    if img:
                        src = img.get('src', '')
                        if 'wp-content' in src and ('talent' in src or 'character' in src):
                             icon_url = src
                             break
            
            # Strategy 4: og:image (Fallback)
            if not icon_url:
                og_img = soup.find('meta', property='og:image')
                if og_img:
                    icon_url = og_img.get('content', '')
            
            channel_id = self._extract_channel_id(youtube_url)
            if not channel_id and youtube_url:
                channel_id = await self._resolve_youtube_channel_id(session, youtube_url)
            
            # If channel_id is missing entirely, skip
            if not channel_id:
                logger.warning(f"Skipping {name}: Invalid channel_id (URL: {youtube_url})")
                return None
            
            return {
                "name": name,
                "group_name": "hololive",
                "generation": "Unknown", 
                "channel_id": channel_id,
                "youtube_url": youtube_url,
                "twitter_url": twitter_url,
                "icon_url": icon_url
            }
        except Exception as e:
            logger.error(f"Error parsing profile {url}: {e}")
            return None

    def _extract_channel_id(self, url: str) -> str:
        """
        Extract YouTube channel ID from various URL formats.
        Returns the actual channel ID (UCxxx) or empty string if not found.
        """
        if not url:
            return ""
        
        # Pattern 1: /channel/UCxxx format
        match = re.search(r'youtube\.com/channel/(UC[\w-]+)', url)
        if match:
            return match.group(1)
        
        # Pattern 2: /c/channelname or /@username format
        # These cannot be converted to UC IDs without API or scraping
        # Return a stable non-UC identifier so members can still be stored.
        if '/@' in url or '/c/' in url or '/user/' in url:
            if '/@' in url:
                match = re.search(r'/@([^/?]+)', url)
                if match:
                    return f"@{match.group(1)}"
            if '/c/' in url:
                match = re.search(r'/c/([^/?]+)', url)
                if match:
                    return f"c_{match.group(1)}"
            if '/user/' in url:
                match = re.search(r'/user/([^/?]+)', url)
                if match:
                    return f"user_{match.group(1)}"
            return ""
        
        # If no pattern matched, return empty
        return ""


    async def scrape_nijisanji(self) -> List[Dict]:
        url = "https://www.nijisanji.jp/talents"
        
        async with aiohttp.ClientSession() as session:
            html = await self.fetch_page(session, url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            
            members = []
            if script:
                import json
                try:
                    data = json.loads(script.string)
                    livers = data.get('props', {}).get('pageProps', {}).get('allLivers', [])
                    
                    logger.info(f"Found {len(livers)} Nijisanji livers")
                    
                    for t in livers:
                        try:
                            name = t.get('name') or t.get('enName', '')
                            if not name: continue
                            
                            slug = t.get('slug', '')
                            
                            socials = t.get('socials', {}) or {}
                            social_links = t.get('socialLinks', {}) or {}
                            youtube_url = socials.get('youtube', '') or social_links.get('youtube', '') or ''
                            twitter_url = socials.get('twitter', '') or social_links.get('twitter', '') or ''
                            
                            if twitter_url and not twitter_url.startswith('http'):
                                twitter_url = f"https://twitter.com/{twitter_url}"

                            # Images - Robust extraction
                            icon_url = ""
                            images = t.get('images', {})
                            # Try known keys
                            keys = ['head', 'main', 'card']
                            for k in keys:
                                if k in images:
                                    val = images[k]
                                    if isinstance(val, dict):
                                        icon_url = val.get('url', '')
                                    elif isinstance(val, str):
                                        icon_url = val
                                    
                                    if icon_url:
                                        if icon_url.startswith('/'):
                                            icon_url = f"https://www.nijisanji.jp{icon_url}"
                                        break
                            
                            if not icon_url:
                                # Fallback: try iterating values if dict
                                if isinstance(images, dict):
                                    for v in images.values():
                                        if isinstance(v, dict) and 'url' in v:
                                            icon_url = v['url']
                                            if icon_url: break

                            affiliation = t.get('affiliation', '')
                            
                            channel_id = self._extract_channel_id(youtube_url)
                            
                            # Enforce UC-only channel IDs for consistency.
                            # If not available from the list page, try resolving from talent page.
                            if not channel_id and slug:
                                channel_id = await self._resolve_nijisanji_channel_id_with_session(session, slug)
                            
                            if not channel_id:
                                # Use slug as fallback so member appears even without UC
                                if slug:
                                    channel_id = f"niji_{slug}"
                                else:
                                    logger.warning(f"Skipping {name}: Invalid channel_id (URL: {youtube_url})")
                                    continue

                            members.append({
                                "name": name,
                                "group_name": "nijisanji",
                                "generation": affiliation if affiliation else "にじさんじ",
                                "channel_id": channel_id,
                                "youtube_url": youtube_url,
                                "twitter_url": twitter_url,
                                "icon_url": icon_url
                            })
                        except Exception as e:
                            logger.error(f"Error parsing nijisanji liver: {e}")
                            continue

                except Exception as e:
                    logger.error(f"Error parsing Nijisanji JSON: {e}")
            
            
            return members

    async def _resolve_nijisanji_channel_id_with_session(self, session: aiohttp.ClientSession, slug: str) -> Optional[str]:
        """
        Resolve YouTube channel ID from a talent page using an existing session.
        """
        url = f"https://www.nijisanji.jp/talents/l/{slug}"
        try:
            html = await self.fetch_page(session, url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            youtube_url = ""
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'youtube.com' in href:
                    if '/channel/' in href or '/@' in href or '/c/' in href or '/user/' in href:
                        youtube_url = href
                        break
            
            if youtube_url:
                channel_id = self._extract_channel_id(youtube_url)
                if not channel_id:
                    channel_id = await self._resolve_youtube_channel_id(session, youtube_url)
                return channel_id
        except Exception as e:
            logger.error(f"Error resolving channel ID for {slug}: {e}")
        return None

    async def _resolve_youtube_channel_id(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """
        Resolve UC channel ID from a YouTube handle/custom URL by fetching the page
        and extracting the channelId from HTML.
        """
        if not url:
            return None
        
        # Normalize to a full URL
        if url.startswith("@"):
            url = f"https://www.youtube.com/{url}"
        
        # Strip query params that might cause mismatches
        url = url.split("?")[0]
        
        html = await self.fetch_page(session, url)
        if not html:
            return None
        
        # Try to extract channelId from page source
        match = re.search(r'channelId\":\"(UC[\\w-]+)\"', html)
        if match:
            return match.group(1)
        
        match = re.search(r'\"channelId\":\"(UC[\\w-]+)\"', html)
        if match:
            return match.group(1)
        
        return None

    async def resolve_nijisanji_channel_id(self, slug: str) -> Optional[str]:
        """
        Fetch individual talent page to resolve YouTube channel ID.
        """
        url = f"https://www.nijisanji.jp/talents/l/{slug}"
        try:
            async with aiohttp.ClientSession() as session:
                html = await self.fetch_page(session, url)
                if not html:
                    return None
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for YouTube link in social links section
                # Usually in a list or specific container
                youtube_url = ""
                
                # Strategy 1: Find 'youtube.com' in any 'a' tag
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if 'youtube.com' in href:
                        if '/channel/' in href or '/@' in href or '/c/' in href or '/user/' in href:
                             youtube_url = href
                             break
                
                if youtube_url:
                    return self._extract_channel_id(youtube_url)
                    
        except Exception as e:
            logger.error(f"Error resolving channel ID for {slug}: {e}")
            
        return None

