from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QTabWidget, QLabel, QListWidget, QListWidgetItem, 
                               QHBoxLayout, QPushButton, QScrollArea, QFrame,
                               QLineEdit, QGroupBox, QSplitter, QComboBox, 
                               QMenuBar, QMenu, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QAction
from core.manager import DataManager
from core.export_manager import ExportManager
from models.member import Member
from ui.group_tabs_container import GroupTabsContainer
from ui.tabs.channels import ChannelsTab
from ui.tabs.videos import VideosTab
from ui.tabs.collabs import CollabsTab
from ui.notifications import NotificationManager
import os
import asyncio
import logging
from datetime import datetime
from ui.log_viewer_dialog import LogViewerDialog # Import the new dialog

class Worker(QThread):
    finished = Signal(bool) # Modified to emit a boolean indicating success
    
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        # Setup logger for worker thread
        logger = logging.getLogger(__name__)
        logger.info("Worker thread started")
        
        success = True # Assume success initially
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("Calling update_all_data")
            loop.run_until_complete(self.manager.update_all_data())
            loop.close()
            logger.info("Worker thread finished successfully")
        except Exception as e:
            logger.error(f"Error in data update worker: {e}", exc_info=True)
            success = False # Set to False on error
        finally:
            self.finished.emit(success) # Emit success status

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ホロライブ・にじさんじ 統合アプリ")
        self.resize(1280, 800)
        
        # Load stylesheet
        self.load_stylesheet()
        
        self.data_manager = DataManager()
        self.export_manager = ExportManager(self.data_manager.db)
        self.api_key = ""
        
        # Setup notification manager
        self.notification_manager = NotificationManager(self)
        
        # Theme state
        self.current_theme = "dark"  # default theme
        
        # Menu Bar
        self.create_menu_bar()
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Header
        header = QLabel("🎮 ホロライブ・にじさんじ 統合アプリ")
        header.setObjectName("headerLabel")
        header.setFont(QFont("Yu Gothic UI", 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)
        
        # API Key Settings Bar
        settings_frame = QFrame()
        settings_layout = QHBoxLayout(settings_frame)
        settings_layout.addWidget(QLabel("YouTube APIキー:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("APIキーを入力（オプション）")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.textChanged.connect(self.on_api_key_changed)
        settings_layout.addWidget(self.api_key_input)
        
        self.api_status_label = QLabel("(未設定)")
        self.api_status_label.setObjectName("subLabel")
        settings_layout.addWidget(self.api_status_label)
        
        refresh_btn = QPushButton("🔄 全データ更新")
        refresh_btn.clicked.connect(self.refresh_data)
        settings_layout.addWidget(refresh_btn)
        
        main_layout.addWidget(settings_frame)
        
        # Main Tabs (2-tier structure)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Hololive Group Tab
        self.hololive_container = GroupTabsContainer(self.data_manager, "hololive")
        self.tabs.addTab(self.hololive_container, "🔷 ホロライブ")
        
        # Nijisanji Group Tab
        self.nijisanji_container = GroupTabsContainer(self.data_manager, "nijisanji")
        self.tabs.addTab(self.nijisanji_container, "🔶 にじさんじ")
        
        # Integrated View Tab (for backward compatibility)
        self.integrated_tab = QWidget()
        self.setup_integrated_tab()
        self.tabs.addTab(self.integrated_tab, "🌐 統合ビュー")

        # Status Bar
        self.status_label = QLabel("準備完了")
        self.statusBar().addWidget(self.status_label)
        
        # Initial Data Fetch
        # DISABLED AUTOMATIC UPDATE ON STARTUP TO PREVENT FREEZE
        # self.refresh_data()

        # Periodic Update Timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.scheduled_update)
        self.update_timer.start(3600000)  # 1 hour

    def load_stylesheet(self):
        qss_path = os.path.join(os.path.dirname(__file__), "styles", "main.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def create_menu_bar(self):
        """Create menu bar with File, Export, Theme, and Help menus"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("ファイル(&F)")
        
        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Export Menu
        export_menu = menubar.addMenu("エクスポート(&E)")
        
        export_members_action = QAction("メンバーリストをエクスポート...", self)
        export_members_action.triggered.connect(self.export_members)
        export_menu.addAction(export_members_action)
        
        export_videos_action = QAction("動画リストをエクスポート...", self)
        export_videos_action.triggered.connect(self.export_videos)
        export_menu.addAction(export_videos_action)
        
        export_menu.addSeparator()
        
        backup_fav_action = QAction("お気に入りをバックアップ...", self)
        backup_fav_action.triggered.connect(self.backup_favorites)
        export_menu.addAction(backup_fav_action)
        
        restore_fav_action = QAction("お気に入りを復元...", self)
        restore_fav_action.triggered.connect(self.restore_favorites)
        export_menu.addAction(restore_fav_action)
        
        # Theme Menu
        theme_menu = menubar.addMenu("テーマ(&T)")
        
        dark_theme_action = QAction("ダークモード", self)
        dark_theme_action.triggered.connect(lambda: self.change_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        light_theme_action = QAction("ライトモード", self)
        light_theme_action.triggered.connect(lambda: self.change_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        holo_theme_action = QAction("ホロライブテーマ", self)
        holo_theme_action.triggered.connect(lambda: self.change_theme("hololive"))
        theme_menu.addAction(holo_theme_action)
        
        niji_theme_action = QAction("にじさんじテーマ", self)
        niji_theme_action.triggered.connect(lambda: self.change_theme("nijisanji"))
        theme_menu.addAction(niji_theme_action)
        
        # Help Menu
        help_menu = menubar.addMenu("ヘルプ(&H)")
        
        about_action = QAction("バージョン情報(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        log_viewer_action = QAction("ログを表示(&L)", self)
        log_viewer_action.triggered.connect(self.show_log_viewer)
        help_menu.addAction(log_viewer_action)

    def export_members(self):
        """Export members list to CSV"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "メンバーリストをエクスポート",
            f"members_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filepath:
            try:
                from datetime import datetime
                self.export_manager.export_members_csv(filepath)
                QMessageBox.information(self, "成功", "メンバーリストをエクスポートしました")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"エクスポートに失敗しました: {e}")
    
    def export_videos(self):
        """Export videos list to CSV"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "動画リストをエクスポート",
            f"videos_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filepath:
            try:
                from datetime import datetime
                self.export_manager.export_videos_csv(filepath)
                QMessageBox.information(self, "成功", "動画リストをエクスポートしました")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"エクスポートに失敗しました: {e}")
    
    def backup_favorites(self):
        """Backup favorites to JSON"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "お気に入りをバックアップ",
            f"favorites_backup_{datetime.now().strftime('%Y%m%d')}.json",
            "JSON Files (*.json)"
        )
        
        if filepath:
            try:
                from datetime import datetime
                self.export_manager.export_favorites_json(filepath)
                QMessageBox.information(self, "成功", "お気に入りをバックアップしました")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"バックアップに失敗しました: {e}")
    
    def restore_favorites(self):
        """Restore favorites from JSON"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "お気に入りを復元",
            "",
            "JSON Files (*.json)"
        )
        
        if filepath:
            try:
                count = self.export_manager.import_favorites_json(filepath)
                QMessageBox.information(self, "成功", f"{count}件のお気に入りを復元しました")
                # Refresh displays
                self.on_update_finished()
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"復元に失敗しました: {e}")
    
    def change_theme(self, theme: str):
        """Change application theme"""
        self.current_theme = theme
        
        if theme == "dark":
            # Default dark theme (current)
            self.load_stylesheet()
        elif theme == "light":
            # Light theme
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #f5f5f5;
                    color: #333;
                }
                QTabWidget::pane {
                    border: 1px solid #ccc;
                    background: white;
                }
                QPushButton {
                    background-color: #e94560;
                    color: white;
                    border-radius: 6px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #ff6b8a;
                }
            """)
        elif theme == "hololive":
            # Hololive-themed colors
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #0f1419;
                    color: #e8f1ff;
                }
                QTabWidget::pane {
                    border: 2px solid #00a0ff;
                    background: #1a1f2e;
                }
                QPushButton {
                    background-color: #00a0ff;
                    color: white;
                    border-radius: 6px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #3bb4ff;
                }
                QLabel#headerLabel {
                    color: #00a0ff;
                }
            """)
        elif theme == "nijisanji":
            # Nijisanji-themed colors
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #0f0f0f;
                    color: #fff;
                }
                QTabWidget::pane {
                    border: 2px solid #ffcc00;
                    background: #1a1a1a;
                }
                QPushButton {
                    background-color: #ffcc00;
                    color: #000;
                    border-radius: 6px;
                    padding: 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffd633;
                }
                QLabel#headerLabel {
                    color: #ffcc00;
                }
            """)
        
        self.status_label.setText(f"テーマを変更しました: {theme}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "バージョン情報",
            "<h2>ホロライブ・にじさんじ 統合アプリ</h2>"
            "<p>バージョン: 2.0</p>"
            "<p>VTuberのメンバー情報、動画、スケジュールなどを統合管理するアプリケーション</p>"
            "<p><b>機能:</b></p>"
            "<ul>"
            "<li>グループ別タブ表示</li>"
            "<li>統計ダッシュボード</li>"
            "<li>配信スケジュール</li>"
            "<li>エクスポート機能</li>"
            "<li>テーマカスタマイズ</li>"
            "<li>通知機能</li>"
            "</ul>"
        )
    
    def show_log_viewer(self):
        """Show log viewer dialog"""
        dialog = LogViewerDialog(self)
        dialog.exec()

    def setup_integrated_tab(self):
        """Setup the integrated view tab with all sub-tabs showing all groups"""
        layout = QVBoxLayout(self.integrated_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a tab widget for integrated view
        integrated_tabs = QTabWidget()
        layout.addWidget(integrated_tabs)
        
        # Add integrated tabs (no group filter)
        from ui.tabs.favorites import FavoritesTab
        from ui.tabs.sns import SNSTab
        
        self.integrated_members_tab = QWidget()
        self.setup_members_tab()
        integrated_tabs.addTab(self.integrated_members_tab, "👥 メンバー一覧")
        
        self.channels_tab = ChannelsTab(self.data_manager)
        integrated_tabs.addTab(self.channels_tab, "📺 チャンネル")
        
        self.videos_tab = VideosTab(self.data_manager)
        integrated_tabs.addTab(self.videos_tab, "🎬 最新動画")
        
        self.collab_tab = CollabsTab(self.data_manager)
        integrated_tabs.addTab(self.collab_tab, "🤝 コラボ")
        
        self.favorites_tab = FavoritesTab(self.data_manager)
        integrated_tabs.addTab(self.favorites_tab, "⭐ お気に入り")
        
        self.sns_tab = SNSTab(self.data_manager)
        integrated_tabs.addTab(self.sns_tab, "🔗 SNS")

    def setup_members_tab(self):
        """Setup the members tab (used in integrated view)"""
        layout = QVBoxLayout(self.integrated_members_tab)
        
        # Group filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("グループで絞り込み:"))
        self.group_filter = QComboBox()
        self.group_filter.addItems(["すべて", "hololive", "nijisanji"])
        self.group_filter.currentTextChanged.connect(self.load_members)
        filter_layout.addWidget(self.group_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Scroll Area for lists
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        container = QWidget()
        self.members_layout = QVBoxLayout(container)
        self.members_layout.setSpacing(20)
        scroll.setWidget(container)
        
        # Placeholders for group boxes (will be created dynamically)
        self.holo_container = QWidget()
        self.holo_layout = QVBoxLayout(self.holo_container)
        self.members_layout.addWidget(self.holo_container)
        
        self.niji_container = QWidget()
        self.niji_layout = QVBoxLayout(self.niji_container)
        self.members_layout.addWidget(self.niji_container)
        
        self.members_layout.addStretch()

    def load_members(self):
        # Clear existing
        def clear_layout(layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
        clear_layout(self.holo_layout)
        clear_layout(self.niji_layout)
        
        members = self.data_manager.db.get_all_members()
        filter_text = self.group_filter.currentText()
        
        # Separate by group
        holo_members = [m for m in members if m.group_name == "hololive"]
        niji_members = [m for m in members if m.group_name == "nijisanji"]
        
        show_holo = filter_text in ["すべて", "hololive"]
        show_niji = filter_text in ["すべて", "nijisanji"]
        
        from collections import defaultdict
        from PySide6.QtWidgets import QGroupBox, QGridLayout
        from ui.components.async_image import AsyncImageLoader
        
        def create_group_section(members, parent_layout, title_prefix):
            if not members: return
            
            # Group by generation
            by_gen = defaultdict(list)
            for m in members:
                by_gen[m.generation].append(m)
            
            # Sort generations (simple sort for now)
            sorted_gens = sorted(by_gen.keys())
            
            main_group = QGroupBox(title_prefix)
            main_group.setStyleSheet("QGroupBox { border: 2px solid #3a3a5e; border-radius: 8px; font-size: 16px; color: #e94560; margin-top: 20px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
            main_layout = QVBoxLayout(main_group)
            
            for gen in sorted_gens:
                gen_box = QGroupBox(gen)
                gen_box.setStyleSheet("QGroupBox { border: 1px solid #555; border-radius: 4px; font-size: 13px; color: #aaa; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
                gen_layout = QGridLayout(gen_box)
                gen_layout.setSpacing(10)
                
                row, col = 0, 0
                cols = 4
                
                for m in by_gen[gen]:
                    # Member Card (Mini)
                    card = QFrame()
                    card.setFixedSize(180, 60)
                    card.setStyleSheet("background-color: #1a1a2e; border-radius: 6px;")
                    card_layout = QHBoxLayout(card)
                    card_layout.setContentsMargins(5,5,5,5)
                    
                    # Icon
                    img = AsyncImageLoader(m.icon_url, 40, 40)
                    img.setStyleSheet("border-radius: 20px;")
                    card_layout.addWidget(img)
                    
                    # Name
                    name_lbl = QLabel(m.name)
                    name_lbl.setStyleSheet("color: white; font-weight: bold;")
                    card_layout.addWidget(name_lbl)
                    
                    gen_layout.addWidget(card, row, col)
                    col += 1
                    if col >= cols:
                        col = 0
                        row += 1
                
                main_layout.addWidget(gen_box)
            
            parent_layout.addWidget(main_group)

        if show_holo:
            create_group_section(holo_members, self.holo_layout, "🔷 ホロライブ")
            self.holo_container.setVisible(True)
        else:
            self.holo_container.setVisible(False)
            
        if show_niji:
            create_group_section(niji_members, self.niji_layout, "🔶 にじさんじ")
            self.niji_container.setVisible(True)
        else:
            self.niji_container.setVisible(False)

    @Slot(str)
    def on_api_key_changed(self, text):
        self.api_key = text.strip()
        if self.api_key:
            self.api_status_label.setText("(設定済み ✓)")
            self.api_status_label.setStyleSheet("color: #4ade80;")
            self.data_manager.api_key = self.api_key
            self.refresh_data()
        else:
            self.api_status_label.setText("(未設定)")
            self.api_status_label.setStyleSheet("color: #888;")
            self.data_manager.api_key = None

    @Slot()
    def scheduled_update(self):
        self.status_label.setText("定期更新を開始しています...")
        self.refresh_data()

    @Slot()
    def refresh_data(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            return
            
        self.status_label.setText("データ更新中...")
        self.worker = Worker(self.data_manager)
        self.worker.finished.connect(self.on_update_finished)
        self.worker.start()

    @Slot(bool)
    def on_update_finished(self, success: bool):
        if success:
            self.status_label.setText("データ更新完了")
        else:
            self.status_label.setText("データ更新完了 (一部エラーあり。詳細はログを確認)")
        
        # Show notification
        self.notification_manager.notify_data_update(success=success)
        
        # Refresh members tab in integrated view
        self.load_members()
        
        # Refresh group containers
        if hasattr(self, 'hololive_container'):
            self.hololive_container.refresh_all_tabs()
        if hasattr(self, 'nijisanji_container'):
            self.nijisanji_container.refresh_all_tabs()
        
        # Refresh integrated view tabs
        if hasattr(self, 'channels_tab'):
            self.channels_tab.refresh_list()
        if hasattr(self, 'videos_tab'):
            self.videos_tab.refresh_list()
        if hasattr(self, 'collab_tab'):
            self.collab_tab.refresh_list()
        if hasattr(self, 'favorites_tab'):
            self.favorites_tab.refresh_list()
        if hasattr(self, 'sns_tab'):
            self.sns_tab.refresh_list()


