import sys
import os
import serial
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QMessageBox, QProgressBar, QFileDialog, QListWidget,
    QFrame, QSplitter, QGridLayout, QSpacerItem, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QGraphicsDropShadowEffect,
    QDialog, QTabWidget, QFormLayout
)
from PyQt5.QtGui import QFont, QPixmap, QColor, QPalette, QIcon, QFontDatabase, QLinearGradient, QPainter, QBrush
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QRect, QTimer

# Global variable to store scanned barcode
SCANNED_BARCODE = None

class BarcodeScanThread(QThread):
    """Thread to handle barcode scanning without freezing the UI"""
    scan_complete = pyqtSignal(str)
    scan_error = pyqtSignal(str)
    scan_progress = pyqtSignal(int)  # New signal for scanning progress

    def __init__(self, port="COM3", baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.is_running = True

    def run(self):
        try:
            # Show progress during scanning
            for i in range(101):
                if not self.is_running:
                    return
                self.scan_progress.emit(i)
                time.sleep(0.02)  # Reduced sleep time for faster scanning

            # Retry mechanism
            max_retries = 3
            for retry in range(max_retries):
                # Create serial connection with longer timeout
                scanner = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=10  # Reduced timeout for faster response
                )
                # Read line from scanner
                line = scanner.readline().decode("utf-8").strip()
                scanner.close()
                if line:
                    self.scan_complete.emit(line)
                    return
                else:
                    print(f"Retry {retry + 1}: No barcode detected.")
            # If no barcode is detected after retries
            self.scan_error.emit("No barcode detected. Please try again.")
        except Exception as e:
            self.scan_error.emit(f"Scanner error: {str(e)}")

    def stop(self):
        self.is_running = False


