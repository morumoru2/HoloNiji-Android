import sys
import os
import logging

# Ensure src is in path (dev) or bundled path (PyInstaller)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    sys.path.append(sys._MEIPASS)
else:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't catch KeyboardInterrupt, let the default handler handle it
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger(__name__)
    logger.critical("Unhandled exception caught by sys.excepthook", exc_info=(exc_type, exc_value, exc_traceback))

    # Ensure QApplication exists before showing QMessageBox
    app = QApplication.instance()
    if app:
        error_message = (
            "予期せぬエラーが発生しました。\n"
            "アプリケーションは終了する可能性があります。\n"
            "詳細については、ログファイル 'app.log' を確認してください。"
        )
        QMessageBox.critical(None, "アプリケーションエラー", error_message)
    else:
        # If QApplication is not available, print to stderr
        print(f"Error: {exc_value}", file=sys.stderr)

    sys.__excepthook__(exc_type, exc_value, exc_traceback) # Call the default handler

def main():
    # Configure logging to file

    log_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'app.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ],
        force=True
    )
    logger = logging.getLogger(__name__)
    logger.info("Application starting...")
    
    sys.excepthook = handle_exception # Set the custom exception handler

    app = QApplication(sys.argv)
    
    from ui.splash import SplashWindow
    splash = SplashWindow()
    splash.show()
    splash.start_video()
    
    # Process events to show the splash window immediately
    app.processEvents()
    
    try:
        # Initialize main window (heavy part)
        window = MainWindow()
        
        # Load finished! Show main window immediately
        splash.close()
        window.show()
        
        # Optional: Handle skip button in splash just in case users click it
        # splash.finished remains as a signal but we handle primary transition here
        
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
