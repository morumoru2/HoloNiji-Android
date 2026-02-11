import asyncio
import os
import sys

# Add src to path to import core, models, etc.
# Assumes main.py is in HololiveNijisanjiApp_Android/
# and src is in HololiveNijisanjiApp_Android/src/
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.recycleview import RecycleView
from kivy.properties import StringProperty, ListProperty
from kivy.core.text import LabelBase
import webbrowser

from core.manager import DataManager

# Register Japanese font if exists
current_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(current_dir, "data", "font.ttf")
if os.path.exists(font_path):
    LabelBase.register(name='Japanese', fn_regular=font_path)

class MemberListScreen(Screen):
    pass

class VideoListScreen(Screen):
    pass

class MainScreenManager(ScreenManager):
    pass

class HoloNijiApp(App):
    def build(self):
        # Database path adjustment for Android
        # On Android, writeable data should be in app's private directory
        db_dir = os.path.join(current_dir, "data")
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self.data_manager = DataManager(os.path.join(db_dir, "app.db"))
        
        # Load KV file
        kv_path = os.path.join(current_dir, "style.kv")
        self.root = Builder.load_file(kv_path)
            
        return self.root

    def open_link(self, url):
        if url:
            webbrowser.open(url)

    def on_start(self):
        # Schedule update
        Clock.schedule_once(self.update_data, 1)
        # Clock.schedule_interval(self.update_data, 3600) # 1 hour

    def update_data(self, dt):
        # Run async update
        asyncio.create_task(self.async_update())

    async def async_update(self):
        print("Mobile: Starting update...")
        try:
            await self.data_manager.update_all_data()
            print("Mobile: Update complete.")
        except Exception as e:
            print(f"Mobile: Update failed: {e}")
        
        # UI Refresh must happen on main thread
        Clock.schedule_once(lambda dt: self.refresh_ui())

    def refresh_ui(self):
        # Refresh member list
        members = self.data_manager.db.get_all_members()
        member_data = [{
            'text': f"[{m.group_name}] {m.name}", 
            'secondary_text': m.generation,
            'url': m.youtube_url
        } for m in members]
        
        screen_manager = self.root.ids.screen_manager
        member_screen = screen_manager.get_screen('members')
        member_screen.ids.member_list.data = member_data

        # Refresh video list
        videos = self.data_manager.db.get_videos(limit=50)
        video_data = [{
            'text': v.title, 
            'secondary_text': f"{v.published_at.strftime('%Y/%m/%d %H:%M')} - {v.channel_id}",
            'url': v.url
        } for v in videos]
        
        video_screen = screen_manager.get_screen('videos')
        video_screen.ids.video_list.data = video_data

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    
    app = HoloNijiApp()
    try:
        loop.run_until_complete(app.async_run(async_lib='asyncio'))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
