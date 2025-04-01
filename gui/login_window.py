import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QHBoxLayout, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont, QPixmap, QResizeEvent, QColor, QPalette, QIcon
from PyQt5.QtCore import Qt, QSize, pyqtSignal

class LoginWindow(QMainWindow):
    login_successful = pyqtSignal()  # Signal to indicate successful login

    def __init__(self):
        super().__init__()

        # Ultraviolette brand colors
        self.uv_blue = "#00C3FF"  # Electric blue accent
        self.uv_dark = "#121212"  # Dark background
        self.uv_light = "#FFFFFF"  # White text
        self.uv_gray = "#333333"  # Secondary dark

        self.setWindowTitle("Ultraviolette Dashboard")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        
        # Set application icon
        self.setWindowIcon(QIcon("assets/small_icon.PNG"))
        
        # Set dark theme globally
        self.apply_dark_theme()
        
        self.init_ui()

    def apply_dark_theme(self):
        """Apply Ultraviolette's dark theme to the entire application"""
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
        """Create the login UI with Ultraviolette branding"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Image panel - will expand to fill available space
        self.image_panel = QLabel()
        self.image_panel.setAlignment(Qt.AlignCenter)
        self.image_panel.setScaledContents(False)  # We'll handle scaling ourselves
        self.bg_pixmap = QPixmap("assets/bg_imnage.png")
        self.update_background_image()
        
        # Login panel - fixed width regardless of window size
        self.login_panel = QWidget()
        self.login_panel.setFixedWidth(400)  # Fixed width for login panel
        self.login_panel.setStyleSheet(f"background-color: {self.uv_dark};")
        login_layout = QVBoxLayout(self.login_panel)
        login_layout.setContentsMargins(40, 60, 40, 60)
        
        # Add logo at the top - now bigger
        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/ultraviolette_automotive_logo.jpg")
        logo_label.setPixmap(logo_pixmap.scaled(300, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)  # Center the logo
        login_layout.addWidget(logo_label)
        
        login_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Welcome text
        title = QLabel("Welcome Back")
        title.setFont(QFont("Montserrat", 24, QFont.Bold))
        title.setStyleSheet(f"color: {self.uv_light};")
        title.setAlignment(Qt.AlignCenter)  # Center the text
        login_layout.addWidget(title)
        
        subtitle = QLabel("Sign in to access your Ultraviolette dashboard")
        subtitle.setFont(QFont("Montserrat", 12))
        subtitle.setStyleSheet(f"color: #999999; margin-bottom: 30px;")
        subtitle.setAlignment(Qt.AlignCenter)  # Center the text
        login_layout.addWidget(subtitle)
        
        # Form fields
        # Username
        username_label = QLabel("Username")
        username_label.setFont(QFont("Montserrat", 10))
        username_label.setStyleSheet(f"color: {self.uv_light}; margin-top: 20px;")
        login_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFont(QFont("Montserrat", 11))
        self.username_input.setMinimumHeight(45)
        self.username_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                color: {self.uv_light};
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 10px 15px;
                margin-bottom: 15px;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.uv_blue};
            }}
        """)
        login_layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password")
        password_label.setFont(QFont("Montserrat", 10))
        password_label.setStyleSheet(f"color: {self.uv_light}; margin-top: 10px;")
        login_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFont(QFont("Montserrat", 11))
        self.password_input.setMinimumHeight(45)
        self.password_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.uv_gray};
                color: {self.uv_light};
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 10px 15px;
                margin-bottom: 20px;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.uv_blue};
            }}
        """)
        login_layout.addWidget(self.password_input)
        
        # Login Button
        login_button = QPushButton("SIGN IN")
        login_button.setFont(QFont("Montserrat", 11, QFont.Bold))
        login_button.setMinimumHeight(48)
        login_button.setCursor(Qt.PointingHandCursor)
        login_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: #33D1FF;
            }}
            QPushButton:pressed {{
                background-color: #0099CC;
            }}
        """)
        login_button.clicked.connect(self.handle_login)
        login_layout.addWidget(login_button)
        
        # Forgot password link
        forgot_pw = QPushButton("Forgot password?")
        forgot_pw.setFont(QFont("Montserrat", 10))
        forgot_pw.setFlat(True)
        forgot_pw.setCursor(Qt.PointingHandCursor)
        forgot_pw.setStyleSheet(f"""
            QPushButton {{
                color: {self.uv_blue};
                border: none;
                padding: 8px;
                text-align: center;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        # Create a layout to center the forgot password button
        forgot_layout = QHBoxLayout()
        forgot_layout.addStretch()
        forgot_layout.addWidget(forgot_pw)
        forgot_layout.addStretch()
        login_layout.addLayout(forgot_layout)
        
        login_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Footer text
        footer = QLabel("© 2025 Ultraviolette Automotive Pvt. Ltd.")
        footer.setFont(QFont("Montserrat", 9))
        footer.setStyleSheet("color: #666666;")
        footer.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(footer)
        
        # Add panels to main layout
        main_layout.addWidget(self.image_panel, 1)  # Image panel takes all remaining space
        main_layout.addWidget(self.login_panel, 0)  # Login panel has fixed width
        
        # Connect enter key to login
        self.password_input.returnPressed.connect(login_button.click)
        self.username_input.returnPressed.connect(self.password_input.setFocus)

    def update_background_image(self):
        """Update the background image display based on current window size"""
        if self.bg_pixmap.isNull():
            return
            
        # Calculate the available width for the image (total width minus login panel width)
        image_width = self.width() - 400  # Subtract login panel width
        
        # Scale image to fit the panel while preserving aspect ratio
        scaled_pixmap = self.bg_pixmap.scaled(
            image_width, 
            self.height(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        self.image_panel.setPixmap(scaled_pixmap)

    def resizeEvent(self, event: QResizeEvent):
        """Handle window resize events"""
        super().resizeEvent(event)
        self.update_background_image()

    def handle_login(self):
        """Verify login credentials."""
        username = self.username_input.text()
        password = self.password_input.text()

        if username == "admin" and password == "admin123":
            self.login_successful.emit()  # Emit the signal on successful login
        else:
            error_msg = QMessageBox(self)
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("Authentication Failed")
            error_msg.setText("Invalid username or password")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {self.uv_dark};
                    color: {self.uv_light};
                }}
                QPushButton {{
                    background-color: {self.uv_blue};
                    color: {self.uv_dark};
                    min-width: 80px;
                    min-height: 30px;
                    border-radius: 4px;
                }}
            """)
            error_msg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply font throughout the app
    font = QFont("Montserrat")
    app.setFont(font)
    
    login = LoginWindow()
    login.show()
    sys.exit(app.exec_())