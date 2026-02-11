from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                               QLabel, QHBoxLayout, QPushButton, QFrame)
from PySide6.QtCore import Qt, QSize
from ui.tabs.videos import VideosTab

class FavoritesTab(VideosTab):
    def __init__(self, data_manager, group_filter: str = None):
        # Initialize parent with group_filter
        super().__init__(data_manager, group_filter)

    def refresh_list(self):
        self.list_widget.clear()
        
        # Get videos from favorite members with optional group filter
        conn = self.data_manager.db._get_connection()
        cursor = conn.cursor()
        
        if self.group_filter:
            cursor.execute('''
                SELECT v.* FROM videos v
                JOIN members m ON v.channel_id = m.channel_id
                WHERE m.is_favorite = 1 AND m.group_name = ?
                ORDER BY v.published_at DESC
                LIMIT 50
            ''', (self.group_filter,))
        else:
            cursor.execute('''
                SELECT v.* FROM videos v
                JOIN members m ON v.channel_id = m.channel_id
                WHERE m.is_favorite = 1
                ORDER BY v.published_at DESC
                LIMIT 50
            ''')
        rows = cursor.fetchall()
        conn.close()
        
        from models.video import Video
        videos = [Video(*row) for row in rows]
        
        if not videos:
            item = QListWidgetItem("No videos from favorites or no favorites set.")
            self.list_widget.addItem(item)
            return

        for video in videos:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 110))
            widget = self.create_video_widget(video)
            self.list_widget.setItemWidget(item, widget)