class BarcodeScanWindow(QMainWindow):
    """Main barcode scanning window"""
    scan_successful = pyqtSignal(dict)  # Signal to emit IMEI after successful scan

    def __init__(self, parent=None):
        super().__init__(parent)

        # Ultraviolette brand colors (modern palette)
        self.uv_blue = "#00C3FF"  # Electric blue accent
        self.uv_dark = "#121212"  # Dark background
        self.uv_light = "#FFFFFF"  # White text
        self.uv_gray = "#333333"  # Input fields
        self.uv_light_gray = "#444444"  # Borders
        self.uv_hover = "#33D1FF"  # Hover state
        self.uv_pressed = "#0099CC"  # Pressed state
        self.uv_footer = "#666666"  # Footer text

        self.setWindowTitle("Vehicle Identification - Ultraviolette Dashboard")
        self.setWindowIcon(QIcon("assets/small_icon.PNG"))
        self.resize(1280, 840)
        self.setMinimumSize(900, 650)

        # Load custom fonts if available
        self.load_fonts()

        # Set dark theme globally
        self.apply_dark_theme()

        # Initialize UI
        self.init_ui()

        # Initialize scan thread as None until needed
        self.scan_thread = None

        # Animation properties
        self.scan_animation = None
        self.is_scanning = False

        # Pulse animation for scan button border
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_value = 0
        self.pulse_direction = 1

        # Animation for scan instructions
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_value = 0
        self.animation_direction = 1

        # Vehicle info storage
        self.vehicle_info = {
            'vin': '',
            'imei': '',
            'uuid': ''
        }

    def update_pulse(self):
        """Update the pulse animation for the scan button border"""
        self.pulse_value += 0.05 * self.pulse_direction
        if self.pulse_value >= 1.0:
            self.pulse_value = 1.0
            self.pulse_direction = -1
        elif self.pulse_value <= 0.0:
            self.pulse_value = 0.0
            self.pulse_direction = 1
        # Calculate opacity based on pulse value
        opacity = 0.5 + 0.5 * self.pulse_value
        self.scan_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
                border: 2px solid rgba(0, 195, 255, {opacity});
            }}
            QPushButton:hover {{
                background-color: {self.uv_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.uv_pressed};
            }}
        """)

    def load_fonts(self):
        """Load custom fonts if available"""
        try:
            # Check if Montserrat font is already in system
            fonts = QFontDatabase().families()
            if "Montserrat" not in fonts:
                # If font file exists, load it
                font_paths = [
                    "assets/fonts/Montserrat-Regular.ttf",
                    "assets/fonts/Montserrat-Bold.ttf",
                    "assets/fonts/Montserrat-Medium.ttf"
                ]
                for path in font_paths:
                    if os.path.exists(path):
                        QFontDatabase.addApplicationFont(path)
        except Exception as e:
            print(f"Font loading error: {str(e)}")

    def apply_dark_theme(self):
        """Apply Ultraviolette's dark theme with modern touches"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(self.uv_dark))
        palette.setColor(QPalette.WindowText, QColor(self.uv_light))
        palette.setColor(QPalette.Base, QColor(self.uv_gray))
        palette.setColor(QPalette.AlternateBase, QColor(self.uv_dark))
        palette.setColor(QPalette.ToolTipBase, QColor(self.uv_light))
        palette.setColor(QPalette.ToolTipText, QColor(self.uv_dark))
        palette.setColor(QPalette.Text, QColor(self.uv_light))
        palette.setColor(QPalette.Button, QColor(self.uv_gray))
        palette.setColor(QPalette.ButtonText, QColor(self.uv_light))
        palette.setColor(QPalette.Link, QColor(self.uv_blue))
        palette.setColor(QPalette.Highlight, QColor(self.uv_blue))
        palette.setColor(QPalette.HighlightedText, QColor(self.uv_dark))
        self.setPalette(palette)

    def init_ui(self):
        """Create the barcode scanning UI with modern design elements"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)

        # Header with logo and user info
        header_layout = QHBoxLayout()

        # Add logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/ultraviolette_automotive_logo.jpg")
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(200, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Fallback if logo not found
            logo_label.setText("ULTRAVIOLETTE")
            logo_label.setFont(QFont("Montserrat", 18, QFont.Bold))
            logo_label.setStyleSheet(f"color: {self.uv_blue};")
        header_layout.addWidget(logo_label, alignment=Qt.AlignLeft)

        # Add header buttons
        header_buttons = QHBoxLayout()
        header_buttons.setSpacing(15)

        # Add help button
        self.help_button = QPushButton()
        self.help_button.setIcon(QIcon("assets/help_icon.png"))
        self.help_button.setIconSize(QSize(18, 18))
        self.help_button.setFixedSize(40, 40)
        self.help_button.setCursor(Qt.PointingHandCursor)
        self.help_button.setToolTip("Help")
        self.help_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_gray};
                color: {self.uv_light};
                border: none;
                border-radius: 20px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: {self.uv_blue};
            }}
        """)
        self.help_button.clicked.connect(self.show_help)
        header_buttons.addWidget(self.help_button)

        # Add logout button
        self.logout_button = QPushButton("Log Out")
        self.logout_button.setFont(QFont("Montserrat", 11, QFont.Bold))
        self.logout_button.setFixedWidth(120)
        self.logout_button.setCursor(Qt.PointingHandCursor)
        self.logout_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_blue};
                border-radius: 6px;
                padding: 10px 25px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 195, 255, 0.15);
                border: 2px solid #33D1FF;
            }}
            QPushButton:pressed {{
                border: 2px solid #0099CC;
                padding-top: 12px;
                padding-bottom: 8px;
            }}
        """)
        self.logout_button.clicked.connect(self.logout)
        header_buttons.addWidget(self.logout_button)

        header_layout.addLayout(header_buttons)
        main_layout.addLayout(header_layout)

        # Add separator line with modern style
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet(f"""
            background-color: {self.uv_light_gray};
            min-height: 1px;
            max-height: 1px;
        """)
        main_layout.addWidget(separator)

        # Create tabs for different modes (Scan & Manual Entry)
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {self.uv_light_gray};
                border-radius: 8px;
                top: -1px;
            }}
        """)
        main_layout.addWidget(self.tab_widget)

        # Create scan tab
        scan_tab = QWidget()
        self.tab_widget.addTab(scan_tab, "Scan Barcode")
        self.setup_scan_tab(scan_tab)

        # Create manual entry tab
        manual_tab = QWidget()
        self.tab_widget.addTab(manual_tab, "Manual Entry")
        self.setup_manual_tab(manual_tab)

        # Vehicle information display area (initially hidden)
        self.vehicle_info_container = QFrame()
        self.vehicle_info_container.setObjectName("glowFrame")
        self.vehicle_info_container.setStyleSheet(f"""
            QFrame#glowFrame {{
                border-radius: 12px;
                border: 1px solid {self.uv_light_gray};
                background-color: {self.uv_dark};
                margin-top: 20px;
            }}
        """)
        self.vehicle_info_container.hide()
        vehicle_info_layout = QVBoxLayout(self.vehicle_info_container)
        vehicle_info_layout.setContentsMargins(25, 25, 25, 25)
        vehicle_info_layout.setSpacing(20)

        # Vehicle info header
        vehicle_info_header = QLabel("Vehicle Information")
        vehicle_info_header.setFont(QFont("Montserrat", 18, QFont.Bold))
        vehicle_info_header.setAlignment(Qt.AlignCenter)
        vehicle_info_layout.addWidget(vehicle_info_header)

        # Container for info cards
        self.info_cards_layout = QVBoxLayout()
        self.info_cards_layout.setSpacing(15)
        vehicle_info_layout.addLayout(self.info_cards_layout)

        # Action buttons
        vehicle_actions_layout = QHBoxLayout()
        vehicle_actions_layout.setSpacing(15)

        self.save_button = QPushButton("Save Information")
        self.save_button.setIcon(QIcon("assets/save_icon.png"))
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #33D1FF;
            }}
            QPushButton:pressed {{
                background-color: #0099CC;
                padding-top: 14px;
                padding-bottom: 8px;
            }}
        """)
        self.save_button.clicked.connect(self.save_vehicle_info)
        vehicle_actions_layout.addWidget(self.save_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setIcon(QIcon("assets/clear_icon.png"))
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_blue};
                border-radius: 6px;
                padding: 10px 25px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 195, 255, 0.15);
                border: 2px solid #33D1FF;
            }}
            QPushButton:pressed {{
                border: 2px solid #0099CC;
                padding-top: 12px;
                padding-bottom: 8px;
            }}
        """)
        self.clear_button.clicked.connect(self.clear_vehicle_info)
        vehicle_actions_layout.addWidget(self.clear_button)

        vehicle_info_layout.addLayout(vehicle_actions_layout)
        main_layout.addWidget(self.vehicle_info_container)

        # Add a footer with version info
        footer_layout = QHBoxLayout()
        version_label = QLabel("Ultraviolette Dashboard v1.2.0")
        version_label.setFont(QFont("Montserrat", 9))
        version_label.setStyleSheet(f"color: {self.uv_footer};")
        footer_layout.addWidget(version_label, alignment=Qt.AlignLeft)

        copyright_label = QLabel("© 2025 Ultraviolette Automotive")
        copyright_label.setFont(QFont("Montserrat", 9))
        copyright_label.setStyleSheet(f"color: {self.uv_footer};")
        footer_layout.addWidget(copyright_label, alignment=Qt.AlignRight)

        main_layout.addLayout(footer_layout)

    def setup_scan_tab(self, tab):
        """Set up the barcode scanning tab"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # Title with badge
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)

        # Create a small badge before the title
        title_badge = QLabel()
        title_badge.setFixedSize(8, 50)
        title_badge.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                      stop:0 {self.uv_blue}, stop:1 {self.uv_hover});
            border-radius: 4px;
        """)
        title_layout.addWidget(title_badge)
        title_layout.addSpacing(15)

        title_container = QVBoxLayout()
        title_container.setSpacing(8)

        title = QLabel("Vehicle Identification")
        title.setFont(QFont("Montserrat", 24, QFont.Bold))
        title.setStyleSheet(f"color: {self.uv_light};")
        title_container.addWidget(title)

        subtitle = QLabel("Scan the vehicle barcode to begin")
        subtitle.setFont(QFont("Montserrat", 14))
        subtitle.setStyleSheet("color: #AAAAAA;")
        title_container.addWidget(subtitle)

        title_layout.addLayout(title_container)
        title_layout.addWidget(QLabel(), 1)  # Spacer to keep title centered

        layout.addLayout(title_layout)

        # Scan card with modern design
        scan_card = QFrame()
        scan_card.setObjectName("glowFrame")

        # Add shadow effect to the card
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(30)
        card_shadow.setColor(QColor(0, 0, 0, 80))
        card_shadow.setOffset(0, 5)
        scan_card.setGraphicsEffect(card_shadow)

        scan_layout = QVBoxLayout(scan_card)
        scan_layout.setContentsMargins(40, 40, 40, 40)
        scan_layout.setSpacing(30)
        scan_layout.setAlignment(Qt.AlignCenter)

        # Scan image with circular container
        self.scan_image_container = QFrame()
        self.scan_image_container.setFixedSize(220, 220)
        self.scan_image_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 110px;
                border: 2px solid {self.uv_blue};
            }}
        """)
        scan_image_layout = QVBoxLayout(self.scan_image_container)
        scan_image_layout.setContentsMargins(20, 20, 20, 20)
        self.scan_image = QLabel()
        scan_pixmap = QPixmap("assets/barcode_scan.png")
        if scan_pixmap.isNull():
            # If image doesn't exist, display text instead
            self.scan_image.setText("[ Scan ]")
            self.scan_image.setStyleSheet(f"""
                color: {self.uv_blue}; 
                font-size: 16px; 
                padding: 40px;
                border: none;
            """)
            self.scan_image.setAlignment(Qt.AlignCenter)
        else:
            # Set the pixmap and make the label transparent
            self.scan_image.setPixmap(scan_pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.scan_image.setStyleSheet("background: transparent; border: none;")
            self.scan_image.setAlignment(Qt.AlignCenter)
        scan_image_layout.addWidget(self.scan_image)
        scan_layout.addWidget(self.scan_image_container, alignment=Qt.AlignCenter)

        # Scan instructions with animation
        self.scan_instructions = QLabel("Position the barcode scanner over the vehicle's barcode")
        self.scan_instructions.setFont(QFont("Montserrat", 14))
        self.scan_instructions.setStyleSheet(f"color: {self.uv_light}; margin-top: 10px;")
        self.scan_instructions.setAlignment(Qt.AlignCenter)
        scan_layout.addWidget(self.scan_instructions)

        # Progress bar for scanning
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(0)
        self.scan_progress.setTextVisible(False)
        self.scan_progress.setFixedHeight(6)
        self.scan_progress.setFixedWidth(300)
        scan_layout.addWidget(self.scan_progress, alignment=Qt.AlignCenter)
        self.scan_progress.hide()  # Initially hidden

        # Status message
        self.status_message = QLabel("")
        self.status_message.setFont(QFont("Montserrat", 12))
        self.status_message.setAlignment(Qt.AlignCenter)
        self.status_message.setStyleSheet(f"color: {self.uv_blue};")
        scan_layout.addWidget(self.status_message)

        # Scan button
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(20)

        self.scan_button = QPushButton("Start Scanning")
        self.scan_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.scan_button.setFixedSize(220, 50)
        self.scan_button.setCursor(Qt.PointingHandCursor)
        self.scan_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: {self.uv_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.uv_pressed};
            }}
        """)
        # Add scan icon
        scan_icon = QIcon("assets/scan_icon.png")
        if not scan_icon.isNull():
            self.scan_button.setIcon(scan_icon)
            self.scan_button.setIconSize(QSize(20, 20))
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.cancel_button.setFixedWidth(150)
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_blue};
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 195, 255, 0.15);
                border: 2px solid #33D1FF;
            }}
            QPushButton:pressed {{
                border: 2px solid #0099CC;
                padding-top: 14px;
                padding-bottom: 10px;
            }}
        """)
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.hide()  # Initially hidden
        button_layout.addWidget(self.cancel_button)

        scan_layout.addLayout(button_layout)
        layout.addWidget(scan_card)

    def setup_manual_tab(self, tab):
        """Set up the manual entry tab"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # Title
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)

        # Create a small badge before the title
        title_badge = QLabel()
        title_badge.setFixedSize(8, 50)
        title_badge.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                      stop:0 {self.uv_blue}, stop:1 {self.uv_hover});
            border-radius: 4px;
        """)
        title_layout.addWidget(title_badge)
        title_layout.addSpacing(15)

        title_container = QVBoxLayout()
        title_container.setSpacing(8)

        title = QLabel("Manual Entry")
        title.setFont(QFont("Montserrat", 24, QFont.Bold))
        title.setStyleSheet(f"color: {self.uv_light};")
        title_container.addWidget(title)

        subtitle = QLabel("Enter vehicle information manually")
        subtitle.setFont(QFont("Montserrat", 14))
        subtitle.setStyleSheet("color: #AAAAAA;")
        title_container.addWidget(subtitle)

        title_layout.addLayout(title_container)
        title_layout.addWidget(QLabel(), 1)  # Spacer to keep title centered

        layout.addLayout(title_layout)

        # Manual entry card
        manual_card = QFrame()
        manual_card.setObjectName("glowFrame")

        # Add shadow effect to the card
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(30)
        card_shadow.setColor(QColor(0, 0, 0, 80))
        card_shadow.setOffset(0, 5)
        manual_card.setGraphicsEffect(card_shadow)

        manual_layout = QVBoxLayout(manual_card)
        manual_layout.setContentsMargins(40, 40, 40, 40)
        manual_layout.setSpacing(25)

        # Form layout for input fields
        form_layout = QFormLayout()
        form_layout.setSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # VIN input
        vin_label = QLabel("VIN:")
        vin_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Enter Vehicle Identification Number")
        self.vin_input.setMaxLength(17)  # Standard VIN length
        self.vin_input.setFont(QFont("Montserrat", 11))
        self.vin_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 10px 12px;
                color: {self.uv_light};
                selection-background-color: {self.uv_blue};
            }}
            QLineEdit:focus {{
                border: 1px solid {self.uv_blue};
            }}
        """)
        form_layout.addRow(vin_label, self.vin_input)

        # IMEI input
        imei_label = QLabel("IMEI:")
        imei_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText("Enter IMEI Number")
        self.imei_input.setMaxLength(15)  # Standard IMEI length
        self.imei_input.setFont(QFont("Montserrat", 11))
        self.imei_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 10px 12px;
                color: {self.uv_light};
                selection-background-color: {self.uv_blue};
            }}
            QLineEdit:focus {{
                border: 1px solid {self.uv_blue};
            }}
        """)
        form_layout.addRow(imei_label, self.imei_input)

        # UUID input
        uuid_label = QLabel("UUID:")
        uuid_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.uuid_input = QLineEdit()
        self.uuid_input.setPlaceholderText("Enter UUID")
        self.uuid_input.setMaxLength(36)  # Standard UUID length with hyphens
        self.uuid_input.setFont(QFont("Montserrat", 11))
        self.uuid_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 10px 12px;
                color: {self.uv_light};
                selection-background-color: {self.uv_blue};
            }}
            QLineEdit:focus {{
                border: 1px solid {self.uv_blue};
            }}
        """)
        form_layout.addRow(uuid_label, self.uuid_input)

        manual_layout.addLayout(form_layout)

        # Info about manual entry
        info_label = QLabel("Enter the vehicle information fields above. All fields are optional but at least one is required.")
        info_label.setFont(QFont("Montserrat", 10))
        info_label.setStyleSheet("color: #AAAAAA;")
        info_label.setWordWrap(True)
        manual_layout.addWidget(info_label)

        # Submit button
        self.submit_button = QPushButton("Submit Information")
        self.submit_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.submit_button.setFixedWidth(200)
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: {self.uv_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.uv_pressed};
            }}
        """)
        self.submit_button.setIcon(QIcon("assets/submit_icon.png"))
        self.submit_button.clicked.connect(self.submit_manual_info)
        manual_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)

        layout.addWidget(manual_card)

    def update_animation(self):
        """Update the pulsating animation for the scan instructions label"""
        self.animation_value += 0.05 * self.animation_direction
        if self.animation_value >= 1.0:
            self.animation_value = 1.0
            self.animation_direction = -1
        elif self.animation_value <= 0.0:
            self.animation_value = 0.0
            self.animation_direction = 1
        # Calculate opacity based on animation value
        opacity = 0.5 + 0.5 * self.animation_value
        self.scan_instructions.setStyleSheet(f"color: rgba(255, 255, 255, {opacity});")

    def start_scan(self):
        """Start the barcode scanning process"""
        # Update UI for scanning state
        self.is_scanning = True
        self.scan_button.hide()
        self.cancel_button.show()
        self.scan_progress.show()
        self.scan_progress.setValue(0)
        self.status_message.setText("Scanning in progress...")
        self.status_message.setStyleSheet(f"color: {self.uv_blue};")
        # Start the pulsating animation
        self.animation_timer.start(50)  # Update every 50ms
        # Start pulse animation for scan button border
        self.pulse_timer.start(50)  # Update every 50ms
        # Initialize and start the scan thread
        self.scan_thread = BarcodeScanThread()
        self.scan_thread.scan_complete.connect(self.handle_scan_complete)
        self.scan_thread.scan_error.connect(self.handle_scan_error)
        self.scan_thread.scan_progress.connect(self.update_scan_progress)
        self.scan_thread.start()

    def cancel_scan(self):
        """Cancel the current scanning process"""
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.stop()
            self.scan_thread.terminate()
            self.scan_thread = None
        self.reset_scan_ui()
        self.status_message.setText("Scan cancelled")
        self.status_message.setStyleSheet("color: #FF6B6B;")  # Red color for cancelled
        # Reset after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_message.setText(""))

    def reset_scan_ui(self):
        """Reset UI elements after scanning"""
        self.is_scanning = False
        self.scan_button.show()
        self.cancel_button.hide()
        self.scan_progress.hide()
        self.pulse_timer.stop()  # Stop the pulse animation
        # Stop the pulsating animation
        self.animation_timer.stop()
        self.scan_instructions.setStyleSheet("color: #FFFFFF;")  # Reset to default color
        # Reset the vehicle info container
        for i in reversed(range(self.info_cards_layout.count())): 
            widget = self.info_cards_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.vehicle_info_container.hide()
        # Clear stored info
        self.vehicle_info = {
            'vin': '',
            'imei': '',
            'uuid': ''
        }
        # Reset status message
        self.status_message.setText("")

    def update_scan_progress(self, value):      
        """Update the progress bar during scanning"""
        self.scan_progress.setValue(value)

    def handle_scan_complete(self, barcode):
        """Handle successful barcode scan"""
        global SCANNED_BARCODE
        # Reset UI
        self.reset_scan_ui()
        # Hide the scan image, button, and instructions
        self.scan_image_container.hide()
        self.scan_button.hide()
        self.scan_instructions.hide()
        self.scan_progress.hide()
        # Show success message
        self.status_message.setText("Barcode scanned successfully!")
        self.status_message.setStyleSheet(f"color: {self.uv_blue};")
        # Store the scanned barcode
        SCANNED_BARCODE = barcode
        # Parse the barcode data (assuming format: VIN|IMEI|UUID)
        try:
            parts = barcode.split('|')
            if len(parts) >= 3:
                self.vehicle_info['vin'] = parts[0]
                self.vehicle_info['imei'] = parts[1]
                self.vehicle_info['uuid'] = parts[2]
            else:
                # If format is unexpected, just store as UUID
                self.vehicle_info['uuid'] = barcode
        except Exception as e:
            print(f"Error parsing barcode: {str(e)}")
            self.vehicle_info['uuid'] = barcode
        # Display the vehicle information in a clean and organized way
        self.display_vehicle_info()
        # Emit the scanned data as a dictionary
        self.scan_successful.emit(self.vehicle_info)

def display_vehicle_info(self):
    """Display the vehicle information in a clean and organized grid layout"""
    # Clear previous info cards if any
    for i in reversed(range(self.info_cards_layout.count())): 
        widget = self.info_cards_layout.itemAt(i).widget()
        if widget:
            widget.setParent(None)
    # Create a grid layout for the vehicle info
    grid_layout = QGridLayout()
    grid_layout.setSpacing(20)
    grid_layout.setContentsMargins(20, 20, 20, 20)
    # Add vehicle info to the grid layout
    row = 0
    if self.vehicle_info['vin']:
        vin_label = QLabel("VIN:")
        vin_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        vin_label.setStyleSheet(f"color: {self.uv_blue};")
        vin_value = QLabel(self.vehicle_info['vin'])
        vin_value.setFont(QFont("Montserrat", 12))
        vin_value.setStyleSheet(f"color: {self.uv_light};")
        vin_value.setTextInteractionFlags(Qt.TextSelectableByMouse)  # Make text selectable
        grid_layout.addWidget(vin_label, row, 0)
        grid_layout.addWidget(vin_value, row, 1)
        row += 1
    if self.vehicle_info['imei']:
        imei_label = QLabel("IMEI:")
        imei_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        imei_label.setStyleSheet(f"color: {self.uv_blue};")
        imei_value = QLabel(self.vehicle_info['imei'])
        imei_value.setFont(QFont("Montserrat", 12))
        imei_value.setStyleSheet(f"color: {self.uv_light};")
        imei_value.setTextInteractionFlags(Qt.TextSelectableByMouse)  # Make text selectable
        grid_layout.addWidget(imei_label, row, 0)
        grid_layout.addWidget(imei_value, row, 1)
        row += 1
    if self.vehicle_info['uuid']:
        uuid_label = QLabel("UUID:")
        uuid_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        uuid_label.setStyleSheet(f"color: {self.uv_blue};")
        uuid_value = QLabel(self.vehicle_info['uuid'])
        uuid_value.setFont(QFont("Montserrat", 12))
        uuid_value.setStyleSheet(f"color: {self.uv_light};")
        uuid_value.setTextInteractionFlags(Qt.TextSelectableByMouse)  # Make text selectable
        grid_layout.addWidget(uuid_label, row, 0)
        grid_layout.addWidget(uuid_value, row, 1)
        row += 1
    # Add "Continue with Analysis" and "Rescan" buttons
    button_layout = QHBoxLayout()
    button_layout.setSpacing(20)
    continue_button = QPushButton("Continue with Analysis")
    continue_button.setFont(QFont("Montserrat", 12, QFont.Bold))
    continue_button.setCursor(Qt.PointingHandCursor)
    continue_button.setStyleSheet(f"""
        QPushButton {{
            background-color: {self.uv_blue};
            color: {self.uv_dark};
            border: none;
            border-radius: 25px;
            padding: 12px 30px;
        }}
        QPushButton:hover {{
            background-color: {self.uv_hover};
        }}
        QPushButton:pressed {{
            background-color: {self.uv_pressed};
        }}
    """)
    continue_button.setIcon(QIcon("assets/analysis_icon.png"))
    continue_button.clicked.connect(self.continue_with_analysis)
    rescan_button = QPushButton("Rescan")
    rescan_button.setFont(QFont("Montserrat", 12, QFont.Bold))
    rescan_button.setCursor(Qt.PointingHandCursor)
    rescan_button.setStyleSheet(f"""
        QPushButton {{
            background-color: transparent;
            color: {self.uv_light};
            border: 2px solid {self.uv_blue};
            border-radius: 25px;
            padding: 12px 30px;
        }}
        QPushButton:hover {{
            background-color: rgba(0, 195, 255, 0.15);
            border: 2px solid #33D1FF;
        }}
        QPushButton:pressed {{
            border: 2px solid #0099CC;
            padding-top: 14px;
            padding-bottom: 10px;
        }}
    """)
    rescan_button.setIcon(QIcon("assets/rescan_icon.png"))
    rescan_button.clicked.connect(self.reset_scan_ui)
    button_layout.addWidget(continue_button)
    button_layout.addWidget(rescan_button)
    grid_layout.addLayout(button_layout, row, 0, 1, 2, alignment=Qt.AlignCenter)

    # Add the grid layout to the info cards layout
    self.info_cards_layout.addLayout(grid_layout)
    # Show the container
    self.vehicle_info_container.show()

def continue_with_analysis(self):
    """Handle the 'Continue with Analysis' button click"""
    try:
        from gui.main_window import MainWindow
        print("Import successful:", MainWindow)
    except ImportError as e:
        print("Import failed:", e)
        return

    # Validate scanned data
    if not any(self.vehicle_info.values()):
        QMessageBox.warning(self, "Incomplete Data", "No vehicle information available for analysis.")
        return

        # Create MainWindow instance and pass the scanned data
        self.main_window = MainWindow(scanned_data=self.vehicle_info)
        self.main_window.show()
        self.close()

    def handle_scan_error(self, error_message):
        """Handle scanning errors"""
        self.reset_scan_ui()
        self.status_message.setText(error_message)
        self.status_message.setStyleSheet("color: #FF6B6B;")  # Red color for error

    def submit_manual_info(self):
        """Process manually entered vehicle information"""
        # Get values from input fields
        vin = self.vin_input.text().strip()
        imei = self.imei_input.text().strip()
        uuid = self.uuid_input.text().strip()

        # Validate - at least one field should have a value
        if not (vin or imei or uuid):
            self.status_message.setText("Please enter at least one field")
            self.status_message.setStyleSheet("color: #FF6B6B;")  # Red color for error
            return

        # Store the values
        self.vehicle_info['vin'] = vin
        self.vehicle_info['imei'] = imei
        self.vehicle_info['uuid'] = uuid

        # Display success message
        self.status_message.setText("Information submitted successfully!")
        self.status_message.setStyleSheet(f"color: {self.uv_blue};")

        # Clear input fields
        self.vin_input.clear()
        self.imei_input.clear()
        self.uuid_input.clear()

        # Display the vehicle information
        self.display_vehicle_info()

        # Reset after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_message.setText(""))

    def save_vehicle_info(self):
        """Save the vehicle information to a file"""
        if not any(self.vehicle_info.values()):
            self.status_message.setText("No vehicle information to save")
            self.status_message.setStyleSheet("color: #FF6B6B;")  # Red color for error
            return

        try:
            # Ask for file location
            file_name = f"Vehicle_Info_{self.vehicle_info['vin'] or 'Unknown'}.txt"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Vehicle Information",
                file_name,
                "Text Files (*.txt);;All Files (*)"
            )
            if not file_path:
                return

            # Write to file
            with open(file_path, 'w') as file:
                file.write("ULTRAVIOLETTE AUTOMOTIVE - VEHICLE INFORMATION\n")
                file.write("=" * 50 + "\n")
                if self.vehicle_info['vin']:
                    file.write(f"VIN: {self.vehicle_info['vin']}\n")
                if self.vehicle_info['imei']:
                    file.write(f"IMEI: {self.vehicle_info['imei']}\n")
                if self.vehicle_info['uuid']:
                    file.write(f"UUID: {self.vehicle_info['uuid']}\n")
                file.write("\n" + "=" * 50 + "\n")
                file.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")

            self.status_message.setText("Information saved successfully!")
            self.status_message.setStyleSheet(f"color: {self.uv_blue};")
            # Reset after 2 seconds
            QTimer.singleShot(2000, lambda: self.status_message.setText(""))
        except Exception as e:
            self.status_message.setText(f"Error saving file: {str(e)}")
            self.status_message.setStyleSheet("color: #FF6B6B;")  # Red color for error

    def clear_vehicle_info(self):
        """Clear the displayed vehicle information"""
        # Clear stored info
        self.vehicle_info = {
            'vin': '',
            'imei': '',
            'uuid': ''
        }

        # Hide the info container
        self.vehicle_info_container.hide()

        # Show confirmation message
        self.status_message.setText("Vehicle information cleared")
        self.status_message.setStyleSheet("color: #AAAAAA;")

        # Reset after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_message.setText(""))

    def show_help(self):
        """Show help information"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setMinimumSize(500, 400)
        help_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {self.uv_dark};
                color: {self.uv_light};
                border-radius: 10px;
            }}
        """)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        help_dialog.setGraphicsEffect(shadow)

        help_layout = QVBoxLayout(help_dialog)
        help_layout.setContentsMargins(30, 30, 30, 30)
        help_layout.setSpacing(20)

        # Title
        title = QLabel("Barcode Scanner Help")
        title.setFont(QFont("Montserrat", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {self.uv_light}; margin-bottom: 10px;")
        help_layout.addWidget(title)

        # Help content card
        help_card = QFrame()
        help_card.setObjectName("glowFrame")
        help_card_layout = QVBoxLayout(help_card)
        help_card_layout.setContentsMargins(20, 20, 20, 20)
        help_card_layout.setSpacing(15)

        help_topics = [
            ("Barcode Scanning", "Position the scanner over the vehicle's barcode and click 'Start Scanning'. Hold steady until the scan completes."),
            ("Manual Entry", "If scanning fails, you can manually enter the VIN, IMEI, or UUID in the 'Manual Entry' tab."),
            ("Vehicle Information", "The scanned or entered information will display in cards below. You can copy individual values or save all information to a file."),
            ("Troubleshooting", "If scanning fails, ensure there's proper lighting and the barcode is clean and undamaged."),
            ("Support Contact", "For technical assistance, contact support at support@ultraviolette.com or call +91-1234567890.")
        ]

        for title, content in help_topics:
            topic_title = QLabel(title)
            topic_title.setFont(QFont("Montserrat", 14, QFont.Bold))
            topic_title.setStyleSheet(f"color: {self.uv_blue};")
            help_card_layout.addWidget(topic_title)

            topic_content = QLabel(content)
            topic_content.setFont(QFont("Montserrat", 12))
            topic_content.setWordWrap(True)
            topic_content.setStyleSheet(f"color: {self.uv_light};")
            help_card_layout.addWidget(topic_content)

            # Add spacer except for the last item
            if title != help_topics[-1][0]:
                spacer = QFrame()
                spacer.setFrameShape(QFrame.HLine)
                spacer.setFrameShadow(QFrame.Plain)
                spacer.setStyleSheet(f"background-color: {self.uv_light_gray}; min-height: 1px; max-height: 1px;")
                help_card_layout.addWidget(spacer)

        help_layout.addWidget(help_card)

        # Close button
        close_button = QPushButton("Close")
        close_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: {self.uv_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.uv_pressed};
            }}
        """)
        close_button.clicked.connect(help_dialog.accept)
        help_layout.addWidget(close_button, alignment=Qt.AlignCenter)

        help_dialog.exec_()

    def logout(self):
        """Handle logout action"""
        confirm = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to log out?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            from gui.login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set application-wide attributes
    app.setStyle("Fusion")
    window = BarcodeScanWindow()
    window.show()
    sys.exit(app.exec_())