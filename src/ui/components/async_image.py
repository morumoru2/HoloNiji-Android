from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt, QUrl
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

class AsyncImageLoader(QLabel):
    _manager = None

    @classmethod
    def get_manager(cls):
        if cls._manager is None:
            cls._manager = QNetworkAccessManager()
        return cls._manager

    def __init__(self, url, w=100, h=100, parent=None):
        super().__init__(parent)
        self.setFixedSize(w, h)
        self.setScaledContents(True)
        self.setStyleSheet("background-color: #ccc; border-radius: 5px;")
        
        # Use shared manager
        self.manager = self.get_manager()
        
        if url:
            self.load_image(url)

    def load_image(self, url):
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        reply = self.manager.get(req)
        reply.finished.connect(lambda: self.handle_finished(reply))

    def handle_finished(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                self.setPixmap(pixmap)
                self.setStyleSheet("background-color: transparent;")
        else:
            # Error placeholder
            self.setText("Error")
        reply.deleteLater()
