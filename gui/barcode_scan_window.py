import sys
import os
import serial
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QMessageBox, QProgressBar, QFileDialog, QListWidget,
    QFrame, QSplitter, QGridLayout, QSpacerItem, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QGraphicsDropShadowEffect,
    QDialog, QTabWidget, QFormLayout, QStackedWidget, QScrollArea
)
from PyQt5.QtGui import (
    QFont, QPixmap, QColor, QPalette, QIcon, QFontDatabase, 
    QLinearGradient, QPainter, QBrush, QMovie, QCursor
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, 
    QEasingCurve, QRect, QTimer, QPoint
)

# Global variable to store scanned barcode
SCANNED_BARCODE = None

class BarcodeScanThread(QThread):
    """Thread to handle barcode scanning without freezing the UI"""
    scan_complete = pyqtSignal(str)
    scan_error = pyqtSignal(str)
    scan_progress = pyqtSignal(int)
    scan_status = pyqtSignal(str)

    def __init__(self, port="COM3", baudrate=115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.is_running = True

    def run(self):
        try:
            # Initialization phase
            self.scan_status.emit("Initializing scanner...")
            # Show progress during scanning
            for i in range(101):
                if not self.is_running:
                    return
                self.scan_progress.emit(i)
                time.sleep(0.02)
            self.scan_status.emit("Ready to scan...")
            time.sleep(0.5)
            self.scan_status.emit("Scanning...")
            # Retry mechanism
            max_retries = 3
            for retry in range(max_retries):
                if not self.is_running:
                    return
                self.scan_status.emit(f"Attempt {retry + 1} of {max_retries}...")
                scanner = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=5
                )
                line = scanner.readline().decode("utf-8").strip()
                scanner.close()
                if line:
                    self.scan_complete.emit(line)
                    return
                else:
                    self.scan_status.emit(f"Retry {retry + 1}: No barcode detected")
            self.scan_error.emit("No barcode detected. Please try again.")
        except Exception as e:
            self.scan_error.emit(f"Scanner error: {str(e)}")

    def stop(self):
        self.is_running = False
        self.scan_status.emit("Scan cancelled")


