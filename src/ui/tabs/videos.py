from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                               QLabel, QHBoxLayout, QPushButton, QFrame, QAbstractItemView)
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QFont
from ui.components.async_image import AsyncImageLoader
from core.manager import DataManager

class VideosTab(QWidget):
    def __init__(self, data_manager: DataManager, group_filter: str = None):
        super().__init__()
        self.data_manager = data_manager
        self.group_filter = group_filter  # 'hololive', 'nijisanji', or None for all
        self.init_ui()


    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Custom Header Layout
        top_layout = QHBoxLayout()
        
        # DB Refresh
        refresh_btn = QPushButton("🔄 表示更新")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setToolTip("データベースからリストを再読み込みします")
        refresh_btn.clicked.connect(self.refresh_list)
        top_layout.addWidget(refresh_btn)
        
        # Web Fetch
        self.fetch_btn = QPushButton("☁️ Webから最新取得")
        self.fetch_btn.setCursor(Qt.PointingHandCursor)
        self.fetch_btn.setStyleSheet("background-color: #2a2a40; color: #4cc9f0; border: 1px solid #4cc9f0;")
        self.fetch_btn.setToolTip("YouTubeから最新データを取得します（時間がかかります）")
        self.fetch_btn.clicked.connect(self.start_web_fetch)
        top_layout.addWidget(self.fetch_btn)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # Progress Bar (Hidden by default)
        from PySide6.QtWidgets import QProgressBar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminate
        self.progress.setVisible(False)
        self.progress.setStyleSheet("QProgressBar { height: 4px; }")
        layout.addWidget(self.progress)

        # Video List
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(160, 90))
        self.list_widget.setSpacing(5)
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection) # Disable blue selection
        layout.addWidget(self.list_widget)

        self.refresh_list()

    def start_web_fetch(self):
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("取得中...")
        self.progress.setVisible(True)
        
        from PySide6.QtCore import QThread, Signal
        import asyncio
        
        class UpdateWorker(QThread):
            finished = Signal()
            
            def __init__(self, manager, group_filter):
                super().__init__()
                self.manager = manager
                self.group_filter = group_filter
                
            def run(self):
                # Run async update in new loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.manager.update_recent_videos(self.group_filter))
                loop.close()
                self.finished.emit()
        
        self.worker = UpdateWorker(self.data_manager, self.group_filter)
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.start()
        
    def on_fetch_finished(self):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("☁️ Webから最新取得")
        self.progress.setVisible(False)
        self.refresh_list()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "完了", "最新データの取得が完了しました。")

    def refresh_list(self):
        self.list_widget.clear()
        
        # Get videos based on group filter
        if self.group_filter:
            videos = self.data_manager.db.get_videos_by_group(self.group_filter, limit=50)
        else:
            videos = self.data_manager.db.get_videos(limit=50)
        
        for video in videos:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 110)) # Height for custom widget
            
            # Custom Widget
            widget = self.create_video_widget(video)
            self.list_widget.setItemWidget(item, widget)


    def create_video_widget(self, video):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Thumbnail
        thumb = AsyncImageLoader(video.thumbnail_url, 160, 90)
        layout.addWidget(thumb)
        
        # Info
        info_layout = QVBoxLayout()
        
        title = QLabel(video.title)
        title.setFont(QFont("Arial", 11, QFont.Bold))
        title.setWordWrap(True)
        info_layout.addWidget(title)
        
        details = QLabel(f"{video.published_at.strftime('%Y-%m-%d %H:%M')}")
        details.setStyleSheet("color: gray;")
        info_layout.addWidget(details)
        
        layout.addLayout(info_layout)
        layout.setStretch(1, 1) # Expand info part
        
        # Buttons
        video_url = video.url
        watch_btn = QPushButton("▶ YouTubeで視聴")
        watch_btn.setCursor(Qt.PointingHandCursor)
        watch_btn.setStyleSheet("""
            QPushButton {
                 background-color: #e94560; 
                 color: white; 
                 border-radius: 6px;
                 padding: 8px 12px;
                 font-weight: bold;
            }
            QPushButton:hover { background-color: #ff6b8a; }
        """)
        watch_btn.clicked.connect(lambda checked, url=video_url: QDesktopServices.openUrl(QUrl(url)))
        
        btn_layout = QVBoxLayout()
        btn_layout.addWidget(watch_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return frame
