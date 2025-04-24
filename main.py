import os
# VERY FIRST THING when app starts:
from ssl_config import configure_ssl
configure_ssl()  # Sets up SSL before any network calls

# Set the SSL_CERT_FILE environment variable to the path of your cacert.pem file
os.environ['SSL_CERT_FILE'] = os.path.join(os.path.dirname(__file__), 'cacert.pem')

# Configure logging to capture debug messages
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),  # Log messages to a file named 'app.log'
        logging.StreamHandler()  # Also log messages to the console
    ]
)

import sys
from PyQt5.QtWidgets import QApplication
from gui.login_window import LoginWindow


class AppManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.open_barcode_scan_window)

    def run(self):
        """Run the application."""
        self.login_window.show()
        sys.exit(self.app.exec_())

    def open_barcode_scan_window(self):
        """Open the barcode scanning window."""
        from gui.barcode_scan_window import BarcodeScanWindow
        self.barcode_scan_window = BarcodeScanWindow()
        self.barcode_scan_window.show()
        self.login_window.close()

if __name__ == "__main__":
    app_manager = AppManager()
    app_manager.run()