class BarcodeScanWindow(QMainWindow):
    """Main barcode scanning window with modern UI enhancements"""
    scan_successful = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Enhanced Ultraviolette color palette
        self.uv_primary = "#00C3FF"  # Primary blue
        self.uv_secondary = "#00E676"  # Green for success
        self.uv_dark = "#121212"  # Dark background
        self.uv_darker = "#0A0A0A"  # Even darker
        self.uv_light = "#FFFFFF"  # White text
        self.uv_gray = "#2D2D2D"  # Input fields
        self.uv_light_gray = "#444444"  # Borders
        self.uv_hover = "#33D1FF"  # Hover state
        self.uv_pressed = "#0099CC"  # Pressed state
        self.uv_error = "#FF5252"  # Error color
        self.uv_warning = "#FFAB40"  # Warning color
        self.uv_footer = "#666666"  # Footer text

        # Window setup
        self.setWindowTitle("Ultraviolette - Vehicle Identification")
        self.setWindowIcon(QIcon("assets/small_icon.PNG"))
        self.resize(1280, 840)
        self.setMinimumSize(1000, 700)

        # Load custom fonts
        self.load_fonts()

        # Set dark theme globally
        self.apply_dark_theme()

        # Initialize UI
        self.init_ui()

        # Initialize scan thread
        self.scan_thread = None

        # Animation properties
        self.scan_animation = None
        self.is_scanning = False

        # Pulse animation for scan button
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_value = 0
        self.pulse_direction = 1

        # Vehicle info storage
        self.vehicle_info = {
            'vin': '',
            'imei': '',
            'uuid': ''
        }

        # Scan state
        self.current_scan_state = "ready"  # ready, scanning, success, error

        # Setup animations
        self.setup_animations()

    def setup_animations(self):
        """Setup various UI animations"""
        # Scan button pulse animation
        self.pulse_animation = QPropertyAnimation(self.scan_button, b"geometry")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setLoopCount(-1)  # Infinite loop
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutSine)

        # Status message fade animation
        self.status_fade_animation = QPropertyAnimation(self.status_message, b"windowOpacity")
        self.status_fade_animation.setDuration(500)
        self.status_fade_animation.setStartValue(1.0)
        self.status_fade_animation.setEndValue(0.0)

        # Scan image animation
        self.scan_image_animation = QPropertyAnimation(self.scan_image_container, b"geometry")
        self.scan_image_animation.setDuration(300)
        self.scan_image_animation.setEasingCurve(QEasingCurve.OutBack)

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
        """Apply enhanced dark theme with modern touches"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(self.uv_dark))
        palette.setColor(QPalette.WindowText, QColor(self.uv_light))
        palette.setColor(QPalette.Base, QColor(self.uv_gray))
        palette.setColor(QPalette.AlternateBase, QColor(self.uv_darker))
        palette.setColor(QPalette.ToolTipBase, QColor(self.uv_light))
        palette.setColor(QPalette.ToolTipText, QColor(self.uv_dark))
        palette.setColor(QPalette.Text, QColor(self.uv_light))
        palette.setColor(QPalette.Button, QColor(self.uv_gray))
        palette.setColor(QPalette.ButtonText, QColor(self.uv_light))
        palette.setColor(QPalette.BrightText, QColor(self.uv_primary))
        palette.setColor(QPalette.Link, QColor(self.uv_primary))
        palette.setColor(QPalette.Highlight, QColor(self.uv_primary))
        palette.setColor(QPalette.HighlightedText, QColor(self.uv_dark))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#555555"))
        self.setPalette(palette)

    def init_ui(self):
        """Create the enhanced barcode scanning UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with subtle gradient background
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create a container with gradient background
        bg_container = QWidget()
        bg_container.setObjectName("bgContainer")
        bg_container.setStyleSheet("""
            QWidget#bgContainer {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #121212, stop:0.5 #0D0D0D, stop:1 #121212
                );
                border-radius: 0px;
            }
        """)

        # Layout for content on top of gradient
        content_layout = QVBoxLayout(bg_container)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(0)
        main_layout.addWidget(bg_container)

        # Header with logo and user info
        self.setup_header(content_layout)

        # Main content area with dynamic layout
        self.setup_main_content(content_layout)

        # Footer
        self.setup_footer(content_layout)

    def setup_header(self, parent_layout):
        """Setup the header with logo and controls"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 20)

        # Logo with modern styling
        logo_container = QFrame()
        logo_container.setFixedHeight(60)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)

        # Logo image or text
        self.logo_label = QLabel()
        logo_pixmap = QPixmap("assets/ultraviolette_automotive_logo.jpg")
        if not logo_pixmap.isNull():
            self.logo_label.setPixmap(
                logo_pixmap.scaled(
                    180, 50, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            )
        else:
            self.logo_label.setText("ULTRAVIOLETTE")
            self.logo_label.setFont(QFont("Montserrat", 18, QFont.Bold))
            self.logo_label.setStyleSheet(f"color: {self.uv_primary};")
        logo_layout.addWidget(self.logo_label)
        header_layout.addWidget(logo_container)

        # Spacer to push controls to right
        header_layout.addStretch()

        # Header controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)

        # Help button with modern icon
        self.help_button = QPushButton()
        self.help_button.setIcon(QIcon("assets/help_icon.png"))
        self.help_button.setIconSize(QSize(20, 20))
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
                background-color: {self.uv_primary};
            }}
        """)
        self.help_button.clicked.connect(self.show_help)
        controls_layout.addWidget(self.help_button)

        # Logout button with modern styling
        self.logout_button = QPushButton("Log Out")
        self.logout_button.setFont(QFont("Montserrat", 10, QFont.Bold))
        self.logout_button.setFixedSize(100, 40)
        self.logout_button.setCursor(Qt.PointingHandCursor)
        self.logout_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_primary};
                border-radius: 20px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 195, 255, 0.1);
                border: 2px solid {self.uv_hover};
            }}
            QPushButton:pressed {{
                border: 2px solid {self.uv_pressed};
            }}
        """)
        self.logout_button.clicked.connect(self.logout)
        controls_layout.addWidget(self.logout_button)

        header_layout.addLayout(controls_layout)
        parent_layout.addLayout(header_layout)

        # Add subtle separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet(f"""
            background-color: {self.uv_light_gray};
            min-height: 1px;
            max-height: 1px;
            margin: 0px;
        """)
        parent_layout.addWidget(separator)

    def setup_main_content(self, parent_layout):
        """Setup the main content area with dynamic layout"""
        # Create a stacked widget to switch between scan view and results view
        self.content_stack = QStackedWidget()
        parent_layout.addWidget(self.content_stack)

        # Scan View (initial view)
        self.scan_view = QWidget()
        self.setup_scan_view()
        self.content_stack.addWidget(self.scan_view)

        # Results View (shown after successful scan)
        self.results_view = QWidget()
        self.setup_results_view()
        self.content_stack.addWidget(self.results_view)

    def setup_scan_view(self):
        """Set up the initial scanning view"""
        scan_layout = QVBoxLayout(self.scan_view)
        scan_layout.setContentsMargins(0, 30, 0, 0)
        scan_layout.setSpacing(30)

        # Create tab widget with modern styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Montserrat", 10))
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {self.uv_light_gray};
                border-radius: 8px;
                top: -1px;
                background: {self.uv_darker};
            }}
            QTabBar::tab {{
                background: {self.uv_dark};
                color: {self.uv_light};
                border: 1px solid {self.uv_light_gray};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 20px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.uv_darker};
                color: {self.uv_primary};
                border-bottom: 2px solid {self.uv_primary};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background: {self.uv_gray};
            }}
        """)

        # Create scan tab
        scan_tab = QWidget()
        self.tab_widget.addTab(scan_tab, " Scan Barcode ")
        self.setup_scan_tab(scan_tab)

        # Create manual entry tab
        manual_tab = QWidget()
        self.tab_widget.addTab(manual_tab, " Manual Entry ")
        self.setup_manual_tab(manual_tab)

        scan_layout.addWidget(self.tab_widget)

    def setup_results_view(self):
        """Set up the results view that shows after scanning"""
        results_layout = QVBoxLayout(self.results_view)
        results_layout.setContentsMargins(0, 30, 0, 0)
        results_layout.setSpacing(30)

        # Results header
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignLeft)

        # Back button
        self.back_button = QPushButton("← Back to Scan")
        self.back_button.setFont(QFont("Montserrat", 12))
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_primary};
                border: none;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                color: {self.uv_hover};
                text-decoration: underline;
            }}
        """)
        self.back_button.clicked.connect(self.show_scan_view)
        header_layout.addWidget(self.back_button)
        header_layout.addStretch()
        results_layout.addLayout(header_layout)

        # Main content area with splitter
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {self.uv_light_gray};
            }}
        """)

        # Vehicle info section (top)
        vehicle_info_container = QWidget()
        vehicle_info_container.setStyleSheet("background: transparent;")
        vehicle_info_layout = QVBoxLayout(vehicle_info_container)
        vehicle_info_layout.setContentsMargins(0, 0, 0, 0)
        vehicle_info_layout.setSpacing(20)

        # Vehicle info title
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignLeft)
        info_icon = QLabel()
        info_icon.setPixmap(QPixmap("assets/info_icon.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(info_icon)
        title_layout.addSpacing(10)
        title_label = QLabel("Vehicle Information")
        title_label.setFont(QFont("Montserrat", 18, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        vehicle_info_layout.addLayout(title_layout)

        # Vehicle info cards (using grid layout for better organization)
        self.info_cards_container = QWidget()
        self.info_cards_layout = QGridLayout(self.info_cards_container)
        self.info_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.info_cards_layout.setSpacing(20)
        self.info_cards_layout.setColumnStretch(0, 1)
        self.info_cards_layout.setColumnStretch(1, 1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2D2D2D;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        scroll_area.setWidget(self.info_cards_container)
        vehicle_info_layout.addWidget(scroll_area)
        splitter.addWidget(vehicle_info_container)

        # Action buttons section (bottom)
        action_buttons_container = QWidget()
        action_buttons_container.setStyleSheet("background: transparent;")
        action_buttons_layout = QVBoxLayout(action_buttons_container)
        action_buttons_layout.setContentsMargins(0, 20, 0, 0)
        action_buttons_layout.setSpacing(20)

        # Button row
        button_row = QHBoxLayout()
        button_row.setSpacing(20)
        button_row.setContentsMargins(0, 0, 0, 0)

        # Continue with Analysis button
        self.continue_button = QPushButton("Continue with Analysis")
        self.continue_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.continue_button.setCursor(Qt.PointingHandCursor)
        self.continue_button.setFixedSize(220, 50)
        self.continue_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_primary};
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
        self.continue_button.setIcon(QIcon("assets/analysis_icon.png"))
        self.continue_button.clicked.connect(self.continue_with_analysis)
        button_row.addWidget(self.continue_button)

        # Rescan button
        self.rescan_button = QPushButton("Rescan")
        self.rescan_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.rescan_button.setCursor(Qt.PointingHandCursor)
        self.rescan_button.setFixedSize(220, 50)
        self.rescan_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_primary};
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 195, 255, 0.15);
                border: 2px solid {self.uv_hover};
            }}
            QPushButton:pressed {{
                border: 2px solid {self.uv_pressed};
            }}
        """)
        self.rescan_button.setIcon(QIcon("assets/rescan_icon.png"))
        self.rescan_button.clicked.connect(self.reset_scan_ui)
        button_row.addWidget(self.rescan_button)

        # Save button
        self.save_button = QPushButton("Save Information")
        self.save_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setFixedSize(220, 50)
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_primary};
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
        self.save_button.setIcon(QIcon("assets/save_icon.png"))
        self.save_button.clicked.connect(self.save_vehicle_info)
        button_row.addWidget(self.save_button)

        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setFixedSize(220, 50)
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_primary};
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 195, 255, 0.15);
                border: 2px solid {self.uv_hover};
            }}
            QPushButton:pressed {{
                border: 2px solid {self.uv_pressed};
            }}
        """)
        self.clear_button.setIcon(QIcon("assets/clear_icon.png"))
        self.clear_button.clicked.connect(self.clear_vehicle_info)
        button_row.addWidget(self.clear_button)

        action_buttons_layout.addLayout(button_row)
        splitter.addWidget(action_buttons_container)

        # Set initial sizes (70% for info, 30% for buttons)
        splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])
        results_layout.addWidget(splitter)

    def show_scan_view(self):
        """Switch back to the scan view"""
        self.content_stack.setCurrentWidget(self.scan_view)
        self.reset_scan_ui()

    def show_results_view(self):
        """Switch to the results view"""
        self.content_stack.setCurrentWidget(self.results_view)

    def setup_scan_tab(self, tab):
        """Set up the barcode scanning tab with modern design"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # Title with modern styling
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)

        # Title badge with gradient
        title_badge = QLabel()
        title_badge.setFixedSize(8, 50)
        title_badge.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 {self.uv_primary}, stop:1 {self.uv_hover});
            border-radius: 4px;
        """)
        title_layout.addWidget(title_badge)
        title_layout.addSpacing(15)

        # Title container
        title_container = QVBoxLayout()
        title_container.setSpacing(5)
        title = QLabel("Vehicle Identification")
        title.setFont(QFont("Montserrat", 22, QFont.Bold))
        title.setStyleSheet(f"color: {self.uv_light};")
        title_container.addWidget(title)
        subtitle = QLabel("Scan the vehicle barcode to begin")
        subtitle.setFont(QFont("Montserrat", 12))
        subtitle.setStyleSheet("color: #AAAAAA;")
        title_container.addWidget(subtitle)
        title_layout.addLayout(title_container)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Scan card with modern design
        scan_card = QFrame()
        scan_card.setObjectName("scanCard")

        # Add shadow effect
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(30)
        card_shadow.setColor(QColor(0, 0, 0, 100))
        card_shadow.setOffset(0, 5)
        scan_card.setGraphicsEffect(card_shadow)
        scan_card.setStyleSheet(f"""
            QFrame#scanCard {{
                background: {self.uv_darker};
                border: 1px solid {self.uv_light_gray};
                border-radius: 12px;
            }}
        """)

        scan_layout = QVBoxLayout(scan_card)
        scan_layout.setContentsMargins(40, 40, 40, 40)
        scan_layout.setSpacing(30)
        scan_layout.setAlignment(Qt.AlignCenter)

        # Scan image container with animated border
        self.scan_image_container = QFrame()
        self.scan_image_container.setFixedSize(220, 220)
        self.scan_image_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 110px;
                border: 2px solid {self.uv_primary};
            }}
        """)
        scan_image_layout = QVBoxLayout(self.scan_image_container)
        scan_image_layout.setContentsMargins(20, 20, 20, 20)

        # Scan image or animation
        self.scan_image = QLabel()
        scan_pixmap = QPixmap("assets/barcode_scan.png")
        if scan_pixmap.isNull():
            self.scan_image.setText("[ Scan ]")
            self.scan_image.setStyleSheet(f"""
                color: {self.uv_primary};
                font-size: 16px;
                padding: 40px;
                border: none;
            """)
            self.scan_image.setAlignment(Qt.AlignCenter)
        else:
            self.scan_image.setPixmap(
                scan_pixmap.scaled(
                    160, 160, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            )
            self.scan_image.setStyleSheet("background: transparent; border: none;")
            self.scan_image.setAlignment(Qt.AlignCenter)
        scan_image_layout.addWidget(self.scan_image)
        scan_layout.addWidget(self.scan_image_container, alignment=Qt.AlignCenter)

        # Scan instructions with animation
        self.scan_instructions = QLabel("Position the barcode scanner over the vehicle's barcode")
        self.scan_instructions.setFont(QFont("Montserrat", 12))
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
        self.scan_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.uv_gray};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {self.uv_primary};
                border-radius: 3px;
            }}
        """)
        scan_layout.addWidget(self.scan_progress, alignment=Qt.AlignCenter)
        self.scan_progress.hide()

        # Status message
        self.status_message = QLabel("Ready to scan")
        self.status_message.setFont(QFont("Montserrat", 11))
        self.status_message.setAlignment(Qt.AlignCenter)
        self.status_message.setStyleSheet(f"color: {self.uv_primary};")
        scan_layout.addWidget(self.status_message)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(20)

        # Scan button with modern styling
        self.scan_button = QPushButton("Start Scanning")
        self.scan_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.scan_button.setFixedSize(220, 50)
        self.scan_button.setCursor(Qt.PointingHandCursor)
        self.scan_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_primary};
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.uv_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.uv_pressed};
            }}
        """)

        # Add scan icon if available
        scan_icon = QIcon("assets/scan_icon.png")
        if not scan_icon.isNull():
            self.scan_button.setIcon(scan_icon)
            self.scan_button.setIconSize(QSize(20, 20))
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.cancel_button.setFixedWidth(150)
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_primary};
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 195, 255, 0.15);
                border: 2px solid {self.uv_hover};
            }}
            QPushButton:pressed {{
                border: 2px solid {self.uv_pressed};
            }}
        """)
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.hide()
        button_layout.addWidget(self.cancel_button)

        scan_layout.addLayout(button_layout)
        layout.addWidget(scan_card)

    def setup_manual_tab(self, tab):
        """Set up the manual entry tab with modern design"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # Title with modern styling
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)

        # Title badge with gradient
        title_badge = QLabel()
        title_badge.setFixedSize(8, 50)
        title_badge.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 {self.uv_primary}, stop:1 {self.uv_hover});
            border-radius: 4px;
        """)
        title_layout.addWidget(title_badge)
        title_layout.addSpacing(15)

        # Title container
        title_container = QVBoxLayout()
        title_container.setSpacing(5)
        title = QLabel("Manual Entry")
        title.setFont(QFont("Montserrat", 22, QFont.Bold))
        title.setStyleSheet(f"color: {self.uv_light};")
        title_container.addWidget(title)
        subtitle = QLabel("Enter vehicle information manually")
        subtitle.setFont(QFont("Montserrat", 12))
        subtitle.setStyleSheet("color: #AAAAAA;")
        title_container.addWidget(subtitle)
        title_layout.addLayout(title_container)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Manual entry card with modern design
        manual_card = QFrame()
        manual_card.setObjectName("manualCard")

        # Add shadow effect
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(30)
        card_shadow.setColor(QColor(0, 0, 0, 100))
        card_shadow.setOffset(0, 5)
        manual_card.setGraphicsEffect(card_shadow)
        manual_card.setStyleSheet(f"""
            QFrame#manualCard {{
                background: {self.uv_darker};
                border: 1px solid {self.uv_light_gray};
                border-radius: 12px;
            }}
        """)

        manual_layout = QVBoxLayout(manual_card)
        manual_layout.setContentsMargins(40, 40, 40, 40)
        manual_layout.setSpacing(25)

        # Form layout for input fields
        form_layout = QFormLayout()
        form_layout.setSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # VIN input with modern styling
        vin_label = QLabel("VIN:")
        vin_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Enter Vehicle Identification Number")
        self.vin_input.setMaxLength(17)
        self.vin_input.setFont(QFont("Montserrat", 11))
        self.vin_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
            QLineEdit:focus {{
                border: 1px solid {self.uv_primary};
            }}
        """)
        form_layout.addRow(vin_label, self.vin_input)

        # IMEI input
        imei_label = QLabel("IMEI:")
        imei_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText("Enter IMEI Number")
        self.imei_input.setMaxLength(15)
        self.imei_input.setFont(QFont("Montserrat", 11))
        self.imei_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
            QLineEdit:focus {{
                border: 1px solid {self.uv_primary};
            }}
        """)
        form_layout.addRow(imei_label, self.imei_input)

        # UUID input
        uuid_label = QLabel("UUID:")
        uuid_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.uuid_input = QLineEdit()
        self.uuid_input.setPlaceholderText("Enter UUID")
        self.uuid_input.setMaxLength(36)
        self.uuid_input.setFont(QFont("Montserrat", 11))
        self.uuid_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
            QLineEdit:focus {{
                border: 1px solid {self.uv_primary};
            }}
        """)
        form_layout.addRow(uuid_label, self.uuid_input)

        manual_layout.addLayout(form_layout)

        # Info text
        info_label = QLabel(
            "Enter the vehicle information fields above. All fields are optional but at least one is required."
        )
        info_label.setFont(QFont("Montserrat", 10))
        info_label.setStyleSheet("color: #AAAAAA;")
        info_label.setWordWrap(True)
        manual_layout.addWidget(info_label)

        # Submit button with modern styling
        self.submit_button = QPushButton("Submit Information")
        self.submit_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        self.submit_button.setFixedSize(220, 50)
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_primary};
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
                font-weight: bold;
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

    def setup_footer(self, parent_layout):
        """Setup the footer with version info"""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 20, 0, 0)
        version_label = QLabel("Ultraviolette Dashboard v1.2.0")
        version_label.setFont(QFont("Montserrat", 9))
        version_label.setStyleSheet(f"color: {self.uv_footer};")
        footer_layout.addWidget(version_label, alignment=Qt.AlignLeft)
        copyright_label = QLabel("© 2025 Ultraviolette Automotive")
        copyright_label.setFont(QFont("Montserrat", 9))
        copyright_label.setStyleSheet(f"color: {self.uv_footer};")
        footer_layout.addWidget(copyright_label, alignment=Qt.AlignRight)
        parent_layout.addLayout(footer_layout)

    def update_pulse(self):
        """Update the pulse animation for the scan button"""
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
                background-color: {self.uv_primary};
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

    def start_scan(self):
        """Start the barcode scanning process with enhanced UI feedback"""
        # Update UI for scanning state
        self.current_scan_state = "scanning"
        self.is_scanning = True
        # UI changes
        self.scan_button.hide()
        self.cancel_button.show()
        self.scan_progress.show()
        self.scan_progress.setValue(0)
        self.status_message.setText("Initializing scanner...")
        self.status_message.setStyleSheet(f"color: {self.uv_primary};")
        # Start the pulse animation
        self.pulse_timer.start(50)
        # Initialize and start the scan thread
        self.scan_thread = BarcodeScanThread()
        self.scan_thread.scan_complete.connect(self.handle_scan_complete)
        self.scan_thread.scan_error.connect(self.handle_scan_error)
        self.scan_thread.scan_progress.connect(self.update_scan_progress)
        self.scan_thread.scan_status.connect(self.update_scan_status)
        self.scan_thread.start()

    def update_scan_status(self, status):
        """Update the status message during scanning"""
        self.status_message.setText(status)
        # Change color based on status
        if "error" in status.lower():
            self.status_message.setStyleSheet(f"color: {self.uv_error};")
        elif "ready" in status.lower():
            self.status_message.setStyleSheet(f"color: {self.uv_primary};")
        else:
            self.status_message.setStyleSheet(f"color: {self.uv_light};")

    def cancel_scan(self):
        """Cancel the current scanning process with smooth UI transition"""
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.stop()
            self.scan_thread.terminate()
            self.scan_thread = None
        self.reset_scan_ui()
        self.status_message.setText("Scan cancelled")
        self.status_message.setStyleSheet(f"color: {self.uv_error};")
        # Fade out the status message after delay
        QTimer.singleShot(2000, self.fade_status_message)

    def fade_status_message(self):
        """Fade out the status message"""
        self.status_fade_animation.start()

    def reset_scan_ui(self):
        """Reset UI elements after scanning"""
        self.current_scan_state = "ready"
        self.is_scanning = False
        # UI reset
        self.scan_button.show()
        self.cancel_button.hide()
        self.scan_progress.hide()
        self.pulse_timer.stop()
        # Reset status message after delay if not already set
        if self.status_message.text() in ("", "Ready to scan"):
            self.status_message.setText("Ready to scan")
            self.status_message.setStyleSheet(f"color: {self.uv_primary};")

    def update_scan_progress(self, value):
        """Update the progress bar during scanning"""
        self.scan_progress.setValue(value)
        # Change color based on progress
        if value < 30:
            self.scan_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {self.uv_gray};
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background-color: {self.uv_error};
                    border-radius: 3px;
                }}
            """)
        elif value < 70:
            self.scan_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {self.uv_gray};
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background-color: {self.uv_warning};
                    border-radius: 3px;
                }}
            """)
        else:
            self.scan_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {self.uv_gray};
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background-color: {self.uv_primary};
                    border-radius: 3px;
                }}
            """)

    def handle_scan_complete(self, barcode):
        """Handle successful barcode scan with enhanced UI feedback"""
        global SCANNED_BARCODE
        # Store the scanned barcode
        SCANNED_BARCODE = barcode
        # Parse the barcode data
        try:
            parts = barcode.split(';')
            parsed_data = {}
            for part in parts:
                key, value = part.split(':')
                parsed_data[key.lower()] = value.strip()
            self.vehicle_info['vin'] = parsed_data.get('vin', '')
            self.vehicle_info['imei'] = parsed_data.get('imei', '')
            self.vehicle_info['uuid'] = parsed_data.get('uuid', '')
        except Exception as e:
            print(f"Error parsing barcode: {str(e)}")
            self.vehicle_info['uuid'] = barcode
        # Display the vehicle information in results view
        self.display_vehicle_info()
        # Switch to results view
        self.show_results_view()
        # Emit the scanned data
        self.scan_successful.emit(self.vehicle_info)

    def display_vehicle_info(self):
        """Display the vehicle information in a modern card layout"""
        # Clear previous info cards
        for i in reversed(range(self.info_cards_layout.count())):
            widget = self.info_cards_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Add vehicle info cards in a grid layout
        row = 0
        col = 0
        if self.vehicle_info['vin']:
            self.add_info_card(row, col, "VIN", self.vehicle_info['vin'], "assets/vin_icon.png")
            col += 1
            if col > 1:
                col = 0
                row += 1
        if self.vehicle_info['imei']:
            self.add_info_card(row, col, "IMEI", self.vehicle_info['imei'], "assets/imei_icon.png")
            col += 1
            if col > 1:
                col = 0
                row += 1
        if self.vehicle_info['uuid']:
            self.add_info_card(row, col, "UUID", self.vehicle_info['uuid'], "assets/uuid_icon.png")

    def add_info_card(self, row, col, title, value, icon_path=None):
        """Add an information card to the grid layout"""
        card = QFrame()
        card.setObjectName("infoCard")
        card.setStyleSheet(f"""
            QFrame#infoCard {{
                background: {self.uv_gray};
                border-radius: 8px;
                border: 1px solid {self.uv_light_gray};
            }}
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(20)
        # Add icon if available
        if icon_path and os.path.exists(icon_path):
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            card_layout.addWidget(icon_label)
        # Add title and value
        text_layout = QVBoxLayout()
        text_layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        title_label.setStyleSheet(f"color: {self.uv_primary};")
        text_layout.addWidget(title_label)
        value_label = QLabel(value)
        value_label.setFont(QFont("Montserrat", 14))
        value_label.setStyleSheet(f"color: {self.uv_light};")
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_layout.addWidget(value_label)
        card_layout.addLayout(text_layout)
        card_layout.addStretch()
        # Add copy button
        copy_button = QPushButton()
        copy_button.setIcon(QIcon("assets/copy_icon.png"))
        copy_button.setIconSize(QSize(16, 16))
        copy_button.setFixedSize(32, 32)
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_primary};
                border-radius: 16px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.uv_hover};
            }}
        """)
        copy_button.clicked.connect(lambda _, v=value: self.copy_to_clipboard(v))
        card_layout.addWidget(copy_button)
        self.info_cards_layout.addWidget(card, row, col)

    def copy_to_clipboard(self, text):
        """Copy text to clipboard and show feedback"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # Show temporary feedback
        feedback = QLabel("Copied!")
        feedback.setFont(QFont("Montserrat", 10))
        feedback.setStyleSheet(f"""
            background-color: {self.uv_secondary};
            color: {self.uv_dark};
            padding: 4px 8px;
            border-radius: 4px;
        """)
        feedback.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        feedback.move(QCursor.pos() + QPoint(15, 15))
        feedback.show()
        # Hide after delay
        QTimer.singleShot(1000, feedback.hide)

    def continue_with_analysis(self):
        """Handle the 'Continue with Analysis' button click"""
        # Validate scanned data
        if not any(self.vehicle_info.values()):
            QMessageBox.warning(
                self,
                "Incomplete Data",
                "No vehicle information available for analysis.")
            return
        try:
            from gui.main_window import MainWindow
            # Create MainWindow instance and pass the scanned data
            self.main_window = MainWindow(scanned_data=self.vehicle_info)
            self.main_window.show()
            self.close()
        except ImportError as e:
            print("Import failed:", e)
            QMessageBox.critical(self, "Error", "Failed to open analysis window")
            return

    def handle_scan_error(self, error_message):
        """Handle scanning errors with enhanced UI feedback"""
        self.reset_scan_ui()
        self.status_message.setText(f"✗ {error_message}")
        self.status_message.setStyleSheet(f"color: {self.uv_error};")
        QTimer.singleShot(2000, self.fade_status_message)

    def submit_manual_info(self):
        """Process manually entered vehicle information"""
        # Get values from input fields
        vin = self.vin_input.text().strip()
        imei = self.imei_input.text().strip()
        uuid = self.uuid_input.text().strip()
        # Validate - at least one field should have a value
        if not (vin or imei or uuid):
            self.status_message.setText("Please enter at least one field")
            self.status_message.setStyleSheet(f"color: {self.uv_error};")
            return
        # Store the values
        self.vehicle_info['vin'] = vin
        self.vehicle_info['imei'] = imei
        self.vehicle_info['uuid'] = uuid
        # Display success message
        self.status_message.setText("✓ Information submitted successfully!")
        self.status_message.setStyleSheet(f"color: {self.uv_secondary};")
        # Clear input fields
        self.vin_input.clear()
        self.imei_input.clear()
        self.uuid_input.clear()
        # Display the vehicle information in results view
        self.display_vehicle_info()
        # Switch to results view
        self.show_results_view()
        # Reset after 2 seconds
        QTimer.singleShot(2000, self.fade_status_message)

    def save_vehicle_info(self):
        """Save the vehicle information to a file"""
        if not any(self.vehicle_info.values()):
            self.status_message.setText("No vehicle information to save")
            self.status_message.setStyleSheet(f"color: {self.uv_error};")
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
                file.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            # Show success message in results view
            feedback = QLabel("✓ Information saved successfully!")
            feedback.setFont(QFont("Montserrat", 11))
            feedback.setStyleSheet(f"color: {self.uv_secondary};")
            feedback.setAlignment(Qt.AlignCenter)
            # Create a temporary widget for the message
            message_widget = QWidget()
            message_layout = QVBoxLayout(message_widget)
            message_layout.addWidget(feedback)
            # Add to the info cards layout temporarily
            self.info_cards_layout.addWidget(message_widget, self.info_cards_layout.rowCount(), 0, 1, 2)
            # Remove after delay
            QTimer.singleShot(2000, lambda: message_widget.setParent(None))
        except Exception as e:
            feedback = QLabel(f"✗ Error saving file: {str(e)}")
            feedback.setFont(QFont("Montserrat", 11))
            feedback.setStyleSheet(f"color: {self.uv_error};")
            feedback.setAlignment(Qt.AlignCenter)
            message_widget = QWidget()
            message_layout = QVBoxLayout(message_widget)
            message_layout.addWidget(feedback)
            self.info_cards_layout.addWidget(message_widget, self.info_cards_layout.rowCount(), 0, 1, 2)
            QTimer.singleShot(2000, lambda: message_widget.setParent(None))

    def clear_vehicle_info(self):
        """Clear the displayed vehicle information"""
        # Clear stored info
        self.vehicle_info = {
            'vin': '',
            'imei': '',
            'uuid': ''
        }
        # Switch back to scan view
        self.show_scan_view()
        # Reset scan UI elements
        self.scan_image_container.show()
        self.scan_button.show()
        self.scan_instructions.show()
        # Show confirmation message
        self.status_message.setText("Vehicle information cleared")
        self.status_message.setStyleSheet(f"color: {self.uv_warning};")
        QTimer.singleShot(2000, self.fade_status_message)

    def show_help(self):
        """Show help information in a modern dialog"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setMinimumSize(600, 500)
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        help_dialog.setGraphicsEffect(shadow)
        help_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {self.uv_darker};
                color: {self.uv_light};
                border-radius: 12px;
                border: 1px solid {self.uv_light_gray};
            }}
        """)
        help_layout = QVBoxLayout(help_dialog)
        help_layout.setContentsMargins(30, 30, 30, 30)
        help_layout.setSpacing(20)
        # Title with icon
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignLeft)
        help_icon = QLabel()
        help_icon.setPixmap(QPixmap("assets/help_icon.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(help_icon)
        title_layout.addSpacing(10)
        title = QLabel("Barcode Scanner Help")
        title.setFont(QFont("Montserrat", 18, QFont.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()
        help_layout.addLayout(title_layout)
        # Help content in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2D2D2D;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 15, 5)
        content_layout.setSpacing(20)
        help_topics = [
            ("Barcode Scanning", "Position the scanner over the vehicle's barcode and click 'Start Scanning'. Hold steady until the scan completes."),
            ("Manual Entry", "If scanning fails, you can manually enter the VIN, IMEI, or UUID in the 'Manual Entry' tab."),
            ("Vehicle Information", "The scanned or entered information will display in cards below. You can copy individual values or save all information to a file."),
            ("Troubleshooting", "If scanning fails, ensure there's proper lighting and the barcode is clean and undamaged."),
            ("Support Contact", "For technical assistance, contact support at support@ultraviolette.com or call +91-1234567890.")
        ]
        for title, content in help_topics:
            topic_card = QFrame()
            topic_card.setObjectName("topicCard")
            topic_card.setStyleSheet(f"""
                QFrame#topicCard {{
                    background: {self.uv_gray};
                    border-radius: 8px;
                    border: 1px solid {self.uv_light_gray};
                }}
            """)
            topic_layout = QVBoxLayout(topic_card)
            topic_layout.setContentsMargins(15, 15, 15, 15)
            topic_layout.setSpacing(10)
            topic_title = QLabel(title)
            topic_title.setFont(QFont("Montserrat", 14, QFont.Bold))
            topic_title.setStyleSheet(f"color: {self.uv_primary};")
            topic_layout.addWidget(topic_title)
            topic_content = QLabel(content)
            topic_content.setFont(QFont("Montserrat", 11))
            topic_content.setWordWrap(True)
            topic_content.setStyleSheet(f"color: {self.uv_light};")
            topic_layout.addWidget(topic_content)
            content_layout.addWidget(topic_card)
        scroll_area.setWidget(content_widget)
        help_layout.addWidget(scroll_area)
        # Close button
        close_button = QPushButton("Close")
        close_button.setFont(QFont("Montserrat", 12, QFont.Bold))
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setFixedSize(120, 40)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_primary};
                color: {self.uv_dark};
                border: none;
                border-radius: 20px;
                padding: 8px 15px;
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
        """Handle logout action with confirmation dialog"""
        confirm_dialog = QMessageBox()
        confirm_dialog.setWindowTitle("Confirm Logout")
        confirm_dialog.setText("Are you sure you want to log out?")
        confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm_dialog.setDefaultButton(QMessageBox.No)
        # Apply custom styling to the message box
        confirm_dialog.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.uv_darker};
                color: {self.uv_light};
                border: 1px solid {self.uv_light_gray};
                border-radius: 8px;
            }}
            QMessageBox QLabel {{
                color: {self.uv_light};
            }}
            QMessageBox QPushButton {{
                background-color: {self.uv_gray};
                color: {self.uv_light};
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {self.uv_primary};
                color: {self.uv_dark};
            }}
        """)
        confirm = confirm_dialog.exec_()
        if confirm == QMessageBox.Yes:
            from gui.login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set application-wide style
    app.setStyle("Fusion")
    # Set application font
    font = QFont("Montserrat", 10)
    app.setFont(font)
    # Create and show main window
    window = BarcodeScanWindow()
    window.show()
    sys.exit(app.exec_())