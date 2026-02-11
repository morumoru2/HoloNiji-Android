from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QGroupBox, QGridLayout, QFrame, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.manager import DataManager
from collections import defaultdict


class StatsTab(QWidget):
    """
    Statistics dashboard tab showing various metrics about VTubers.
    """
    
    def __init__(self, data_manager: DataManager, group_filter: str = None):
        super().__init__()
        self.data_manager = data_manager
        self.group_filter = group_filter
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("📊 統計ダッシュボード")
        header.setFont(QFont("Yu Gothic UI", 16, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #e94560; padding: 10px;")
        layout.addWidget(header)
        
        # Scroll area for stats
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        container = QWidget()
        self.stats_layout = QVBoxLayout(container)
        self.stats_layout.setSpacing(15)
        scroll.setWidget(container)
        
        self.refresh_stats()
    
    def refresh_stats(self):
        """Refresh all statistics"""
        # Clear existing widgets
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get members based on group filter
        if self.group_filter:
            members = self.data_manager.db.get_members_by_group(self.group_filter)
            title_suffix = f" ({self.group_filter})"
        else:
            members = self.data_manager.db.get_all_members()
            title_suffix = " (全グループ)"
        
        # Create stats cards
        self.create_overview_card(members, title_suffix)
        self.create_generation_breakdown(members)
        self.create_video_stats(members)
        self.create_active_members_ranking(members)
        
        self.stats_layout.addStretch()
    
    def create_overview_card(self, members, title_suffix):
        """Create overview statistics card"""
        group_box = QGroupBox(f"📈 全体統計{title_suffix}")
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
        
        layout = QGridLayout(group_box)
        layout.setSpacing(10)
        
        # Count members by group
        holo_count = len([m for m in members if m.group_name == "hololive"])
        niji_count = len([m for m in members if m.group_name == "nijisanji"])
        total_count = len(members)
        
        # Favorite count
        fav_count = len([m for m in members if m.is_favorite])
        
        # Video count
        if self.group_filter:
            videos = self.data_manager.db.get_videos_by_group(self.group_filter, limit=999999)
        else:
            videos = self.data_manager.db.get_videos(limit=999999)
        video_count = len(videos)
        
        # Collab count
        collab_count = len([v for v in videos if v.is_collab])
        
        # Create stat cards
        row = 0
        col = 0
        cols = 3
        
        stats_data = [
            ("👥 総メンバー数", str(total_count), "#4ade80"),
            ("🔷 ホロライブ", str(holo_count), "#60a5fa"),
            ("🔶 にじさんじ", str(niji_count), "#facc15"),
            ("⭐ お気に入り", str(fav_count), "#fbbf24"),
            ("🎬 総動画数", str(video_count), "#a78bfa"),
            ("🤝 コラボ数", str(collab_count), "#fb7185"),
        ]
        
        for label, value, color in stats_data:
            card = self.create_stat_card(label, value, color)
            layout.addWidget(card, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1
        
        self.stats_layout.addWidget(group_box)
    
    def create_stat_card(self, label, value, color):
        """Create a single stat card"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #16213e;
                border-left: 4px solid {color};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        frame.setMinimumHeight(80)
        
        layout = QVBoxLayout(frame)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        # Label
        text_label = QLabel(label)
        text_label.setFont(QFont("Yu Gothic UI", 10))
        text_label.setStyleSheet("color: #aaa;")
        text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(text_label)
        
        return frame
    
    def create_generation_breakdown(self, members):
        """Create generation breakdown statistics"""
        group_box = QGroupBox("🎭 世代別メンバー数")
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
        
        layout = QVBoxLayout(group_box)
        
        # Count by generation
        gen_counts = defaultdict(int)
        for m in members:
            gen_key = f"[{m.group_name}] {m.generation}"
            gen_counts[gen_key] += 1
        
        # Sort by count
        sorted_gens = sorted(gen_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Display top 10
        grid = QGridLayout()
        grid.setSpacing(10)
        
        row = 0
        col = 0
        cols = 2
        
        for gen_key, count in sorted_gens[:10]:
            # Generation label
            gen_label = QLabel(gen_key)
            gen_label.setStyleSheet("color: #eaeaea; font-weight: bold;")
            grid.addWidget(gen_label, row, col * 2)
            
            # Count
            count_label = QLabel(f"{count}人")
            count_label.setStyleSheet("color: #4ade80;")
            count_label.setAlignment(Qt.AlignRight)
            grid.addWidget(count_label, row, col * 2 + 1)
            
            col += 1
            if col >= cols:
                col = 0
                row += 1
        
        layout.addLayout(grid)
        self.stats_layout.addWidget(group_box)
    
    def create_video_stats(self, members):
        """Create video-related statistics"""
        group_box = QGroupBox("📹 動画統計 (全投稿数ランキング)")
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
        
        layout = QVBoxLayout(group_box)
        layout.setSpacing(10)
        
        # Get video data per member
        member_video_counts = []
        for m in members:
            # We use a reasonably large limit to get a good estimate of activity
            videos = self.data_manager.db.get_videos_by_channel(m.channel_id, limit=2000)
            member_video_counts.append((m.name, len(videos), m.group_name))
        
        # Sort by video count
        member_video_counts.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate average
        if member_video_counts:
            avg_videos = sum(count for _, count, _ in member_video_counts) / len(member_video_counts)
        else:
            avg_videos = 0
        
        # Display average
        avg_label = QLabel(f"📈 メンバー平均投稿数: {avg_videos:.1f} 本")
        avg_label.setStyleSheet("color: #4ade80; font-size: 14px; font-weight: bold; padding: 5px;")
        avg_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(avg_label)
        
        # Ranking Grid
        grid = QGridLayout()
        grid.setSpacing(8)
        
        # Header for ranking
        header_rank = QLabel("順位")
        header_name = QLabel("メンバー名")
        header_count = QLabel("投稿数")
        for h in [header_rank, header_name, header_count]:
            h.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        
        grid.addWidget(header_rank, 0, 0)
        grid.addWidget(header_name, 0, 1)
        grid.addWidget(header_count, 0, 2)
        
        # Top 10 ranking
        for idx, (name, count, group) in enumerate(member_video_counts[:10], start=1):
            rank_label = QLabel(f"#{idx}")
            rank_label.setStyleSheet("color: #fbbf24; font-weight: bold;")
            grid.addWidget(rank_label, idx, 0)
            
            name_label = QLabel(f"{name} [{group}]")
            name_label.setStyleSheet("color: #eaeaea;")
            grid.addWidget(name_label, idx, 1)
            
            count_label = QLabel(f"{count} 本")
            count_label.setStyleSheet("color: #4ade80;")
            count_label.setAlignment(Qt.AlignRight)
            grid.addWidget(count_label, idx, 2)
            
        layout.addLayout(grid)
        
        self.stats_layout.addWidget(group_box)
    
    def create_active_members_ranking(self, members):
        """Create ranking of most active members based on recent videos"""
        group_box = QGroupBox("🏆 活動ランキング (最近の動画数)")
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
        
        layout = QVBoxLayout(group_box)
        
        # Get recent video counts (last 50 per member)
        member_activity = []
        for m in members:
            videos = self.data_manager.db.get_videos_by_channel(m.channel_id, limit=20)
            member_activity.append((m.name, len(videos), m.group_name))
        
        # Sort by activity
        member_activity.sort(key=lambda x: x[1], reverse=True)
        
        # Display top 10
        grid = QGridLayout()
        grid.setSpacing(5)
        
        for idx, (name, count, group) in enumerate(member_activity[:10], start=1):
            # Rank
            rank_label = QLabel(f"#{idx}")
            rank_label.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 14px;")
            rank_label.setFixedWidth(40)
            grid.addWidget(rank_label, idx - 1, 0)
            
            # Name
            name_label = QLabel(name)
            name_label.setStyleSheet("color: #eaeaea;")
            grid.addWidget(name_label, idx - 1, 1)
            
            # Group
            group_label = QLabel(f"[{group}]")
            group_label.setStyleSheet("color: #888; font-size: 10px;")
            grid.addWidget(group_label, idx - 1, 2)
            
            # Count
            count_label = QLabel(f"{count}本")
            count_label.setStyleSheet("color: #4ade80;")
            count_label.setAlignment(Qt.AlignRight)
            grid.addWidget(count_label, idx - 1, 3)
        
        layout.addLayout(grid)
        self.stats_layout.addWidget(group_box)
    
    def refresh_list(self):
        """Refresh the statistics (compatibility method)"""
        self.refresh_stats()
