from PySide6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QFrame, 
                               QGridLayout, QLabel, QPushButton, QLineEdit, QHBoxLayout)
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from ui.components.async_image import AsyncImageLoader
from core.manager import DataManager

class ChannelsTab(QWidget):
    def __init__(self, data_manager: DataManager, group_filter: str = None):
        super().__init__()
        self.data_manager = data_manager
        self.group_filter = group_filter  # 'hololive', 'nijisanji', or None for all
        self.init_ui()


    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 メンバーを検索...")
        self.search_bar.textChanged.connect(self.filter_members)
        layout.addWidget(self.search_bar)

        # Scroll Area for Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.scroll.setWidget(self.container)
        
        self.members_widgets = {} # Keep refs
        self.refresh_list()

    def refresh_list(self):
        # Stop timer if running
        if hasattr(self, 'batch_timer') and self.batch_timer.isActive():
            self.batch_timer.stop()
            
        # Clear existing
        for i in reversed(range(self.grid_layout.count())): 
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        self.members_widgets = {}

        # Get members based on group filter
        if self.group_filter:
            self.all_members = self.data_manager.db.get_members_by_group(self.group_filter)
        else:
            self.all_members = self.data_manager.db.get_all_members()
            
        self.current_load_index = 0
        self.grid_row, self.grid_col = 0, 0
        
        # Start batch loading
        if not hasattr(self, 'batch_timer'):
            self.batch_timer = QTimer(self)
            self.batch_timer.timeout.connect(self.load_next_batch)
        
        self.batch_timer.start(30) # 30ms interval for better responsiveness
        
    def load_next_batch(self):
        BATCH_SIZE = 5
        end_index = min(self.current_load_index + BATCH_SIZE, len(self.all_members))
        batch = self.all_members[self.current_load_index:end_index]
        
        cols = 4
        
        for m in batch:
            card = self.create_member_card(m)
            self.members_widgets[m.channel_id] = (card, m.name.lower())
            self.grid_layout.addWidget(card, self.grid_row, self.grid_col)
            
            self.grid_col += 1
            if self.grid_col >= cols:
                self.grid_col = 0
                self.grid_row += 1
        
        self.current_load_index = end_index
        
        if self.current_load_index >= len(self.all_members):
            self.batch_timer.stop()


    def create_member_card(self, member):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("QFrame { background-color: #16213e; border: 1px solid #3a3a5e; border-radius: 8px; padding: 5px; }")
        frame.setFixedSize(160, 200)
        
        layout = QVBoxLayout(frame)
        
        # Icon
        icon_url = member.icon_url if member.icon_url else ""
        img = AsyncImageLoader(icon_url, 80, 80)
        layout.addWidget(img, alignment=Qt.AlignCenter)
        
        # Name
        lbl = QLabel(member.name)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-weight: bold; color: #eaeaea;")
        layout.addWidget(lbl)
        
        # Group Label
        group_lbl = QLabel(f"[{member.group_name}]")
        group_lbl.setAlignment(Qt.AlignCenter)
        group_lbl.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(group_lbl)
        
        # Button Layout
        btn_layout = QHBoxLayout()
        
        # Link Button
        btn = QPushButton("📺 視聴")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("background-color: #e94560; color: white; border-radius: 6px; padding: 6px;")
        yt_url = member.youtube_url
        btn.clicked.connect(lambda checked, url=yt_url: QDesktopServices.openUrl(QUrl(url)))
        btn_layout.addWidget(btn)
        
        # Favorite Button
        fav_btn = QPushButton("★" if member.is_favorite else "☆")
        fav_btn.setCursor(Qt.PointingHandCursor)
        fav_btn.setCheckable(True)
        fav_btn.setChecked(member.is_favorite)
        fav_btn.setObjectName("favoriteBtn")
        fav_btn.setStyleSheet(f"color: {'#fbbf24' if member.is_favorite else '#666'}; font-size: 18px; background: transparent;")
        fav_btn.clicked.connect(lambda checked, m=member, b=fav_btn: self.toggle_favorite(m, b))
        
        btn_layout.addWidget(fav_btn)
        
        layout.addLayout(btn_layout)
        
        return frame

    def toggle_favorite(self, member, btn):
        new_state = not member.is_favorite
        member.is_favorite = new_state
        self.data_manager.db.toggle_favorite(member.channel_id, new_state)
        
        # Update UI
        btn.setText("★" if new_state else "☆")
        btn.setStyleSheet(f"color: {'#fbbf24' if new_state else '#666'}; font-size: 18px;")

    def filter_members(self, text):
        text = text.lower()
        cols = 4
        visible_widgets = []
        
        # Hide all first
        for _, (widget, name) in self.members_widgets.items():
            widget.setVisible(name.find(text) != -1)
            if widget.isVisible():
                visible_widgets.append(widget)
        
        # Re-layout visible ones (optional, simple hiding works for grid but leaves gaps? 
        # Grid layout manages gaps poorly when items serve as hidden.
        # Ideally we re-add them.
        
        # Simple implementation: basic hiding, might enable gaps.
        # Better: Clear layout and add back visible.
        
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
            
        row, col = 0, 0
        for w in visible_widgets:
            self.grid_layout.addWidget(w, row, col)
            w.setVisible(True) # Ensure visible
            col += 1
            if col >= cols:
                col = 0
                row += 1
