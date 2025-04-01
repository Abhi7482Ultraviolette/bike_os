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