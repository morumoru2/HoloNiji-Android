from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QUrl, Signal
import ui.resources.resources_rc  # Import embedded resources

class SplashWindow(QWidget):
    """
    Video splash screen shown during application starup.
    """
    finished = Signal()
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Set dark background until video loads
        self.setStyleSheet("background-color: black;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget = QVideoWidget()
        self.layout.addWidget(self.video_widget)
        
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        # Connect signals
        self.media_player.playbackStateChanged.connect(self.on_state_changed)
        self.media_player.errorOccurred.connect(self.on_error)
        
        # Fixed size for splash
        self.setFixedSize(640, 360)
        
        # Center on screen
        self.center()
        
    def center(self):
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, 
                  (screen.height() - size.height()) // 2)

    def start_video(self):
        try:
            # Path to embedded resource
            url = QUrl("qrc:/videos/Loading.mp4")
            self.media_player.setSource(url)
            self.audio_output.setVolume(1.0) # Unmute and set volume
            self.media_player.play()
        except Exception as e:
            print(f"Failed to start splash video: {e}")
            self.finished.emit()
        
    def on_state_changed(self, state):
        if state == QMediaPlayer.StoppedState:
            # Loop the video until closed
            self.media_player.play()
            
    def on_error(self, error, error_string):
        print(f"Splash Video Error: {error_string}")
        # Finish on error to not block startup
        self.finished.emit()
        
    def mousePressEvent(self, event):
        # Allow skipping with click
        self.finished.emit()
