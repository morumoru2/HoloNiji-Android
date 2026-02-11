from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QListWidget, QListWidgetItem, QFrame,
                               QScrollArea, QGridLayout, QLineEdit, QGroupBox)
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from ui.components.async_image import AsyncImageLoader
from core.manager import DataManager
from collections import defaultdict

class SNSTab(QWidget):
    def __init__(self, data_manager: DataManager, group_filter: str = None):
        super().__init__()
        self.data_manager = data_manager
        self.group_filter = group_filter  # 'hololive', 'nijisanji', or None for all
        self._is_refreshing = False
        self.init_ui()


    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with Official Links
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("🔗 公式リンク:"))
        
        holo_btn = QPushButton("🔷 ホロライブ公式サイト")
        holo_btn.setCursor(Qt.PointingHandCursor)
        holo_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://hololive.hololivepro.com/talents")))
        header_layout.addWidget(holo_btn)
        
        niji_btn = QPushButton("🔶 にじさんじ公式サイト")
        niji_btn.setCursor(Qt.PointingHandCursor)
        niji_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.nijisanji.jp/talents")))
        header_layout.addWidget(niji_btn)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Search
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 メンバー名で検索...")
        self.search_bar.textChanged.connect(self.filter_members)
        search_layout.addWidget(self.search_bar)
        layout.addLayout(search_layout)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        self.container = QWidget()
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setSpacing(15)
        self.scroll.setWidget(self.container)
        
        self.all_cards = []  # (card, name, generation)
        # Deferred initial refresh
        QTimer.singleShot(100, self.refresh_list)

    def refresh_list(self):
        if self._is_refreshing:
            return
        self._is_refreshing = True
        
        try:
            # Clear existing
            while self.main_layout.count():
                item = self.main_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.all_cards = []

            # Get members based on group filter
            if self.group_filter:
                members = self.data_manager.db.get_members_by_group(self.group_filter)
            else:
                members = self.data_manager.db.get_all_members()
            
            # Group by generation
            groups = defaultdict(list)
            for m in members:
                gen_key = f"[{m.group_name}] {m.generation}"
                groups[gen_key].append(m)
            
            # Sort groups
            sorted_groups = sorted(groups.keys())
            
            for gen_key in sorted_groups:
                group_box = QGroupBox(gen_key)
                group_box.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        font-size: 14px;
                        color: #e94560;
                        border: 2px solid #3a3a5e;
                        border-radius: 8px;
                        margin-top: 15px;
                        padding-top: 15px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 15px;
                        padding: 0 5px;
                    }
                """)
                group_layout = QGridLayout(group_box)
                group_layout.setSpacing(10)
                
                row, col = 0, 0
                cols = 3
                
                for m in groups[gen_key]:
                    card = self.create_sns_card(m)
                    self.all_cards.append((card, m.name.lower(), gen_key))
                    group_layout.addWidget(card, row, col)
                    
                    col += 1
                    if col >= cols:
                        col = 0
                        row += 1
                
                self.main_layout.addWidget(group_box)
            
            self.main_layout.addStretch()
        finally:
            self._is_refreshing = False

    def create_sns_card(self, member):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        frame.setFixedSize(320, 140)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Icon
        icon_url = member.icon_url if member.icon_url else ""
        img = AsyncImageLoader(icon_url, 80, 80)
        img.setStyleSheet("border-radius: 40px;")
        layout.addWidget(img)
        
        # Info and Buttons
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # Name
        name_lbl = QLabel(member.name)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #eaeaea;")
        name_lbl.setWordWrap(True)
        info_layout.addWidget(name_lbl)
        
        # SNS Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        
        # Store URLs to avoid closure issues
        yt_url = member.youtube_url
        tw_url = member.twitter_url
        
        if yt_url:
            yt_btn = QPushButton("📺")
            yt_btn.setFixedSize(40, 30)
            yt_btn.setToolTip("YouTubeを開く")
            yt_btn.setStyleSheet("background-color: #ff0000; color: white; border-radius: 6px;")
            yt_btn.clicked.connect(lambda checked, url=yt_url: QDesktopServices.openUrl(QUrl(url)))
            btn_layout.addWidget(yt_btn)
        
        if tw_url:
            tw_btn = QPushButton("🐦")
            tw_btn.setFixedSize(40, 30)
            tw_btn.setToolTip("X/Twitterを開く")
            tw_btn.setStyleSheet("background-color: #1da1f2; color: white; border-radius: 6px;")
            tw_btn.clicked.connect(lambda checked, url=tw_url: QDesktopServices.openUrl(QUrl(url)))
            btn_layout.addWidget(tw_btn)
        
        btn_layout.addStretch()
        info_layout.addLayout(btn_layout)
        layout.addLayout(info_layout)
        
        return frame

    def filter_members(self, text):
        text = text.lower()
        
        for card, name, gen_key in self.all_cards:
            visible = text in name or text in gen_key.lower()
            card.setVisible(visible)

