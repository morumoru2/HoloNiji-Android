from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QCalendarWidget, QListWidget, QListWidgetItem, 
                                QFrame, QPushButton, QSplitter, QGroupBox)
from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QFont, QDesktopServices
from core.manager import DataManager
from datetime import datetime, timedelta
import re


class ScheduleTab(QWidget):
    """
    Schedule tab showing upcoming streams and videos.
    Note: This is a basic implementation. Full YouTube API integration 
    would require API keys and additional setup.
    """
    
    def __init__(self, data_manager: DataManager, group_filter: str = None):
        super().__init__()
        self.data_manager = data_manager
        self.group_filter = group_filter
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("📅 配信スケジュール")
        header.setFont(QFont("Yu Gothic UI", 16, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #e94560; padding: 10px;")
        layout.addWidget(header)
        
        # Info message
        info_box = QFrame()
        info_box.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border-left: 4px solid #60a5fa;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        info_layout = QVBoxLayout(info_box)
        info_label = QLabel(
            "ℹ️ 配信スケジュール機能\n\n"
            "この機能は最近の動画情報から配信スケジュールを表示します。\n"
            "より正確なスケジュール情報を取得するには、YouTube API キーが必要です。\n"
            "現在は、最近公開された動画の情報を日付別に表示しています。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaa; font-size: 11px;")
        info_layout.addWidget(info_label)
        layout.addWidget(info_box)
        
        # Splitter for calendar and list
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Calendar
        self.calendar = QCalendarWidget()
        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: #16213e;
                color: white;
            }
            QCalendarWidget QToolButton {
                color: white;
                background-color: #1a1a2e;
            }
            QCalendarWidget QMenu {
                background-color: #1a1a2e;
                color: white;
            }
            QCalendarWidget QSpinBox {
                background-color: #1a1a2e;
                color: white;
            }
            QCalendarWidget QTableView {
                background-color: #16213e;
                selection-background-color: #e94560;
            }
        """)
        self.calendar.selectionChanged.connect(self.on_date_selected)
        splitter.addWidget(self.calendar)
        
        # Schedule list
        schedule_container = QWidget()
        schedule_layout = QVBoxLayout(schedule_container)
        schedule_layout.setContentsMargins(0, 0, 0, 0)
        
        self.date_label = QLabel()
        self.date_label.setFont(QFont("Yu Gothic UI", 13, QFont.Bold))
        self.date_label.setStyleSheet("color: #e94560; padding: 10px;")
        schedule_layout.addWidget(self.date_label)
        
        self.schedule_list = QListWidget()
        self.schedule_list.setStyleSheet("""
            QListWidget {
                background-color: #16213e;
                border: 1px solid #3a3a5e;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 5px;
            }
        """)
        schedule_layout.addWidget(self.schedule_list)
        
        splitter.addWidget(schedule_container)
        splitter.setSizes([300, 500])
        
        self.refresh_schedule()
    
    def refresh_schedule(self):
        """Refresh schedule data"""
        # Select today's date
        self.calendar.setSelectedDate(QDate.currentDate())
        self.on_date_selected()
    
    def on_date_selected(self):
        """Handle date selection"""
        selected_date = self.calendar.selectedDate()
        self.date_label.setText(f"📅 {selected_date.toString('yyyy年MM月dd日')} のスケジュール")
        
        # Clear list
        self.schedule_list.clear()
        
        # Get videos for selected date
        # Convert QDate to datetime
        selected_datetime = datetime(
            selected_date.year(),
            selected_date.month(),
            selected_date.day()
        )
        
        # Get all videos
        if self.group_filter:
            videos = self.data_manager.db.get_videos_by_group(self.group_filter, limit=500)
        else:
            videos = self.data_manager.db.get_videos(limit=500)
        
        # Filter videos by date
        day_videos = []
        for video in videos:
            video_date = video.published_at.date()
            selected_date_py = selected_datetime.date()
            
            if video_date == selected_date_py:
                day_videos.append(video)
        
        # Sort by time
        day_videos.sort(key=lambda v: v.published_at, reverse=True)
        
        if not day_videos:
            item = QListWidgetItem("この日の配信情報はありません")
            item.setForeground(Qt.gray)
            self.schedule_list.addItem(item)
            return
        
        # Get member info for each video
        members_dict = {}
        if self.group_filter:
            members = self.data_manager.db.get_members_by_group(self.group_filter)
        else:
            members = self.data_manager.db.get_all_members()
        
        # Create mapping by ID and also by slug/name just in case for mixed ID scenarios
        for m in members:
            members_dict[m.channel_id] = m
            # If Nijisanji and using niji_ slug as channel_id temporarily
            if m.group_name == 'nijisanji':
                # Map by name as well to handle cases where video might have a different ID format
                members_dict[m.name] = m 
        
        # Display videos
        for video in day_videos:
            item = QListWidgetItem(self.schedule_list)
            from PySide6.QtCore import QSize
            item.setSizeHint(QSize(0, 100)) # Increased height for better visibility
            
            # Find member by channel_id or channel_title (if ID resolution is in progress)
            member = members_dict.get(video.channel_id)
            
            widget = self.create_schedule_item(video, member)
            self.schedule_list.setItemWidget(item, widget)
    
    def create_schedule_item(self, video, member):
        """Create a schedule item widget"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 1px solid #3a3a5e;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Time
        time_label = QLabel(video.published_at.strftime('%H:%M'))
        time_label.setFont(QFont("Arial", 16, QFont.Bold))
        time_label.setStyleSheet("color: #4ade80;")
        time_label.setFixedWidth(65)
        layout.addWidget(time_label)
        
        # Icon
        from ui.components.async_image import AsyncImageLoader
        icon_url = member.icon_url if member else None
        icon = AsyncImageLoader(icon_url, 60, 60)
        icon.setFixedSize(60, 60)
        layout.addWidget(icon)
        
        # Details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(2)
        
        # Member name (Emphasized)
        if member:
            group_color = "#60a5fa" if member.group_name == "hololive" else "#fbbf24"
            member_label = QLabel(f"👤 {member.name}")
            member_label.setFont(QFont("Yu Gothic UI", 12, QFont.Bold))
            member_label.setStyleSheet(f"color: {group_color};")
            details_layout.addWidget(member_label)
            
            group_label = QLabel(f"[{member.group_name}]")
            group_label.setStyleSheet("color: #888; font-size: 10px; margin-top: -5px;")
            details_layout.addWidget(group_label)
        else:
            unknown_label = QLabel(f"👤 {video.channel_title or '不明な配信者'}")
            unknown_label.setStyleSheet("color: #aaa; font-style: italic;")
            details_layout.addWidget(unknown_label)
        
        # Title
        title = QLabel(video.title)
        title.setFont(QFont("Yu Gothic UI", 10))
        title.setStyleSheet("color: #eaeaea;")
        title.setWordWrap(True)
        title.setMaximumHeight(40)
        details_layout.addWidget(title)
        
        layout.addLayout(details_layout, 1)
        
        # Watch button
        watch_btn = QPushButton("▶ 視聴")
        watch_btn.setFixedSize(80, 30)
        watch_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94560;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6b8a;
            }
        """)
        watch_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(video.url)))
        layout.addWidget(watch_btn)
        
        return frame
    
    def refresh_list(self):
        """Refresh the schedule (compatibility method)"""
        self.refresh_schedule()
