import os
import sys
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QApplication
from PySide6.QtCore import Qt, QTimer

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("アプリケーションログ")
        self.resize(800, 600)

        self.layout = QVBoxLayout(self)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.layout.addWidget(self.log_display)

        refresh_button = QPushButton("更新")
        refresh_button.clicked.connect(self.load_log)
        self.layout.addWidget(refresh_button)

        self.log_file_path = self._get_log_file_path()
        self.load_log()

        # Optional: Auto-refresh every few seconds
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.load_log)
        self.auto_refresh_timer.start(5000) # Refresh every 5 seconds

    def _get_log_file_path(self):
        # This assumes app.log is in the same directory as the executable
        # which is set up in src/main.py
        app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(app_dir, 'app.log')

    def load_log(self):
        if not os.path.exists(self.log_file_path):
            self.log_display.setText("ログファイルが見つかりません。")
            return

        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.log_display.setText(content)
                self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum()) # Scroll to bottom
        except Exception as e:
            self.log_display.setText(f"ログファイルの読み込み中にエラーが発生しました: {e}")

    def closeEvent(self, event):
        self.auto_refresh_timer.stop()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = LogViewerDialog()
    dialog.exec()
    sys.exit(app.exec())
