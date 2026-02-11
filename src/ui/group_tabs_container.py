from PySide6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from core.manager import DataManager
from ui.tabs.channels import ChannelsTab
from ui.tabs.videos import VideosTab
from ui.tabs.collabs import CollabsTab
from ui.tabs.favorites import FavoritesTab
from ui.tabs.sns import SNSTab
from ui.tabs.stats_tab import StatsTab
from ui.tabs.schedule_tab import ScheduleTab




class GroupTabsContainer(QWidget):
    """
    A container widget that holds all tabs for a specific group (hololive or nijisanji).
    Each container has: Channels, Videos, Collabs, Favorites, and SNS tabs.
    """
    
    def __init__(self, data_manager: DataManager, group_name: str):
        """
        Initialize the group tabs container.
        
        Args:
            data_manager: The data manager instance
            group_name: The group name ('hololive' or 'nijisanji')
        """
        super().__init__()
        self.data_manager = data_manager
        self.group_name = group_name
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a tab widget for this group
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create all tabs with group filter
        self.stats_tab = StatsTab(self.data_manager, group_filter=self.group_name)
        self.tabs.addTab(self.stats_tab, "📊 統計")
        
        self.schedule_tab = ScheduleTab(self.data_manager, group_filter=self.group_name)
        self.tabs.addTab(self.schedule_tab, "📅 スケジュール")
        
        self.channels_tab = ChannelsTab(self.data_manager, group_filter=self.group_name)
        self.tabs.addTab(self.channels_tab, "📺 チャンネル")
        
        self.videos_tab = VideosTab(self.data_manager, group_filter=self.group_name)
        self.tabs.addTab(self.videos_tab, "🎬 最新動画")
        
        self.collabs_tab = CollabsTab(self.data_manager, group_filter=self.group_name)
        self.tabs.addTab(self.collabs_tab, "🤝 コラボ")
        
        self.favorites_tab = FavoritesTab(self.data_manager, group_filter=self.group_name)
        self.tabs.addTab(self.favorites_tab, "⭐ お気に入り")
        
        self.sns_tab = SNSTab(self.data_manager, group_filter=self.group_name)
        self.tabs.addTab(self.sns_tab, "🔗 SNS")
        
        # Connect tab change signal
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Track loaded state
        self.tab_loaded = {} # widget -> bool
        
        # Delay initial refresh to ensure UI is ready
        # Use QTimer to defer the refresh until after the UI is fully initialized
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.refresh_all_tabs)



    
    def refresh_all_tabs(self):
        """Reset loaded state and refresh current tab only (Lazy Loading)"""
        # Mark all as not loaded
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            self.tab_loaded[widget] = False
            
        # Load current tab immediately
        current = self.tabs.currentWidget()
        if current:
            self._refresh_tab(current)

    def on_tab_changed(self, index):
        """Handle tab change to load data if needed"""
        widget = self.tabs.widget(index)
        if not self.tab_loaded.get(widget, False):
            self._refresh_tab(widget)

    def _refresh_tab(self, widget):
        """Refresh specific tab"""
        if hasattr(widget, 'refresh_list'):
            widget.refresh_list()
        self.tab_loaded[widget] = True


