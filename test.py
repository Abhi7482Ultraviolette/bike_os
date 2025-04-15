import sys
import os
import serial
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QMessageBox, QProgressBar, QFileDialog, QListWidget,
    QFrame, QSplitter, QGridLayout, QSpacerItem, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QGraphicsDropShadowEffect,
    QDialog, QTabWidget, QFormLayout, QStackedWidget, QScrollArea, QGraphicsBlurEffect
)
from PyQt5.QtGui import (
    QFont, QPixmap, QColor, QPalette, QIcon, QFontDatabase, 
    QLinearGradient, QPainter, QBrush, QMovie, QCursor, QRadialGradient,
    QFontMetrics
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, 
    QEasingCurve, QRect, QTimer, QPoint, QParallelAnimationGroup,
    QSequentialAnimationGroup, QAbstractAnimation
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
        # Enhanced Ultraviolette color palette with more depth and vibrancy
        self.uv_primary = "#00C3FF"  # Primary blue
        self.uv_primary_dark = "#0099CC"  # Darker primary
        self.uv_primary_light = "#66D9FF"  # Lighter primary
        self.uv_secondary = "#00E676"  # Green for success
        self.uv_secondary_dark = "#00B058"  # Darker green
        self.uv_dark = "#121212"  # Dark background
        self.uv_darker = "#0A0A0A"  # Even darker
        self.uv_darkest = "#050505"  # Darkest for depth
        self.uv_light = "#FFFFFF"  # White text
        self.uv_light_alt = "#F0F0F0"  # Slightly off-white
        self.uv_gray = "#2D2D2D"  # Input fields
        self.uv_light_gray = "#444444"  # Borders
        self.uv_hover = "#33D1FF"  # Hover state
        self.uv_pressed = "#0099CC"  # Pressed state
        self.uv_error = "#FF5252"  # Error color
        self.uv_warning = "#FFAB40"  # Warning color
        self.uv_footer = "#777777"  # Footer text (slightly brighter)
        self.uv_accent = "#FF7043"  # Accent color for highlights
        self.uv_card_bg = "#161616"  # Card background
        self.uv_card_border = "rgba(255, 255, 255, 0.08)"  # Subtle border

        # Window setup with polished appearance
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
        
        # Apply glass morphism effect to main containers
        self.apply_glass_morphism()
        
        # Add subtle animation on startup
        self.animate_startup()
    
    def animate_startup(self):
        """Add a subtle animation when the application starts"""
        # Create fade-in animation for the main window
        self.setWindowOpacity(0)
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(800)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setEasingCurve(QEasingCurve.OutCubic)
        self.fade_in.start()

    def apply_glass_morphism(self):
        """Apply glass morphism effect to key UI elements"""
        # This creates a subtle frosted glass effect on cards
        glass_style = f"""
            background-color: rgba(30, 30, 30, 0.8);
            border: 1px solid {self.uv_card_border};
            border-radius: 12px;
        """
        
        # Find all frames that should have glass effect
        for widget in self.findChildren(QFrame):
            if widget.objectName() in ["scanCard", "manualCard", "infoCard", "topicCard"]:
                current_style = widget.styleSheet()
                widget.setStyleSheet(current_style + glass_style)
                
                # Add enhanced shadow effect
                shadow = QGraphicsDropShadowEffect()
                shadow.setBlurRadius(20)
                shadow.setColor(QColor(0, 0, 0, 80))
                shadow.setOffset(0, 4)
                widget.setGraphicsEffect(shadow)

    def setup_animations(self):
        """Setup various UI animations"""
        # Initialize fade_effect
        self.fade_effect = QGraphicsBlurEffect()
        self.fade_effect.setBlurRadius(0)
        
        # Scan button pulse animation with improved timing
        self.pulse_animation = QPropertyAnimation(self.scan_button, b"geometry")
        self.pulse_animation.setDuration(1500)
        self.pulse_animation.setLoopCount(-1)  # Infinite loop
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Status message fade animation
        self.status_fade_animation = QPropertyAnimation(self.status_message, b"windowOpacity")
        self.status_fade_animation.setDuration(800)
        self.status_fade_animation.setStartValue(1.0)
        self.status_fade_animation.setEndValue(0.0)
        self.status_fade_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Scan image animation - pulsing glow effect
        self.scan_image_animation = QPropertyAnimation(self.scan_image_container, b"styleSheet")
        self.scan_image_animation.setDuration(2000)
        self.scan_image_animation.setLoopCount(-1)
        
        # Define start and end styles for the animation
        base_style = f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 110px;
                border: 2px solid {self.uv_primary};
            }}
        """
        
        glow_style = f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 110px;
                border: 2px solid {self.uv_primary};
            }}
        """
        
        self.scan_image_animation.setStartValue(base_style)
        self.scan_image_animation.setEndValue(glow_style)

    def load_fonts(self):
        """Load custom fonts if available"""
        try:
            # Check if Montserrat font is already in system
            fonts = QFontDatabase().families()
            
            # Define preferred fonts with fallbacks
            self.font_family = "Montserrat"
            self.fallback_fonts = ["Roboto", "Segoe UI", "Arial", "Helvetica", "Sans-serif"]
            
            if self.font_family not in fonts:
                # If font file exists, load it
                font_paths = [
                    "assets/fonts/Montserrat-Regular.ttf",
                    "assets/fonts/Montserrat-Bold.ttf",
                    "assets/fonts/Montserrat-Medium.ttf",
                    "assets/fonts/Montserrat-Light.ttf"
                ]
                for path in font_paths:
                    if os.path.exists(path):
                        QFontDatabase.addApplicationFont(path)
                        
            # Set application-wide default font
            app_font = QFont(self.font_family, 10)
            QApplication.setFont(app_font)
                        
        except Exception as e:
            print(f"Font loading error: {str(e)}")

    def apply_dark_theme(self):
        """Apply enhanced dark theme with modern touches and depth"""
        # Create a palette with richer colors
        palette = QPalette()
        
        # Main colors
        palette.setColor(QPalette.Window, QColor(self.uv_dark))
        palette.setColor(QPalette.WindowText, QColor(self.uv_light))
        palette.setColor(QPalette.Base, QColor(self.uv_gray))
        palette.setColor(QPalette.AlternateBase, QColor(self.uv_darker))
        
        # UI element colors
        palette.setColor(QPalette.ToolTipBase, QColor(self.uv_darker))
        palette.setColor(QPalette.ToolTipText, QColor(self.uv_light))
        palette.setColor(QPalette.Text, QColor(self.uv_light))
        palette.setColor(QPalette.Button, QColor(self.uv_gray))
        palette.setColor(QPalette.ButtonText, QColor(self.uv_light))
        
        # Highlight colors
        palette.setColor(QPalette.BrightText, QColor(self.uv_primary_light))
        palette.setColor(QPalette.Link, QColor(self.uv_primary))
        palette.setColor(QPalette.Highlight, QColor(self.uv_primary))
        palette.setColor(QPalette.HighlightedText, QColor(self.uv_dark))
        
        # Disabled state
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#555555"))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#555555"))
        
        self.setPalette(palette)
        
        # Set global stylesheet for common widgets
        QApplication.instance().setStyleSheet(f"""
            QToolTip {{
                background-color: {self.uv_darker};
                color: {self.uv_light};
                border: 1px solid {self.uv_primary};
                padding: 5px;
                border-radius: 3px;
                opacity: 200;
            }}
            
            QScrollBar:vertical {{
                border: none;
                background: {self.uv_gray};
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            
            QScrollBar::handle:vertical {{
                background: {self.uv_light_gray};
                min-height: 20px;
                border-radius: 4px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: {self.uv_primary};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                border: none;
                background: {self.uv_gray};
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            
            QScrollBar::handle:horizontal {{
                background: {self.uv_light_gray};
                min-width: 20px;
                border-radius: 4px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background: {self.uv_primary};
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)

    def init_ui(self):
        """Create the enhanced barcode scanning UI with depth and polish"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with gradient background
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create a container with enhanced gradient background
        bg_container = QWidget()
        bg_container.setObjectName("bgContainer")
        bg_container.setStyleSheet(f"""
            QWidget#bgContainer {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {self.uv_darkest}, 
                    stop:0.3 {self.uv_darker}, 
                    stop:0.7 {self.uv_dark},
                    stop:1 {self.uv_darkest}
                );
                border-radius: 0px;
            }}
        """)

        # Add subtle noise texture overlay for depth
        noise_overlay = QLabel(bg_container)
        noise_overlay.setObjectName("noiseOverlay")
        noise_overlay.setStyleSheet("""
            QLabel#noiseOverlay {
                background-image: url(assets/noise_texture.png);
                background-repeat: repeat;
                opacity: 0.03;
            }
        """)
        noise_overlay.setGeometry(0, 0, self.width(), self.height())
        
        # Layout for content on top of gradient
        content_layout = QVBoxLayout(bg_container)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(0)
        main_layout.addWidget(bg_container)

        # Header with logo and user info
        self.setup_header(content_layout)

        # Add subtle separator with glow
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet(f"""
            background-color: {self.uv_light_gray};
            min-height: 1px;
            max-height: 1px;
            margin: 0px;
            border-bottom: 1px solid rgba(0, 195, 255, 0.1);
        """)
        content_layout.addWidget(separator)

        # Main content area with dynamic layout
        self.setup_main_content(content_layout)

        # Footer
        self.setup_footer(content_layout)
        
        # Make sure the noise overlay stays on top and covers the entire window
        self.resizeEvent = lambda event: noise_overlay.setGeometry(0, 0, self.width(), self.height())

    def setup_header(self, parent_layout):
        """Setup the header with logo and controls"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 20)

        # Logo with modern styling and subtle animation
        logo_container = QFrame()
        logo_container.setFixedHeight(60)
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)

        # Logo image or text with glow effect
        self.logo_label = QLabel()
        logo_pixmap = QPixmap("assets/ultraviolette_automotive_logo.jpg")
        if not logo_pixmap.isNull():
            # Add subtle glow to logo
            glow_effect = QGraphicsDropShadowEffect()
            glow_effect.setBlurRadius(15)
            glow_effect.setColor(QColor(0, 195, 255, 70))
            glow_effect.setOffset(0, 0)
            
            self.logo_label.setPixmap(
                logo_pixmap.scaled(
                    180, 50, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            )
            self.logo_label.setGraphicsEffect(glow_effect)
        else:
            self.logo_label.setText("ULTRAVIOLETTE")
            self.logo_label.setFont(QFont(self.font_family, 18, QFont.Bold))
            self.logo_label.setStyleSheet(f"""
                color: {self.uv_primary};
                text-shadow: 0 0 10px rgba(0, 195, 255, 0.5);
            """)
        logo_layout.addWidget(self.logo_label)
        header_layout.addWidget(logo_container)

        # Spacer to push controls to right
        header_layout.addStretch()

        # Header controls with improved styling
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)

        # Help button with modern icon and tooltip
        self.help_button = QPushButton()
        self.help_button.setIcon(QIcon("assets/help_icon.png"))
        self.help_button.setIconSize(QSize(20, 20))
        self.help_button.setFixedSize(40, 40)
        self.help_button.setCursor(Qt.PointingHandCursor)
        self.help_button.setToolTip("Help & Documentation")
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
                box-shadow: 0 0 10px {self.uv_primary};
            }}
            QPushButton:pressed {{
                background-color: {self.uv_primary_dark};
            }}
        """)
        self.help_button.clicked.connect(self.show_help)
        controls_layout.addWidget(self.help_button)

        # Logout button with modern styling and icon
        self.logout_button = QPushButton("Log Out")
        self.logout_button.setFont(QFont(self.font_family, 10, QFont.Bold))
        self.logout_button.setFixedSize(100, 40)
        self.logout_button.setCursor(Qt.PointingHandCursor)
        self.logout_button.setIcon(QIcon("assets/logout_icon.png"))
        self.logout_button.setIconSize(QSize(16, 16))
        self.logout_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_primary};
                border-radius: 20px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 195, 255, 0.15);
                border: 2px solid {self.uv_hover};
            }}
            QPushButton:pressed {{
                border: 2px solid {self.uv_pressed};
                background-color: rgba(0, 195, 255, 0.25);
            }}
        """)
        self.logout_button.clicked.connect(self.logout)
        controls_layout.addWidget(self.logout_button)

        header_layout.addLayout(controls_layout)
        parent_layout.addLayout(header_layout)

    def setup_main_content(self, parent_layout):
        """Setup the main content area with dynamic layout and smooth transitions"""
        # Create a stacked widget to switch between scan view and results view
        self.content_stack = QStackedWidget()
        
        # Add fade transition effect between pages
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background: transparent;
            }
        """)
        
        parent_layout.addWidget(self.content_stack)

        # Scan View (initial view)
        self.scan_view = QWidget()
        self.setup_scan_view()
        self.content_stack.addWidget(self.scan_view)

        # Results View (shown after successful scan)
        self.results_view = QWidget()
        self.setup_results_view()
        self.content_stack.addWidget(self.results_view)
        
        # Apply glass morphism effect to main containers
        self.apply_glass_morphism()
        
        # Add subtle animation on startup
        self.animate_startup()
    
    def setup_scan_view(self):
        """Set up the initial scanning view with enhanced visual appeal"""
        scan_layout = QVBoxLayout(self.scan_view)
        scan_layout.setContentsMargins(0, 30, 0, 0)
        scan_layout.setSpacing(30)

        # Create tab widget with modern styling and animation effects
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont(self.font_family, 10))
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {self.uv_light_gray};
                border-radius: 12px;
                top: -1px;
                background: {self.uv_darker};
            }}
            QTabBar::tab {{
                background: {self.uv_dark};
                color: {self.uv_light};
                border: 1px solid {self.uv_light_gray};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 25px;
                margin-right: 4px;
                font-weight: normal;
            }}
            QTabBar::tab:selected {{
                background: {self.uv_darker};
                color: {self.uv_primary};
                border-bottom: 3px solid {self.uv_primary};
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background: {self.uv_gray};
                border-bottom: 2px solid rgba(0, 195, 255, 0.3);
            }}
        """)
        
        # Add tab change animation
        self.tab_widget.currentChanged.connect(self.animate_tab_change)

        # Create scan tab
        scan_tab = QWidget()
        self.tab_widget.addTab(scan_tab, " Scan Barcode ")
        self.setup_scan_tab(scan_tab)

        # Create manual entry tab
        manual_tab = QWidget()
        self.tab_widget.addTab(manual_tab, " Manual Entry ")
        self.setup_manual_tab(manual_tab)

        scan_layout.addWidget(self.tab_widget)

    def animate_tab_change(self, index):
        """Animate tab change with subtle blur effect"""
        # Create blur animation
        blur_anim = QPropertyAnimation(self.fade_effect, b"blurRadius")
        blur_anim.setDuration(150)
        blur_anim.setStartValue(0)
        blur_anim.setEndValue(5)
        
        # Create unblur animation
        unblur_anim = QPropertyAnimation(self.fade_effect, b"blurRadius")
        unblur_anim.setDuration(150)
        unblur_anim.setStartValue(5)
        unblur_anim.setEndValue(0)
        
        # Create sequential animation group
        anim_group = QSequentialAnimationGroup()
        anim_group.addAnimation(blur_anim)
        anim_group.addAnimation(unblur_anim)
        anim_group.start()

    def setup_results_view(self):
        """Set up the results view that shows after scanning with enhanced visuals"""
        results_layout = QVBoxLayout(self.results_view)
        results_layout.setContentsMargins(0, 30, 0, 0)
        results_layout.setSpacing(30)

        # Results header with improved styling
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignLeft)

        # Back button with animation
        self.back_button = QPushButton("← Back to Scan")
        self.back_button.setFont(QFont(self.font_family, 12))
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_primary};
                border: none;
                padding: 8px 15px;
                text-align: left;
            }}
            QPushButton:hover {{
                color: {self.uv_hover};
                text-decoration: underline;
                padding-left: 5px; /* Shift slightly on hover */
            }}
        """)
        self.back_button.clicked.connect(self.show_scan_view)
        header_layout.addWidget(self.back_button)
        header_layout.addStretch()
        results_layout.addLayout(header_layout)

        # Main content area with splitter and improved styling
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {self.uv_primary};
                height: 1px;
            }}
            QSplitter::handle:hover {{
                background: {self.uv_hover};
            }}
        """)

        # Vehicle info section (top) with card-based design
        vehicle_info_container = QWidget()
        vehicle_info_container.setStyleSheet("background: transparent;")
        vehicle_info_layout = QVBoxLayout(vehicle_info_container)
        vehicle_info_layout.setContentsMargins(0, 0, 0, 0)
        vehicle_info_layout.setSpacing(25)

        # Vehicle info title with icon and enhanced styling
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignLeft)
        info_icon = QLabel()
        info_pixmap = QPixmap("assets/info_icon.png")
        if not info_pixmap.isNull():
            info_icon.setPixmap(info_pixmap.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(info_icon)
        title_layout.addSpacing(12)
        title_label = QLabel("Vehicle Information")
        title_label.setFont(QFont(self.font_family, 20, QFont.Bold))
        title_label.setStyleSheet(f"""
            color: {self.uv_light};
            padding-bottom: 5px;
            border-bottom: 2px solid {self.uv_primary};
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        vehicle_info_layout.addLayout(title_layout)

        # Vehicle info cards (using grid layout for better organization)
        self.info_cards_container = QWidget()
        self.info_cards_layout = QGridLayout(self.info_cards_container)
        self.info_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.info_cards_layout.setSpacing(25)
        self.info_cards_layout.setColumnStretch(0, 1)
        self.info_cards_layout.setColumnStretch(1, 1)

        # Enhanced scroll area with smooth scrolling
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        scroll_area.setWidget(self.info_cards_container)
        vehicle_info_layout.addWidget(scroll_area)
        splitter.addWidget(vehicle_info_container)

        # Action buttons section (bottom) with improved layout and animations
        action_buttons_container = QWidget()
        action_buttons_container.setStyleSheet(f"""
            background: transparent;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        """)
        action_buttons_layout = QVBoxLayout(action_buttons_container)
        action_buttons_layout.setContentsMargins(0, 25, 0, 0)
        action_buttons_layout.setSpacing(20)

        # Button row with improved spacing and alignment
        button_row = QHBoxLayout()
        button_row.setSpacing(25)
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setAlignment(Qt.AlignCenter)

        # Continue with Analysis button with enhanced styling
        self.continue_button = QPushButton("Continue with Analysis")
        self.continue_button.setFont(QFont(self.font_family, 12, QFont.Bold))
        self.continue_button.setCursor(Qt.PointingHandCursor)
        self.continue_button.setFixedSize(240, 50)
        self.continue_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_primary}, stop:1 #0088cc);
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_hover}, stop:1 #00a0e6);
                box-shadow: 0 0 15px rgba(0, 195, 255, 0.5);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_pressed}, stop:1 #007ab8);
            }}
        """)

        # Add glow effect to primary button
        continue_glow = QGraphicsDropShadowEffect()
        continue_glow.setBlurRadius(15)
        continue_glow.setColor(QColor(0, 195, 255, 70))
        continue_glow.setOffset(0, 0)
        self.continue_button.setGraphicsEffect(continue_glow)

        self.continue_button.setIcon(QIcon("assets/analysis_icon.png"))
        self.continue_button.setIconSize(QSize(22, 22))
        self.continue_button.clicked.connect(self.continue_with_analysis)
        button_row.addWidget(self.continue_button)

        # Rescan button with improved styling
        self.rescan_button = QPushButton("Rescan")
        self.rescan_button.setFont(QFont(self.font_family, 12, QFont.Bold))
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
                background-color: rgba(0, 195, 255, 0.25);
            }}
        """)
        self.rescan_button.setIcon(QIcon("assets/rescan_icon.png"))
        self.rescan_button.setIconSize(QSize(20, 20))
        self.rescan_button.clicked.connect(self.reset_scan_ui)
        button_row.addWidget(self.rescan_button)

        # Save button with gradient styling
        self.save_button = QPushButton("Save Information")
        self.save_button.setFont(QFont(self.font_family, 12, QFont.Bold))
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.setFixedSize(220, 50)
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_secondary_dark}, stop:1 {self.uv_secondary});
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_secondary}, stop:1 #00ff85);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 #009f52, stop:1 {self.uv_secondary_dark});
            }}
        """)
        self.save_button.setIcon(QIcon("assets/save_icon.png"))
        self.save_button.setIconSize(QSize(20, 20))
        self.save_button.clicked.connect(self.save_vehicle_info)
        button_row.addWidget(self.save_button)

        # Clear button with improved styling
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFont(QFont(self.font_family, 12, QFont.Bold))
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setFixedSize(220, 50)
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 2px solid {self.uv_light_gray};
                border-radius: 25px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid {self.uv_light};
                color: {self.uv_light};
            }}
            QPushButton:pressed {{
                border: 2px solid {self.uv_light_gray};
                background-color: rgba(255, 255, 255, 0.05);
            }}
        """)
        self.clear_button.setIcon(QIcon("assets/clear_icon.png"))
        self.clear_button.setIconSize(QSize(20, 20))
        self.clear_button.clicked.connect(self.clear_vehicle_info)
        button_row.addWidget(self.clear_button)

        action_buttons_layout.addLayout(button_row)
        
        # Add a subtle hint text below buttons
        hint_label = QLabel("Tip: You can save the vehicle information for future reference")
        hint_label.setFont(QFont(self.font_family, 9))
        hint_label.setStyleSheet(f"color: {self.uv_footer}; margin-top: 5px;")
        hint_label.setAlignment(Qt.AlignCenter)
        action_buttons_layout.addWidget(hint_label)
        
        splitter.addWidget(action_buttons_container)

        # Set initial sizes (70% for info, 30% for buttons)
        splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])
        results_layout.addWidget(splitter)

    def show_scan_view(self):
        """Switch back to the scan view with smooth transition"""
        # Create fade out animation
        fade_out = QPropertyAnimation(self.content_stack, b"windowOpacity")
        fade_out.setDuration(150)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.8)
        fade_out.setEasingCurve(QEasingCurve.InQuad)
        
        # Create fade in animation
        fade_in = QPropertyAnimation(self.content_stack, b"windowOpacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.8)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.OutQuad)
        
        # Create sequential animation group
        anim_group = QSequentialAnimationGroup()
        anim_group.addAnimation(fade_out)
        
        # Switch view in between animations
        anim_group.finished.connect(lambda: self._complete_view_transition(self.scan_view))
        
        # Add fade in animation
        anim_group.addAnimation(fade_in)
        
        # Start animation
        anim_group.start()

    def _complete_view_transition(self, target_view):
        """Complete the view transition"""
        self.content_stack.setCurrentWidget(target_view)
        if target_view == self.scan_view:
            self.reset_scan_ui()

    def show_results_view(self):
        """Switch to the results view with smooth transition"""
        # Create fade out animation
        fade_out = QPropertyAnimation(self.content_stack, b"windowOpacity")
        fade_out.setDuration(150)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.8)
        fade_out.setEasingCurve(QEasingCurve.InQuad)
        
        # Create fade in animation
        fade_in = QPropertyAnimation(self.content_stack, b"windowOpacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.8)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.OutQuad)
        
        # Create sequential animation group
        anim_group = QSequentialAnimationGroup()
        anim_group.addAnimation(fade_out)
        
        # Switch view in between animations
        anim_group.finished.connect(lambda: self.content_stack.setCurrentWidget(self.results_view))
        
        # Add fade in animation
        anim_group.addAnimation(fade_in)
        
        # Start animation
        anim_group.start()

    def setup_scan_tab(self, tab):
        """Set up the barcode scanning tab with modern design and animations"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # Title with modern styling and icon badge
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

        # Title container with enhanced typography
        title_container = QVBoxLayout()
        title_container.setSpacing(8)
        title = QLabel("Vehicle Identification")
        title.setFont(QFont(self.font_family, 24, QFont.Bold))
        title.setStyleSheet(f"""
            color: {self.uv_light};
            letter-spacing: 0.5px;
        """)
        title_container.addWidget(title)
        subtitle = QLabel("Scan the vehicle barcode to begin")
        subtitle.setFont(QFont(self.font_family, 12))
        subtitle.setStyleSheet("color: #AAAAAA;")
        title_container.addWidget(subtitle)
        title_layout.addLayout(title_container)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Scan card with enhanced design and animations
        scan_card = QFrame()
        scan_card.setObjectName("scanCard")

        # Add enhanced shadow effect with blue glow
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(30)
        card_shadow.setColor(QColor(0, 100, 150, 60))
        card_shadow.setOffset(0, 5)
        scan_card.setGraphicsEffect(card_shadow)
        scan_card.setStyleSheet(f"""
            QFrame#scanCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 {self.uv_card_bg}, stop:1 {self.uv_darker});
                border: 1px solid {self.uv_card_border};
                border-radius: 16px;
            }}
        """)

        scan_layout = QVBoxLayout(scan_card)
        scan_layout.setContentsMargins(40, 50, 40, 50)
        scan_layout.setSpacing(35)
        scan_layout.setAlignment(Qt.AlignCenter)

        # Scan image container with animated border and glow effect
        self.scan_image_container = QFrame()
        self.scan_image_container.setFixedSize(240, 240)
        self.scan_image_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 120px;
                border: 2px solid {self.uv_primary};
            }}
        """)

        # Add pulsing glow effect to scan container
        scan_glow = QGraphicsDropShadowEffect()
        scan_glow.setBlurRadius(20)
        scan_glow.setColor(QColor(0, 195, 255, 100))
        scan_glow.setOffset(0, 0)
        self.scan_image_container.setGraphicsEffect(scan_glow)

        # Setup glow animation
        self.glow_animation = QPropertyAnimation(scan_glow, b"color")
        self.glow_animation.setDuration(2000)
        self.glow_animation.setStartValue(QColor(0, 195, 255, 30))
        self.glow_animation.setEndValue(QColor(0, 195, 255, 150))
        self.glow_animation.setLoopCount(-1)
        self.glow_animation.setEasingCurve(QEasingCurve.InOutSine)

        scan_image_layout = QVBoxLayout(self.scan_image_container)
        scan_image_layout.setContentsMargins(30, 30, 30, 30)
        scan_image_layout.setAlignment(Qt.AlignCenter)

        # Scan image or animation with enhanced visuals
        self.scan_image = QLabel()
        scan_pixmap = QPixmap("assets/barcode_scan.png")
        if scan_pixmap.isNull():
            # Create a stylized placeholder if image is missing
            self.scan_image.setText("[ SCAN ]")
            self.scan_image.setStyleSheet(f"""
                color: {self.uv_primary};
                font-size: 18px;
                font-weight: bold;
                padding: 40px;
                border: none;
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, 
                                          stop:0 {self.uv_primary}, stop:0.2 transparent);
            """)
            self.scan_image.setAlignment(Qt.AlignCenter)
        else:
            # Apply enhanced styling to the image
            self.scan_image.setPixmap(
                scan_pixmap.scaled(
                    180, 180, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            )
            self.scan_image.setStyleSheet("background: transparent; border: none;")
            self.scan_image.setAlignment(Qt.AlignCenter)
        scan_image_layout.addWidget(self.scan_image)
        scan_layout.addWidget(self.scan_image_container, alignment=Qt.AlignCenter)

        # Scan instructions with animation and improved typography
        self.scan_instructions = QLabel("Position the barcode scanner over the vehicle's barcode")
        self.scan_instructions.setFont(QFont(self.font_family, 13))
        self.scan_instructions.setStyleSheet(f"""
            color: {self.uv_light};
            margin-top: 15px;
            letter-spacing: 0.5px;
        """)
        self.scan_instructions.setAlignment(Qt.AlignCenter)
        scan_layout.addWidget(self.scan_instructions)

        # Progress bar for scanning with animated styling
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(0)
        self.scan_progress.setTextVisible(False)
        self.scan_progress.setFixedHeight(6)
        self.scan_progress.setFixedWidth(350)
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

        # Status message with improved styling
        self.status_message = QLabel("Ready to scan")
        self.status_message.setFont(QFont(self.font_family, 12))
        self.status_message.setAlignment(Qt.AlignCenter)
        self.status_message.setStyleSheet(f"""
            color: {self.uv_primary};
            font-weight: 500;
            padding: 5px 15px;
            background-color: rgba(0, 195, 255, 0.1);
            border-radius: 15px;
        """)
        scan_layout.addWidget(self.status_message)

        # Button layout with improved spacing
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.setSpacing(25)

        # Scan button with enhanced styling and animations
        self.scan_button = QPushButton("Start Scanning")
        self.scan_button.setFont(QFont(self.font_family, 13, QFont.Bold))
        self.scan_button.setFixedSize(240, 54)
        self.scan_button.setCursor(Qt.PointingHandCursor)
        self.scan_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_primary}, stop:1 #0088cc);
                color: {self.uv_dark};
                border: none;
                border-radius: 27px;
                padding: 12px 30px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_hover}, stop:1 #00a0e6);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_pressed}, stop:1 #007ab8);
            }}
        """)

        # Add scan button glow effect
        button_glow = QGraphicsDropShadowEffect()
        button_glow.setBlurRadius(20)
        button_glow.setColor(QColor(0, 195, 255, 100))
        button_glow.setOffset(0, 2)
        self.scan_button.setGraphicsEffect(button_glow)

        # Add scan icon if available
        scan_icon = QIcon("assets/scan_icon.png")
        if not scan_icon.isNull():
            self.scan_button.setIcon(scan_icon)
            self.scan_button.setIconSize(QSize(22, 22))
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)

        # Cancel button with improved styling
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFont(QFont(self.font_family, 13, QFont.Bold))
        self.cancel_button.setFixedSize(160, 54)
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 82, 82, 0.1);
                color: {self.uv_light};
                border: 2px solid {self.uv_error};
                border-radius: 27px;
                padding: 12px 30px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 82, 82, 0.2);
                border: 2px solid #ff6e6e;
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 82, 82, 0.3);
                border: 2px solid #ff3939;
            }}
        """)
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.hide()
        button_layout.addWidget(self.cancel_button)

        scan_layout.addLayout(button_layout)
        layout.addWidget(scan_card)
        
        # Start the glow animation
        self.glow_animation.start()

    def setup_manual_tab(self, tab):
        """Set up the manual entry tab with modern design and enhanced UX"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # Title with modern styling and icon badge
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)

        # Title badge with gradient
        title_badge = QLabel()
        title_badge.setFixedSize(8, 50)
        title_badge.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 {self.uv_accent}, stop:1 {self.uv_primary});
            border-radius: 4px;
        """)
        title_layout.addWidget(title_badge)
        title_layout.addSpacing(15)

        # Title container with enhanced typography
        title_container = QVBoxLayout()
        title_container.setSpacing(8)
        title = QLabel("Manual Entry")
        title.setFont(QFont(self.font_family, 24, QFont.Bold))
        title.setStyleSheet(f"""
            color: {self.uv_light};
            letter-spacing: 0.5px;
        """)
        title_container.addWidget(title)
        subtitle = QLabel("Enter vehicle information manually")
        subtitle.setFont(QFont(self.font_family, 12))
        subtitle.setStyleSheet("color: #AAAAAA;")
        title_container.addWidget(subtitle)
        title_layout.addLayout(title_container)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Manual entry card with enhanced design
        manual_card = QFrame()
        manual_card.setObjectName("manualCard")

        # Add shadow effect with subtle accent color
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(30)
        card_shadow.setColor(QColor(255, 112, 67, 40))  # Accent color shadow
        card_shadow.setOffset(0, 5)
        manual_card.setGraphicsEffect(card_shadow)
        manual_card.setStyleSheet(f"""
            QFrame#manualCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 {self.uv_card_bg}, stop:1 {self.uv_darker});
                border: 1px solid {self.uv_card_border};
                border-radius: 16px;
            }}
        """)

        manual_layout = QVBoxLayout(manual_card)
        manual_layout.setContentsMargins(40, 50, 40, 50)
        manual_layout.setSpacing(30)

        # Form layout for input fields with improved spacing and styling
        form_layout = QFormLayout()
        form_layout.setSpacing(25)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignCenter)
        form_layout.setContentsMargins(10, 0, 10, 0)

        # VIN input with enhanced styling and animation
        vin_label = QLabel("VIN:")
        vin_label.setFont(QFont(self.font_family, 13, QFont.Bold))
        vin_label.setStyleSheet(f"color: {self.uv_light};")
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Enter Vehicle Identification Number")
        self.vin_input.setMaxLength(17)
        self.vin_input.setMinimumHeight(50)
        self.vin_input.setFont(QFont(self.font_family, 12))
        self.vin_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
            QLineEdit:focus {{
                border: 2px solid {self.uv_primary};
                background-color: rgba(45, 45, 45, 0.7);
            }}
            QLineEdit:hover {{
                border: 1px solid #666666;
            }}
        """)
        form_layout.addRow(vin_label, self.vin_input)

        # IMEI input with enhanced styling
        imei_label = QLabel("IMEI:")
        imei_label.setFont(QFont(self.font_family, 13, QFont.Bold))
        imei_label.setStyleSheet(f"color: {self.uv_light};")
        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText("Enter IMEI Number")
        self.imei_input.setMaxLength(15)
        self.imei_input.setMinimumHeight(50)
        self.imei_input.setFont(QFont(self.font_family, 12))
        self.imei_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
            QLineEdit:focus {{
                border: 2px solid {self.uv_primary};
                background-color: rgba(45, 45, 45, 0.7);
            }}
            QLineEdit:hover {{
                border: 1px solid #666666;
            }}
        """)
        form_layout.addRow(imei_label, self.imei_input)

        # UUID input with enhanced styling
        uuid_label = QLabel("UUID:")
        uuid_label.setFont(QFont(self.font_family, 13, QFont.Bold))
        uuid_label.setStyleSheet(f"color: {self.uv_light};")
        self.uuid_input = QLineEdit()
        self.uuid_input.setPlaceholderText("Enter UUID")
        self.uuid_input.setMaxLength(36)
        self.uuid_input.setMinimumHeight(50)
        self.uuid_input.setFont(QFont(self.font_family, 12))
        self.uuid_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
            QLineEdit:focus {{
                border: 2px solid {self.uv_primary};
                background-color: rgba(45, 45, 45, 0.7);
            }}
            QLineEdit:hover {{
                border: 1px solid #666666;
            }}
        """)
        form_layout.addRow(uuid_label, self.uuid_input)

        manual_layout.addLayout(form_layout)

        # Info text with improved styling and icon
        info_container = QHBoxLayout()
        info_icon = QLabel()
        info_icon_pixmap = QPixmap("assets/info_small_icon.png")
        if not info_icon_pixmap.isNull():
            info_icon.setPixmap(info_icon_pixmap.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            info_icon.setText("ℹ")
            info_icon.setFont(QFont(self.font_family, 12))
            info_icon.setStyleSheet(f"color: {self.uv_primary};")
        info_container.addWidget(info_icon)
        info_container.addSpacing(10)
        
        info_label = QLabel(
            "Enter the vehicle information fields above. All fields are optional but at least one is required."
        )
        info_label.setFont(QFont(self.font_family, 11))
        info_label.setStyleSheet("color: #AAAAAA;")
        info_label.setWordWrap(True)
        info_container.addWidget(info_label)
        manual_layout.addLayout(info_container)
        
        # Add spacing
        manual_layout.addSpacing(10)

        # Submit button with enhanced styling and animation
        self.submit_button = QPushButton("Submit Information")
        self.submit_button.setFont(QFont(self.font_family, 13, QFont.Bold))
        self.submit_button.setFixedSize(240, 54)
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_accent}, stop:1 {self.uv_primary});
                color: {self.uv_dark};
                border: none;
                border-radius: 27px;
                padding: 12px 30px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 #ff8a60, stop:1 {self.uv_hover});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 #e5633c, stop:1 {self.uv_pressed});
            }}
        """)
        
        # Add glow effect to submit button
        submit_glow = QGraphicsDropShadowEffect()
        submit_glow.setBlurRadius(20)
        submit_glow.setColor(QColor(255, 112, 67, 100))
        submit_glow.setOffset(0, 2)
        self.submit_button.setGraphicsEffect(submit_glow)
        
        self.submit_button.setIcon(QIcon("assets/submit_icon.png"))
        self.submit_button.setIconSize(QSize(22, 22))
        self.submit_button.clicked.connect(self.submit_manual_info)
        manual_layout.addWidget(self.submit_button, alignment=Qt.AlignCenter)

        layout.addWidget(manual_card)

    def setup_footer(self, parent_layout):
        """Setup the footer with version info and enhanced styling"""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 25, 0, 0)
        
        # Add subtle separator above footer
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet(f"""
            background-color: rgba(255, 255, 255, 0.05);
            min-height: 1px;
            max-height: 1px;
            margin: 0px;
        """)
        parent_layout.addWidget(separator)
        parent_layout.addSpacing(15)
        
        # Version info with icon
        version_container = QHBoxLayout()
        version_icon = QLabel()
        version_icon_pixmap = QPixmap("assets/version_icon.png")
        if not version_icon_pixmap.isNull():
            version_icon.setPixmap(version_icon_pixmap.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        version_container.addWidget(version_icon)
        version_container.addSpacing(8)
        
        version_label = QLabel("Ultraviolette Dashboard v1.2.0")
        version_label.setFont(QFont(self.font_family, 9))
        version_label.setStyleSheet(f"color: {self.uv_footer};")
        version_container.addWidget(version_label)
        footer_layout.addLayout(version_container)
        
        # Center spacer
        footer_layout.addStretch()
        
        # Copyright with subtle styling
        copyright_container = QHBoxLayout()
        copyright_icon = QLabel()
        copyright_icon_pixmap = QPixmap("assets/copyright_icon.png")
        if not copyright_icon_pixmap.isNull():
            copyright_icon.setPixmap(copyright_icon_pixmap.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            copyright_icon.setText("©")
            copyright_icon.setFont(QFont(self.font_family, 9))
            copyright_icon.setStyleSheet(f"color: {self.uv_footer};")
        copyright_container.addWidget(copyright_icon)
        copyright_container.addSpacing(8)
        
        copyright_label = QLabel("2025 Ultraviolette Automotive")
        copyright_label.setFont(QFont(self.font_family, 9))
        copyright_label.setStyleSheet(f"color: {self.uv_footer};")
        copyright_container.addWidget(copyright_label)
        footer_layout.addLayout(copyright_container)
        
        parent_layout.addLayout(footer_layout)

    def update_pulse(self):
        """Update the pulse animation for the scan button with enhanced visual effects"""
        self.pulse_value += 0.05 * self.pulse_direction
        if self.pulse_value >= 1.0:
            self.pulse_value = 1.0
            self.pulse_direction = -1
        elif self.pulse_value <= 0.0:
            self.pulse_value = 0.0
            self.pulse_direction = 1
            
        # Calculate opacity based on pulse value
        opacity = 0.5 + 0.5 * self.pulse_value
        
        # Update button glow effect
        if hasattr(self, 'scan_button') and self.scan_button.graphicsEffect():
            glow = self.scan_button.graphicsEffect()
            glow.setColor(QColor(0, 195, 255, int(70 + 80 * self.pulse_value)))
            
        # Update scan image container border
        if self.is_scanning:
            border_width = 2 + int(2 * self.pulse_value)
            self.scan_image_container.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.uv_gray};
                    border-radius: 120px;
                    border: {border_width}px solid {self.uv_primary};
                }}
            """)

    def start_scan(self):
        """Start the barcode scanning process with enhanced UI feedback and animations"""
        # Update UI for scanning state
        self.current_scan_state = "scanning"
        self.is_scanning = True
        
        # UI changes with smooth transitions
        self.scan_button.hide()
        self.cancel_button.show()
        self.scan_progress.show()
        self.scan_progress.setValue(0)
        
        # Update status with animation
        self.status_message.setText("Initializing scanner...")
        self.status_message.setStyleSheet(f"""
            color: {self.uv_primary};
            font-weight: 500;
            padding: 5px 15px;
            background-color: rgba(0, 195, 255, 0.15);
            border-radius: 15px;
        """)
        
        # Animate the scan container
        container_anim = QPropertyAnimation(self.scan_image_container, b"geometry")
        container_anim.setDuration(400)
        current_geo = self.scan_image_container.geometry()
        target_geo = QRect(current_geo.x() - 5, current_geo.y() - 5, 
                           current_geo.width() + 10, current_geo.height() + 10)
        container_anim.setStartValue(current_geo)
        container_anim.setEndValue(target_geo)
        container_anim.setEasingCurve(QEasingCurve.OutBack)
        container_anim.start()
        
        # Start the pulse animation
        self.pulse_timer.start(50)
        
        # Change scan instructions with animation
        self.scan_instructions.setText("Please hold the scanner steady...")
        self.scan_instructions.setStyleSheet(f"""
            color: {self.uv_light};
            margin-top: 15px;
            letter-spacing: 0.5px;
            font-weight: bold;
        """)
        
        # Initialize and start the scan thread
        self.scan_thread = BarcodeScanThread()
        self.scan_thread.scan_complete.connect(self.handle_scan_complete)
        self.scan_thread.scan_error.connect(self.handle_scan_error)
        self.scan_thread.scan_progress.connect(self.update_scan_progress)
        self.scan_thread.scan_status.connect(self.update_scan_status)
        self.scan_thread.start()

    def update_scan_status(self, status):
        """Update the status message during scanning with enhanced visual feedback"""
        self.status_message.setText(status)
        
        # Change color and style based on status
        if "error" in status.lower():
            self.status_message.setStyleSheet(f"""
                color: {self.uv_error};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(255, 82, 82, 0.15);
                border-radius: 15px;
            """)
        elif "ready" in status.lower():
            self.status_message.setStyleSheet(f"""
                color: {self.uv_primary};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(0, 195, 255, 0.15);
                border-radius: 15px;
            """)
        elif "success" in status.lower() or "complete" in status.lower():
            self.status_message.setStyleSheet(f"""
                color: {self.uv_secondary};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(0, 230, 118, 0.15);
                border-radius: 15px;
            """)
        else:
            self.status_message.setStyleSheet(f"""
                color: {self.uv_light};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
            """)

    def cancel_scan(self):
        """Cancel the current scanning process with smooth UI transition"""
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.stop()
            self.scan_thread.terminate()
            self.scan_thread = None
            
        # Animate the scan container back to normal
        container_anim = QPropertyAnimation(self.scan_image_container, b"geometry")
        container_anim.setDuration(400)
        current_geo = self.scan_image_container.geometry()
        target_geo = QRect(current_geo.x() + 5, current_geo.y() + 5, 
                           current_geo.width() - 10, current_geo.height() - 10)
        container_anim.setStartValue(current_geo)
        container_anim.setEndValue(target_geo)
        container_anim.setEasingCurve(QEasingCurve.OutBack)
        container_anim.start()
            
        self.reset_scan_ui()
        self.status_message.setText("Scan cancelled")
        self.status_message.setStyleSheet(f"""
            color: {self.uv_warning};
            font-weight: 500;
            padding: 5px 15px;
            background-color: rgba(255, 171, 64, 0.15);
            border-radius: 15px;
        """)
        
        # Fade out the status message after delay
        QTimer.singleShot(2000, self.fade_status_message)
        
        # Reset scan instructions
        self.scan_instructions.setText("Position the barcode scanner over the vehicle's barcode")
        self.scan_instructions.setStyleSheet(f"""
            color: {self.uv_light};
            margin-top: 15px;
            letter-spacing: 0.5px;
        """)

    def fade_status_message(self):
        """Fade out the status message with smooth animation"""
        # Only fade if not in scanning state
        if not self.is_scanning:
            self.status_fade_animation.start()
            
            # Reset status message after animation completes
            self.status_fade_animation.finished.connect(lambda: self.status_message.setText("Ready to scan"))
            self.status_fade_animation.finished.connect(lambda: self.status_message.setWindowOpacity(1.0))
            self.status_fade_animation.finished.connect(lambda: self.status_message.setStyleSheet(f"""
                color: {self.uv_primary};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(0, 195, 255, 0.1);
                border-radius: 15px;
            """))

    def reset_scan_ui(self):
        """Reset UI elements after scanning with smooth animations"""
        self.current_scan_state = "ready"
        self.is_scanning = False
        
        # UI reset with animations
        self.scan_button.show()
        self.cancel_button.hide()
        self.scan_progress.hide()
        self.pulse_timer.stop()
        
        # Reset scan image container style
        self.scan_image_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 120px;
                border: 2px solid {self.uv_primary};
            }}
        """)
        
        # Reset button glow
        if self.scan_button.graphicsEffect():
            glow = self.scan_button.graphicsEffect()
            glow.setColor(QColor(0, 195, 255, 100))
        
        # Reset status message after delay if not already set
        if self.status_message.text() in ("", "Ready to scan"):
            self.status_message.setText("Ready to scan")
            self.status_message.setStyleSheet(f"""
                color: {self.uv_primary};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(0, 195, 255, 0.1);
                border-radius: 15px;
            """)

    def update_scan_progress(self, value):
        """Update the progress bar during scanning with dynamic color changes"""
        self.scan_progress.setValue(value)
        
        # Change color based on progress with smooth gradient transitions
        if value < 30:
            # Red to Orange gradient
            self.scan_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {self.uv_gray};
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                  stop:0 {self.uv_error}, stop:1 {self.uv_warning});
                    border-radius: 3px;
                }}
            """)
        elif value < 70:
            # Orange to Blue gradient
            self.scan_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {self.uv_gray};
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                  stop:0 {self.uv_warning}, stop:1 {self.uv_primary});
                    border-radius: 3px;
                }}
            """)
        else:
            # Blue to Green gradient for completion
            self.scan_progress.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {self.uv_gray};
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                  stop:0 {self.uv_primary}, stop:1 {self.uv_secondary});
                    border-radius: 3px;
                }}
            """)
            
        # Update scan instructions based on progress
        if value > 90:
            self.scan_instructions.setText("Almost done! Processing data...")
            self.scan_instructions.setStyleSheet(f"""
                color: {self.uv_light};
                margin-top: 15px;
                letter-spacing: 0.5px;
                font-weight: bold;
            """)

    def handle_scan_complete(self, barcode):
        """Handle successful barcode scan with enhanced UI feedback and animations"""
        global SCANNED_BARCODE
        
        # Play success animation
        self.play_success_animation()
        
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
            
        # Update status message
        self.status_message.setText("✓ Scan completed successfully!")
        self.status_message.setStyleSheet(f"""
            color: {self.uv_secondary};
            font-weight: 500;
            padding: 5px 15px;
            background-color: rgba(0, 230, 118, 0.15);
            border-radius: 15px;
        """)
            
        # Display the vehicle information in results view
        self.display_vehicle_info()
        
        # Switch to results view with animation
        QTimer.singleShot(800, self.show_results_view)
        
        # Emit the scanned data
        self.scan_successful.emit(self.vehicle_info)

    def play_success_animation(self):
        """Play a success animation after successful scan"""
        # Create a sequence of animations for success feedback
        
        # 1. Flash the scan container with success color
        flash_anim = QPropertyAnimation(self.scan_image_container, b"styleSheet")
        flash_anim.setDuration(300)
        flash_anim.setStartValue(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 120px;
                border: 2px solid {self.uv_primary};
            }}
        """)
        flash_anim.setEndValue(f"""
            QFrame {{
                background-color: rgba(0, 230, 118, 0.3);
                border-radius: 120px;
                border: 3px solid {self.uv_secondary};
            }}
        """)
        
        # 2. Scale up animation
        scale_up = QPropertyAnimation(self.scan_image_container, b"geometry")
        scale_up.setDuration(200)
        current_geo = self.scan_image_container.geometry()
        scale_up.setStartValue(current_geo)
        scale_up.setEndValue(QRect(
            current_geo.x() - 10, 
            current_geo.y() - 10, 
            current_geo.width() + 20, 
            current_geo.height() + 20
        ))
        scale_up.setEasingCurve(QEasingCurve.OutQuad)
        
        # 3. Scale down animation
        scale_down = QPropertyAnimation(self.scan_image_container, b"geometry")
        scale_down.setDuration(300)
        scale_down.setStartValue(QRect(
            current_geo.x() - 10, 
            current_geo.y() - 10, 
            current_geo.width() + 20, 
            current_geo.height() + 20
        ))
        scale_down.setEndValue(current_geo)
        scale_down.setEasingCurve(QEasingCurve.OutBounce)
        
        # Create animation group and run sequentially
        anim_group = QSequentialAnimationGroup()
        anim_group.addAnimation(flash_anim)
        anim_group.addAnimation(scale_up)
        anim_group.addAnimation(scale_down)
        anim_group.start()
        
        # Reset the scan UI after animation
        anim_group.finished.connect(self.reset_scan_ui)

    def display_vehicle_info(self):
        """Display the vehicle information in a modern card layout with animations"""
        # Clear previous info cards
        for i in reversed(range(self.info_cards_layout.count())):
            widget = self.info_cards_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        # Add vehicle info cards in a grid layout with staggered animations
        row = 0
        col = 0
        delay = 0
        
        if self.vehicle_info['vin']:
            self.add_info_card(row, col, "VIN", self.vehicle_info['vin'], "assets/vin_icon.png", delay)
            col += 1
            if col > 1:
                col = 0
                row += 1
            delay += 100
            
        if self.vehicle_info['imei']:
            self.add_info_card(row, col, "IMEI", self.vehicle_info['imei'], "assets/imei_icon.png", delay)
            col += 1
            if col > 1:
                col = 0
                row += 1
            delay += 100
            
        if self.vehicle_info['uuid']:
            self.add_info_card(row, col, "UUID", self.vehicle_info['uuid'], "assets/uuid_icon.png", delay)

    def add_info_card(self, row, col, title, value, icon_path=None, delay=0):
        """Add an information card to the grid layout with entrance animation"""
        card = QFrame()
        card.setObjectName("infoCard")
        
        # Set initial opacity to 0 for animation
        card.setWindowOpacity(0)
        
        # Apply glass morphism effect
        card.setStyleSheet(f"""
            QFrame#infoCard {{
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        
        # Add shadow effect
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setColor(QColor(0, 0, 0, 80))
        card_shadow.setOffset(0, 4)
        card.setGraphicsEffect(card_shadow)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(20)
        
        # Add icon if available
        if icon_path and os.path.exists(icon_path):
            icon_label = QLabel()
            icon_label.setPixmap(QPixmap(icon_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            card_layout.addWidget(icon_label)
        else:
            # Create a colored circle with first letter if no icon
            icon_placeholder = QLabel(title[0])
            icon_placeholder.setAlignment(Qt.AlignCenter)
            icon_placeholder.setFixedSize(28, 28)
            icon_placeholder.setFont(QFont(self.font_family, 12, QFont.Bold))
            icon_placeholder.setStyleSheet(f"""
                background-color: {self.uv_primary};
                color: {self.uv_dark};
                border-radius: 14px;
            """)
            card_layout.addWidget(icon_placeholder)
            
        # Add title and value with enhanced typography
        text_layout = QVBoxLayout()
        text_layout.setSpacing(10)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(self.font_family, 12, QFont.Bold))
        title_label.setStyleSheet(f"""
            color: {self.uv_primary};
            letter-spacing: 0.5px;
        """)
        text_layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setFont(QFont(self.font_family, 14))
        value_label.setStyleSheet(f"""
            color: {self.uv_light};
            letter-spacing: 0.3px;
        """)
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value_label.setCursor(Qt.IBeamCursor)
        
        # Add tooltip for long values
        metrics = QFontMetrics(value_label.font())
        if metrics.horizontalAdvance(value) > 300:
            value_label.setToolTip(value)
            
            # Elide text if too long
            elidedText = metrics.elidedText(value, Qt.ElideMiddle, 300)
            value_label.setText(elidedText)
            
        text_layout.addWidget(value_label)
        card_layout.addLayout(text_layout)
        card_layout.addStretch()
        
        # Add copy button with improved styling
        copy_button = QPushButton()
        copy_button.setIcon(QIcon("assets/copy_icon.png"))
        copy_button.setIconSize(QSize(16, 16))
        copy_button.setFixedSize(36, 36)
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.setToolTip(f"Copy {title}")
        copy_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_primary};
                border-radius: 18px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.uv_hover};
                box-shadow: 0 0 8px {self.uv_primary};
            }}
            QPushButton:pressed {{
                background-color: {self.uv_pressed};
            }}
        """)
        copy_button.clicked.connect(lambda _, v=value: self.copy_to_clipboard(v))
        card_layout.addWidget(copy_button)
        
        # Add the card to the layout
        self.info_cards_layout.addWidget(card, row, col)
        
        # Create entrance animation with delay
        QTimer.singleShot(delay, lambda: self.animate_card_entrance(card))
        
        return card

    def animate_card_entrance(self, card):
        """Animate the entrance of an info card"""
        # Set initial position slightly below and with 0 opacity
        card.setWindowOpacity(0.0)
        
        # Create opacity animation
        opacity_anim = QPropertyAnimation(card, b"windowOpacity")
        opacity_anim.setDuration(400)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # Create position animation
        pos_anim = QPropertyAnimation(card, b"pos")
        pos_anim.setDuration(500)
        current_pos = card.pos()
        pos_anim.setStartValue(QPoint(current_pos.x(), current_pos.y() + 20))
        pos_anim.setEndValue(current_pos)
        pos_anim.setEasingCurve(QEasingCurve.OutBack)
        
        # Create animation group
        anim_group = QParallelAnimationGroup()
        anim_group.addAnimation(opacity_anim)
        anim_group.addAnimation(pos_anim)
        anim_group.start()

    def copy_to_clipboard(self, text):
        """Copy text to clipboard and show feedback with enhanced animation"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Show temporary feedback with animation
        feedback = QLabel("Copied!")
        feedback.setFont(QFont(self.font_family, 10, QFont.Bold))
        feedback.setAlignment(Qt.AlignCenter)
        feedback.setStyleSheet(f"""
            background-color: {self.uv_secondary};
            color: {self.uv_dark};
            padding: 8px 16px;
            border-radius: 16px;
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 230, 118, 100))
        shadow.setOffset(0, 2)
        feedback.setGraphicsEffect(shadow)
        
        feedback.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        
        # Position near cursor
        cursor_pos = QCursor.pos()
        feedback.move(cursor_pos.x() + 15, cursor_pos.y() + 15)
        feedback.show()
        
        # Create fade in animation
        fade_in = QPropertyAnimation(feedback, b"windowOpacity")
        fade_in.setDuration(150)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)
        
        # Create fade out animation
        fade_out = QPropertyAnimation(feedback, b"windowOpacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)
        
        # Create sequential animation group
        anim_group = QSequentialAnimationGroup()
        anim_group.addAnimation(fade_in)
        anim_group.addPause(800)  # Show for 800ms
        anim_group.addAnimation(fade_out)
        
        # Hide and destroy the label after animation
        anim_group.finished.connect(feedback.deleteLater)
        anim_group.start()

    def continue_with_analysis(self):
        """Handle the 'Continue with Analysis' button click with transition animation"""
        # Validate scanned data
        if not any(self.vehicle_info.values()):
            self.show_error_message(
                "Incomplete Data",
                "No vehicle information available for analysis."
            )
            return
            
        # Create fade out animation for transition
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)
        
        # Open main window after animation completes
        fade_out.finished.connect(self.open_main_window)
        fade_out.start()

    def open_main_window(self):
        """Open the main analysis window"""
        try:
            from gui.main_window import MainWindow
            # Create MainWindow instance and pass the scanned data
            self.main_window = MainWindow(scanned_data=self.vehicle_info)
            self.main_window.show()
            self.close()
        except ImportError as e:
            print("Import failed:", e)
            self.setWindowOpacity(1.0)  # Restore opacity
            self.show_error_message("Error", "Failed to open analysis window")

    def show_error_message(self, title, message):
        """Show styled error message dialog"""
        error_dialog = QMessageBox(self)
        error_dialog.setWindowTitle(title)
        error_dialog.setText(message)
        error_dialog.setIcon(QMessageBox.Warning)
        
        # Apply custom styling
        error_dialog.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.uv_darker};
                color: {self.uv_light};
            }}
            QMessageBox QLabel {{
                color: {self.uv_light};
                font-size: 12px;
                min-width: 300px;
            }}
            QPushButton {{
                background-color: {self.uv_primary};
                color: {self.uv_dark};
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.uv_hover};
            }}
            QPushButton:pressed {{
                background-color: {self.uv_pressed};
            }}
        """)
        
        error_dialog.exec_()

    def handle_scan_error(self, error_message):
        """Handle scanning errors with enhanced UI feedback and animations"""
        # Play error animation
        self.play_error_animation()
        
        # Reset UI
        self.reset_scan_ui()
        
        # Show error message with icon
        self.status_message.setText(f"✗ {error_message}")
        self.status_message.setStyleSheet(f"""
            color: {self.uv_error};
            font-weight: 500;
            padding: 5px 15px;
            background-color: rgba(255, 82, 82, 0.15);
            border-radius: 15px;
        """)
        
        # Update scan instructions
        self.scan_instructions.setText("Please try again or use manual entry")
        self.scan_instructions.setStyleSheet(f"""
            color: {self.uv_light};
            margin-top: 15px;
            letter-spacing: 0.5px;
        """)
        
        # Fade out the status message after delay
        QTimer.singleShot(3000, self.fade_status_message)

    def play_error_animation(self):
        """Play an error animation after failed scan"""
        # Create a sequence of animations for error feedback
        
        # 1. Flash the scan container with error color
        flash_anim = QPropertyAnimation(self.scan_image_container, b"styleSheet")
        flash_anim.setDuration(300)
        flash_anim.setStartValue(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 120px;
                border: 2px solid {self.uv_primary};
            }}
        """)
        flash_anim.setEndValue(f"""
            QFrame {{
                background-color: rgba(255, 82, 82, 0.3);
                border-radius: 120px;
                border: 3px solid {self.uv_error};
            }}
        """)
        
        # 2. Shake animation
        shake_anim = QSequentialAnimationGroup()
        
        # Create a series of small position changes for shaking effect
        current_geo = self.scan_image_container.geometry()
        center_x = current_geo.x()
        
        # Add small movements left and right
        for i in range(5):
            # Move right
            move_right = QPropertyAnimation(self.scan_image_container, b"geometry")
            move_right.setDuration(50)
            move_right.setStartValue(QRect(center_x - 10 if i % 2 else center_x, 
                                         current_geo.y(), 
                                         current_geo.width(), 
                                         current_geo.height()))
            move_right.setEndValue(QRect(center_x + 10, 
                                       current_geo.y(), 
                                       current_geo.width(), 
                                       current_geo.height()))
            shake_anim.addAnimation(move_right)
            
            # Move left
            move_left = QPropertyAnimation(self.scan_image_container, b"geometry")
            move_left.setDuration(50)
            move_left.setStartValue(QRect(center_x + 10, 
                                        current_geo.y(), 
                                        current_geo.width(), 
                                        current_geo.height()))
            move_left.setEndValue(QRect(center_x - 10 if i < 4 else center_x, 
                                      current_geo.y(), 
                                      current_geo.width(), 
                                      current_geo.height()))
            shake_anim.addAnimation(move_left)
        
        # Create animation group and run sequentially
        anim_group = QSequentialAnimationGroup()
        anim_group.addAnimation(flash_anim)
        anim_group.addAnimation(shake_anim)
        anim_group.start()

    def submit_manual_info(self):
        """Process manually entered vehicle information with enhanced validation and feedback"""
        # Get values from input fields
        vin = self.vin_input.text().strip()
        imei = self.imei_input.text().strip()
        uuid = self.uuid_input.text().strip()
        
        # Validate - at least one field should have a value
        if not (vin or imei or uuid):
            # Show error with shake animation on fields
            self.shake_input_field(self.vin_input)
            self.shake_input_field(self.imei_input)
            self.shake_input_field(self.uuid_input)
            
            self.status_message.setText("Please enter at least one field")
            self.status_message.setStyleSheet(f"""
                color: {self.uv_error};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(255, 82, 82, 0.15);
                border-radius: 15px;
            """)
            return
            
        # Basic validation for VIN (if provided)
        if vin and (len(vin) != 17 or not vin.isalnum()):
            self.shake_input_field(self.vin_input)
            self.status_message.setText("VIN should be 17 alphanumeric characters")
            self.status_message.setStyleSheet(f"""
                color: {self.uv_warning};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(255, 171, 64, 0.15);
                border-radius: 15px;
            """)
            return
            
        # Basic validation for IMEI (if provided)
        if imei and (len(imei) != 15 or not imei.isdigit()):
            self.shake_input_field(self.imei_input)
            self.status_message.setText("IMEI should be 15 digits")
            self.status_message.setStyleSheet(f"""
                color: {self.uv_warning};
                font-weight: 500;
                padding: 5px 15px;
                background-color: rgba(255, 171, 64, 0.15);
                border-radius: 15px;
            """)
            return
        
        # Store the values
        self.vehicle_info['vin'] = vin
        self.vehicle_info['imei'] = imei
        self.vehicle_info['uuid'] = uuid
        
        # Play success animation on submit button
        self.animate_submit_success()
        
        # Display success message
        self.status_message.setText("✓ Information submitted successfully!")
        self.status_message.setStyleSheet(f"""
            color: {self.uv_secondary};
            font-weight: 500;
            padding: 5px 15px;
            background-color: rgba(0, 230, 118, 0.15);
            border-radius: 15px;
        """)
        
        # Clear input fields with fade effect
        self.fade_clear_input(self.vin_input)
        self.fade_clear_input(self.imei_input)
        self.fade_clear_input(self.uuid_input)
        
        # Display the vehicle information in results view
        self.display_vehicle_info()
        
        # Switch to results view with delay for better UX
        QTimer.singleShot(800, self.show_results_view)

    def shake_input_field(self, input_field):
        """Shake an input field to indicate error"""
        # Create shake animation
        shake = QSequentialAnimationGroup()
        
        # Get original position
        original_pos = input_field.pos()
        
        # Create a series of small position changes
        for i in range(5):
            # Move right
            move_right = QPropertyAnimation(input_field, b"pos")
            move_right.setDuration(40)
            move_right.setStartValue(QPoint(original_pos.x() - 5 if i % 2 else original_pos.x(), original_pos.y()))
            move_right.setEndValue(QPoint(original_pos.x() + 5, original_pos.y()))
            shake.addAnimation(move_right)
            
            # Move left
            move_left = QPropertyAnimation(input_field, b"pos")
            move_left.setDuration(40)
            move_left.setStartValue(QPoint(original_pos.x() + 5, original_pos.y()))
            move_left.setEndValue(QPoint(original_pos.x() - 5 if i < 4 else original_pos.x(), original_pos.y()))
            shake.addAnimation(move_left)
        
        # Also change the border color to indicate error
        input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 2px solid {self.uv_error};
                border-radius: 8px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
        """)
        
        # Reset style after shake
        shake.finished.connect(lambda: input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
            QLineEdit:focus {{
                border: 2px solid {self.uv_primary};
                background-color: rgba(45, 45, 45, 0.7);
            }}
            QLineEdit:hover {{
                border: 1px solid #666666;
            }}
        """))
        
        # Start animation
        shake.start()

    def animate_submit_success(self):
        """Animate the submit button on successful submission"""
        # Create a glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(30)
        glow.setColor(QColor(0, 230, 118, 150))
        glow.setOffset(0, 0)
        
        # Store original effect
        original_effect = self.submit_button.graphicsEffect()
        self.submit_button.setGraphicsEffect(glow)
        
        # Change button style temporarily
        original_style = self.submit_button.styleSheet()
        self.submit_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_secondary_dark}, stop:1 {self.uv_secondary});
                color: {self.uv_dark};
                border: none;
                border-radius: 27px;
                padding: 12px 30px;
            }}
        """)
        
        # Create a scale animation
        scale_up = QPropertyAnimation(self.submit_button, b"geometry")
        scale_up.setDuration(150)
        current_geo = self.submit_button.geometry()
        scale_up.setStartValue(current_geo)
        scale_up.setEndValue(QRect(
            current_geo.x() - 5, 
            current_geo.y() - 5, 
            current_geo.width() + 10, 
            current_geo.height() + 10
        ))
        scale_up.setEasingCurve(QEasingCurve.OutQuad)
        
        # Scale down animation
        scale_down = QPropertyAnimation(self.submit_button, b"geometry")
        scale_down.setDuration(300)
        scale_down.setStartValue(QRect(
            current_geo.x() - 5, 
            current_geo.y() - 5, 
            current_geo.width() + 10, 
            current_geo.height() + 10
        ))
        scale_down.setEndValue(current_geo)
        scale_down.setEasingCurve(QEasingCurve.OutElastic)
        
        # Sequential animation
        anim_group = QSequentialAnimationGroup()
        anim_group.addAnimation(scale_up)
        anim_group.addAnimation(scale_down)
        
        # Reset after animation
        anim_group.finished.connect(lambda: self.submit_button.setStyleSheet(original_style))
        anim_group.finished.connect(lambda: self.submit_button.setGraphicsEffect(original_effect))
        
        anim_group.start()

    def fade_clear_input(self, input_field):
        """Clear an input field with fade animation"""
        # Create fade out animation
        fade_out = QPropertyAnimation(input_field, b"styleSheet")
        fade_out.setDuration(300)
        fade_out.setStartValue(input_field.styleSheet())
        fade_out.setEndValue(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 12px 15px;
                color: rgba(255, 255, 255, 0.3);
                selection-background-color: {self.uv_primary};
            }}
        """)
        
        # Clear the text and reset style after fade
        fade_out.finished.connect(input_field.clear)
        fade_out.finished.connect(lambda: input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 12px 15px;
                color: {self.uv_light};
                selection-background-color: {self.uv_primary};
            }}
            QLineEdit:focus {{
                border: 2px solid {self.uv_primary};
                background-color: rgba(45, 45, 45, 0.7);
            }}
            QLineEdit:hover {{
                border: 1px solid #666666;
            }}
        """))
        
        fade_out.start()

    def save_vehicle_info(self):
        """Save the vehicle information to a file with enhanced UX and feedback"""
        if not any(self.vehicle_info.values()):
            self.show_notification("No vehicle information to save", "error")
            return
            
        try:
            # Ask for file location with styled dialog
            file_name = f"Vehicle_Info_{self.vehicle_info['vin'] or 'Unknown'}.txt"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Vehicle Information",
                file_name,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if not file_path:
                return
                
            # Show saving indicator
            self.show_notification("Saving information...", "info")
                
            # Write to file with enhanced formatting
            with open(file_path, 'w') as file:
                file.write("ULTRAVIOLETTE AUTOMOTIVE - VEHICLE INFORMATION\n")
                file.write("=" * 50 + "\n\n")
                
                if self.vehicle_info['vin']:
                    file.write(f"VIN:  {self.vehicle_info['vin']}\n")
                if self.vehicle_info['imei']:
                    file.write(f"IMEI: {self.vehicle_info['imei']}\n")
                if self.vehicle_info['uuid']:
                    file.write(f"UUID: {self.vehicle_info['uuid']}\n")
                
                file.write("\n" + "=" * 50 + "\n")
                file.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write(f"Ultraviolette Automotive Dashboard v1.2.0\n")
            
            # Show success message with animation
            self.show_notification("✓ Information saved successfully!", "success")
            
            # Animate the save button
            self.animate_button_success(self.save_button)
            
        except Exception as e:
            # Show error message with animation
            self.show_notification(f"✗ Error saving file: {str(e)}", "error")

    def show_notification(self, message, message_type="info"):
        """Show a floating notification with animation"""
        # Create notification widget
        notification = QLabel(message)
        notification.setFont(QFont(self.font_family, 11, QFont.Bold if message_type == "success" else QFont.Normal))
        notification.setAlignment(Qt.AlignCenter)
        
        # Style based on message type
        if message_type == "success":
            bg_color = self.uv_secondary
            text_color = self.uv_dark
            shadow_color = QColor(0, 230, 118, 100)
        elif message_type == "error":
            bg_color = self.uv_error
            text_color = self.uv_light
            shadow_color = QColor(255, 82, 82, 100)
        else:  # info
            bg_color = self.uv_primary
            text_color = self.uv_dark
            shadow_color = QColor(0, 195, 255, 100)
            
        notification.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            padding: 12px 24px;
            border-radius: 20px;
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(shadow_color)
        shadow.setOffset(0, 2)
        notification.setGraphicsEffect(shadow)
        
        # Set window flags
        notification.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        
        # Calculate position - centered at top of results view
        results_rect = self.results_view.geometry()
        notification_width = 400
        notification_height = 50
        
        global_pos = self.mapToGlobal(QPoint(
            results_rect.x() + (results_rect.width() - notification_width) // 2,
            results_rect.y() + 20
        ))
        
        notification.setFixedSize(notification_width, notification_height)
        notification.move(global_pos)
        notification.show()
        
        # Create slide-in animation
        slide_in = QPropertyAnimation(notification, b"pos")
        slide_in.setDuration(300)
        slide_in.setStartValue(QPoint(global_pos.x(), global_pos.y() - 50))
        slide_in.setEndValue(global_pos)
        slide_in.setEasingCurve(QEasingCurve.OutCubic)
        
        # Create fade-out animation
        fade_out = QPropertyAnimation(notification, b"windowOpacity")
        fade_out.setDuration(300)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)
        
        # Create animation sequence
        anim_group = QSequentialAnimationGroup()
        anim_group.addAnimation(slide_in)
        anim_group.addPause(2000)  # Show for 2 seconds
        anim_group.addAnimation(fade_out)
        
        # Clean up after animation
        anim_group.finished.connect(notification.deleteLater)
        anim_group.start()

    def animate_button_success(self, button):
        """Animate a button to indicate successful action"""
        # Store original properties
        original_style = button.styleSheet()
        original_effect = button.graphicsEffect()
        
        # Create glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(30)
        glow.setColor(QColor(0, 230, 118, 150))
        glow.setOffset(0, 0)
        button.setGraphicsEffect(glow)
        
        # Change button style temporarily
        button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_secondary_dark}, stop:1 {self.uv_secondary});
                color: {self.uv_dark};
                border: none;
                border-radius: 25px;
                padding: 12px 30px;
            }}
        """)
        
        # Create pulse animation
        pulse_anim = QSequentialAnimationGroup()
        
        # First pulse
        scale_up1 = QPropertyAnimation(button, b"geometry")
        scale_up1.setDuration(150)
        current_geo = button.geometry()
        scale_up1.setStartValue(current_geo)
        scale_up1.setEndValue(QRect(
            current_geo.x() - 5, 
            current_geo.y() - 5, 
            current_geo.width() + 10, 
            current_geo.height() + 10
        ))
        
        scale_down1 = QPropertyAnimation(button, b"geometry")
        scale_down1.setDuration(150)
        scale_down1.setStartValue(QRect(
            current_geo.x() - 5, 
            current_geo.y() - 5, 
            current_geo.width() + 10, 
            current_geo.height() + 10
        ))
        scale_down1.setEndValue(current_geo)
        
        pulse_anim.addAnimation(scale_up1)
        pulse_anim.addAnimation(scale_down1)
        
        # Reset after animation
        pulse_anim.finished.connect(lambda: button.setStyleSheet(original_style))
        pulse_anim.finished.connect(lambda: button.setGraphicsEffect(original_effect))
        
        pulse_anim.start()

    def clear_vehicle_info(self):
        """Clear the displayed vehicle information with smooth transitions"""
        # Confirm dialog with styled UI
        confirm_dialog = QMessageBox(self)
        confirm_dialog.setWindowTitle("Confirm Clear")
        confirm_dialog.setText("Are you sure you want to clear all vehicle information?")
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
                font-size: 12px;
                min-width: 300px;
            }}
            QMessageBox QPushButton {{
                background-color: {self.uv_gray};
                color: {self.uv_light};
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {self.uv_primary};
                color: {self.uv_dark};
            }}
            QMessageBox QPushButton[text="Yes"] {{
                background-color: {self.uv_error};
                color: {self.uv_light};
            }}
            QMessageBox QPushButton[text="Yes"]:hover {{
                background-color: #ff6e6e;
            }}
        """)
        
        confirm = confirm_dialog.exec_()
        
        if confirm == QMessageBox.Yes:
            # Fade out existing cards
            self.fade_out_info_cards()
            
            # Clear stored info
            self.vehicle_info = {
                'vin': '',
                'imei': '',
                'uuid': ''
            }
            
            # Show temporary feedback
            self.show_notification("Vehicle information cleared", "info")
            
            # Switch back to scan view after a short delay
            QTimer.singleShot(800, self.show_scan_view)

    def fade_out_info_cards(self):
        """Fade out all info cards with staggered animations"""
        # Find all info cards
        cards = []
        for i in range(self.info_cards_layout.count()):
            widget = self.info_cards_layout.itemAt(i).widget()
            if widget and widget.objectName() == "infoCard":
                cards.append(widget)
        
        # Create staggered animations
        for i, card in enumerate(cards):
            # Create fade out animation
            fade_out = QPropertyAnimation(card, b"windowOpacity")
            fade_out.setDuration(300)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setEasingCurve(QEasingCurve.InCubic)
            
            # Add slight upward movement
            move_up = QPropertyAnimation(card, b"pos")
            move_up.setDuration(300)
            current_pos = card.pos()
            move_up.setStartValue(current_pos)
            move_up.setEndValue(QPoint(current_pos.x(), current_pos.y() - 20))
            move_up.setEasingCurve(QEasingCurve.InCubic)
            
            # Create parallel animation group
            anim_group = QParallelAnimationGroup()
            anim_group.addAnimation(fade_out)
            anim_group.addAnimation(move_up)
            
            # Start with delay based on card index
            QTimer.singleShot(i * 100, anim_group.start)
            
            # Remove card after animation
            anim_group.finished.connect(lambda c=card: c.setParent(None))

    def show_help(self):
        """Show help information in a modern dialog with enhanced styling"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help & Documentation")
        help_dialog.setMinimumSize(650, 550)
        
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
        help_layout.setSpacing(25)
        
        # Title with icon and enhanced styling
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignLeft)
        help_icon = QLabel()
        help_pixmap = QPixmap("assets/help_icon.png")
        if not help_pixmap.isNull():
            help_icon.setPixmap(help_pixmap.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_layout.addWidget(help_icon)
        title_layout.addSpacing(12)
        
        title = QLabel("Barcode Scanner Help")
        title.setFont(QFont(self.font_family, 20, QFont.Bold))
        title.setStyleSheet(f"""
            color: {self.uv_light};
            padding-bottom: 5px;
            border-bottom: 2px solid {self.uv_primary};
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        help_layout.addLayout(title_layout)
        
        # Help content in tabs for better organization
        tab_widget = QTabWidget()
        tab_widget.setFont(QFont(self.font_family, 11))
        tab_widget.setStyleSheet(f"""
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
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {self.uv_darker};
                color: {self.uv_primary};
                border-bottom: 2px solid {self.uv_primary};
            }}
            QTabBar::tab:hover:!selected {{
                background: {self.uv_gray};
            }}
        """)
        
        # Create tabs for different help sections
        general_tab = QWidget()
        scanning_tab = QWidget()
        troubleshooting_tab = QWidget()
        
        tab_widget.addTab(general_tab, "General")
        tab_widget.addTab(scanning_tab, "Scanning")
        tab_widget.addTab(troubleshooting_tab, "Troubleshooting")
        
        # Set up general tab
        self.setup_general_help_tab(general_tab)
        
        # Set up scanning tab
        self.setup_scanning_help_tab(scanning_tab)
        
        # Set up troubleshooting tab
        self.setup_troubleshooting_help_tab(troubleshooting_tab)
        
        help_layout.addWidget(tab_widget)
        
        # Close button with enhanced styling
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        
        close_button = QPushButton("Close")
        close_button.setFont(QFont(self.font_family, 12, QFont.Bold))
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setFixedSize(140, 45)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_primary}, stop:1 #0088cc);
                color: {self.uv_dark};
                border: none;
                border-radius: 22px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_hover}, stop:1 #00a0e6);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                              stop:0 {self.uv_pressed}, stop:1 #007ab8);
            }}
        """)
        
        # Add button glow effect
        button_glow = QGraphicsDropShadowEffect()
        button_glow.setBlurRadius(15)
        button_glow.setColor(QColor(0, 195, 255, 70))
        button_glow.setOffset(0, 2)
        close_button.setGraphicsEffect(button_glow)
        
        close_button.clicked.connect(help_dialog.accept)
        button_layout.addWidget(close_button)
        help_layout.addLayout(button_layout)
        
        # Fade in animation for dialog
        help_dialog.setWindowOpacity(0)
        fade_in = QPropertyAnimation(help_dialog, b"windowOpacity")
        fade_in.setDuration(300)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)
        
        # Show dialog and start animation
        help_dialog.show()
        fade_in.start()
        
        # Execute dialog
        help_dialog.exec_()

    def setup_general_help_tab(self, tab):
        """Set up the general help tab with enhanced styling and content"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 15, 5)
        content_layout.setSpacing(25)
        
        # Add overview card
        overview_card = self.create_help_card(
            "Overview",
            "This application allows you to scan and identify vehicles using their barcode information. "
            "The scanned data can include VIN, IMEI, and UUID information which can be used for vehicle "
            "registration, diagnostics, and tracking."
        )
        content_layout.addWidget(overview_card)
        
        # Add interface card
        interface_card = self.create_help_card(
            "Interface Guide",
            "The application is divided into two main sections:\n\n"
            "• <b>Scan Barcode:</b> Use this tab to scan vehicle barcodes using the connected scanner.\n\n"
            "• <b>Manual Entry:</b> If scanning is not possible, you can manually enter vehicle information."
        )
        content_layout.addWidget(interface_card)
        
        # Add workflow card
        workflow_card = self.create_help_card(
            "Typical Workflow",
            "1. Scan a vehicle barcode or enter information manually\n"
            "2. Review the captured vehicle information\n"
            "3. Save the information or continue with analysis\n"
            "4. If needed, you can rescan or clear the information"
        )
        content_layout.addWidget(workflow_card)
        
        # Add version info card
        version_card = self.create_help_card(
            "Version Information",
            f"<b>Current Version:</b> 1.2.0<br>"
            f"<b>Release Date:</b> April 2025<br>"
            f"<b>Compatible Scanners:</b> All standard USB barcode scanners<br>"
            f"<b>Required Permissions:</b> USB device access"
        )
        content_layout.addWidget(version_card)
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def setup_scanning_help_tab(self, tab):
        """Set up the scanning help tab with enhanced styling and content"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 15, 5)
        content_layout.setSpacing(25)
        
        # Add scanner setup card
        scanner_card = self.create_help_card(
            "Scanner Setup",
            "1. Connect your barcode scanner to an available USB port\n"
            "2. Wait for the device to be recognized by your system\n"
            "3. The application will automatically detect the scanner\n"
            "4. If the scanner isn't detected, try reconnecting or using a different port"
        )
        content_layout.addWidget(scanner_card)
        
        # Add scanning tips card
        tips_card = self.create_help_card(
            "Scanning Tips",
            "• Hold the scanner 4-8 inches (10-20 cm) from the barcode\n"
            "• Ensure the barcode is well-lit and clearly visible\n"
            "• Keep the scanner steady during the scanning process\n"
            "• For best results, scan at a slight angle to avoid glare\n"
            "• If scanning fails, try adjusting the distance or angle"
        )
        content_layout.addWidget(tips_card)
        
        # Add barcode types card
        barcode_card = self.create_help_card(
            "Supported Barcode Types",
            "This application supports the following barcode formats:\n\n"
            "• QR Codes\n"
            "• Code 128\n"
            "• Code 39\n"
            "• Data Matrix\n"
            "• UPC/EAN\n\n"
            "Vehicle information should be encoded in format: 'VIN:value;IMEI:value;UUID:value'"
        )
        content_layout.addWidget(barcode_card)
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def setup_troubleshooting_help_tab(self, tab):
        """Set up the troubleshooting help tab with enhanced styling and content"""
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 15, 5)
        content_layout.setSpacing(25)
        
        # Add common issues card
        issues_card = self.create_help_card(
            "Common Issues",
            "<b>Scanner not detected:</b> Check USB connection and ensure the scanner is powered on.<br><br>"
            "<b>Barcode not scanning:</b> Clean the barcode surface and ensure proper lighting conditions.<br><br>"
            "<b>Data not recognized:</b> Verify the barcode format matches the expected pattern.br><br>"
            "<b>Application freezes:</b> Restart the application and check for system resource constraints."
        )
        content_layout.addWidget(issues_card)
        
        # Add error messages card
        errors_card = self.create_help_card(
            "Error Messages",
            "<b>\"Scanner error\":</b> The scanner could not be initialized. Check connection and permissions.<br><br>"
            "<b>\"No barcode detected\":</b> The scanner couldn't read a valid barcode. Try repositioning.<br><br>"
            "<b>\"Invalid data format\":</b> The scanned barcode doesn't contain the expected information.<br><br>"
            "<b>\"Connection timeout\":</b> The scanner took too long to respond. Check for interference."
        )
        content_layout.addWidget(errors_card)
        
        # Add contact support card with styled links
        support_card = self.create_help_card(
            "Contact Support",
            "If you're experiencing persistent issues, please contact our support team:<br><br>"
            f"<span style='color: {self.uv_primary};'>Email:</span> support@ultraviolette.com<br>"
            f"<span style='color: {self.uv_primary};'>Phone:</span> +91-1234567890<br>"
            f"<span style='color: {self.uv_primary};'>Hours:</span> Monday-Friday, 9:00 AM - 6:00 PM IST<br><br>"
            "Please include your application version and a detailed description of the issue."
        )
        content_layout.addWidget(support_card)
        
        # Add system requirements card
        system_card = self.create_help_card(
            "System Requirements",
            "<b>Operating System:</b> Windows 10/11, macOS 12+, or Linux<br>"
            "<b>CPU:</b> Intel Core i3 or equivalent (2.0 GHz or higher)<br>"
            "<b>RAM:</b> 4 GB minimum, 8 GB recommended<br>"
            "<b>Disk Space:</b> 500 MB free space<br>"
            "<b>USB:</b> Available USB 2.0 or 3.0 port<br>"
            "<b>Display:</b> 1280x720 or higher resolution<br>"
            "<b>Network:</b> Internet connection for updates"
        )
        content_layout.addWidget(system_card)
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def create_help_card(self, title, content):
        """Create a styled help card with title and content"""
        card = QFrame()
        card.setObjectName("topicCard")
        
        # Apply glass morphism effect
        card.setStyleSheet(f"""
            QFrame#topicCard {{
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        
        # Add shadow effect
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setColor(QColor(0, 0, 0, 80))
        card_shadow.setOffset(0, 4)
        card.setGraphicsEffect(card_shadow)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)
        
        # Title with accent line
        title_container = QVBoxLayout()
        title_container.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(self.font_family, 14, QFont.Bold))
        title_label.setStyleSheet(f"color: {self.uv_primary};")
        title_container.addWidget(title_label)
        
        # Add subtle separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setStyleSheet(f"""
            background-color: rgba(0, 195, 255, 0.3);
            min-height: 1px;
            max-height: 1px;
            margin: 0px;
        """)
        title_container.addWidget(separator)
        
        card_layout.addLayout(title_container)
        
        # Content with rich text support
        content_label = QLabel()
        content_label.setFont(QFont(self.font_family, 11))
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.RichText)
        content_label.setText(content)
        content_label.setStyleSheet(f"""
            color: {self.uv_light};
            line-height: 150%;
        """)
        card_layout.addWidget(content_label)
        
        return card

    def logout(self):
        """Handle logout action with confirmation dialog and smooth transition"""
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
                font-size: 12px;
                min-width: 300px;
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
            QMessageBox QPushButton[text="Yes"] {{
                background-color: {self.uv_primary};
                color: {self.uv_dark};
            }}
        """)
        
        confirm = confirm_dialog.exec_()
        
        if confirm == QMessageBox.Yes:
            # Create fade out animation
            fade_out = QPropertyAnimation(self, b"windowOpacity")
            fade_out.setDuration(300)
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setEasingCurve(QEasingCurve.InCubic)
            
            # Connect to logout function
            fade_out.finished.connect(self.complete_logout)
            fade_out.start()
    
    def complete_logout(self):
        """Complete the logout process after animation"""
        try:
            from gui.login_window import LoginWindow
            self.login_window = LoginWindow()
            
            # Fade in the login window
            self.login_window.setWindowOpacity(0)
            self.login_window.show()
            
            fade_in = QPropertyAnimation(self.login_window, b"windowOpacity")
            fade_in.setDuration(400)
            fade_in.setStartValue(0)
            fade_in.setEndValue(1)
            fade_in.setEasingCurve(QEasingCurve.OutCubic)
            fade_in.start()
            
            self.close()
        except ImportError as e:
            print(f"Login window import failed: {e}")
            # If import fails, just close the current window
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application-wide style
    app.setStyle("Fusion")
    
    # Set application font
    font = QFont("Montserrat", 10)
    app.setFont(font)
    
    # Apply custom stylesheets to tooltips and other global elements
    app.setStyleSheet("""
        QToolTip {
            background-color: #121212;
            color: white;
            border: 1px solid #00C3FF;
            border-radius: 4px;
            padding: 5px;
            opacity: 220;
        }
    """)
    
    # Create and show main window with splash effect
    window = BarcodeScanWindow()
    
    # Start with zero opacity for fade-in effect
    window.setWindowOpacity(0)
    window.show()
    
    # Fade in animation
    fade_animation = QPropertyAnimation(window, b"windowOpacity")
    fade_animation.setDuration(800)
    fade_animation.setStartValue(0)
    fade_animation.setEndValue(1)
    fade_animation.setEasingCurve(QEasingCurve.OutCubic)
    fade_animation.start()
    
    sys.exit(app.exec_())