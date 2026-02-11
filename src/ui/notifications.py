"""
Simple notification system for the application.
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal, QTimer
import sys


class NotificationManager(QObject):
    """
    Manage system notifications for the application.
    Supports system tray icon and Windows native notifications.
    """
    
    # Signal emitted when user clicks on notification
    notification_clicked = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = None
        self.setup_tray_icon()
    
    def setup_tray_icon(self):
        """Setup system tray icon"""
        # Check if system tray is available
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self.parent())
        
        # Try to load icon, fallback to default
        # For now, using a simple default icon
        try:
            from PySide6.QtGui import QPixmap
            # Try to use a standard pixmap
            app_icon = QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_FileDialogStart)
            self.tray_icon.setIcon(app_icon)
        except Exception:
            # If that fails, just don't set an icon (will use default)
            pass

        
        # Create context menu
        tray_menu = QMenu()
        
        show_action = QAction("アプリを表示", self)
        show_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("終了", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("ホロライブ・にじさんじ 統合アプリ")
        
        # Connect signals
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # Show tray icon
        self.tray_icon.show()
    
    def show_main_window(self):
        """Show the main application window"""
        if self.parent():
            self.parent().show()
            self.parent().raise_()
            self.parent().activateWindow()
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_main_window()
    
    def show_notification(self, title: str, message: str, duration: int = 5000):
        """
        Show a system notification.
        
        Args:
            title: Notification title
            message: Notification message
            duration: Display duration in milliseconds
        """
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.Information,
                duration
            )
    
    def notify_new_video(self, member_name: str, video_title: str):
        """
        Notify user about new video from favorite member.
        
        Args:
            member_name: Name of the member
            video_title: Title of the video
        """
        self.show_notification(
            f"🎬 新着動画 - {member_name}",
            video_title,
            duration=8000
        )
    
    def notify_collab(self, members: str, video_title: str):
        """
        Notify user about new collaboration video.
        
        Args:
            members: Members involved in the collab
            video_title: Title of the video
        """
        self.show_notification(
            f"🤝 コラボ動画 - {members}",
            video_title,
            duration=8000
        )
    
    def notify_data_update(self, success: bool = True):
        """
        Notify user about data update status.
        
        Args:
            success: Whether the update was successful
        """
        if success:
            self.show_notification(
                "✅ データ更新完了",
                "メンバーと動画情報を更新しました",
                duration=3000
            )
        else:
            self.show_notification(
                "❌ データ更新失敗",
                "データの更新中にエラーが発生しました",
                duration=5000
            )
    
    def hide_tray_icon(self):
        """Hide the system tray icon"""
        if self.tray_icon:
            self.tray_icon.hide()
    
    def show_tray_icon(self):
        """Show the system tray icon"""
        if self.tray_icon:
            self.tray_icon.show()
