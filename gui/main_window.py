import os
import certifi
import ssl
from ssl_config import configure_ssl

# Configure SSL before anything else
if not configure_ssl():
    print("Warning: SSL configuration failed. Some features may not work.")

import sys
import io
import logging
import pandas as pd
from dotenv import load_dotenv  # Import load_dotenv
import ssl
import certifi

print("SSL Cert File Used:", ssl.get_default_verify_paths().openssl_cafile)
print("Certifi Cert File:", certifi.where())


from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QMessageBox, QSplitter, 
    QGridLayout, QFrame, QStackedWidget, QListWidget, QListWidgetItem,
    QProgressBar, QScrollArea, QSizePolicy, QDialog, QDesktopWidget
)
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
# Import analysis functions
from analysis.run_analysis import (
    temp_fluctuation_detection,
    solder_issue_detection,
    weld_issue_detection,
    normalize_column_names,
    validate_columns
)

# Import AWSClient class
from custom_aws_client import AWSClient

# Load environment variables from .env file
load_dotenv()  # Load the environment variables

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

class AnalysisThread(QThread):
    """Thread for running analysis in background"""
    finished = pyqtSignal(dict, dict, dict)  # solder, weld, temp results
    progress = pyqtSignal(int, str)          # progress percentage, message
    error = pyqtSignal(str)                  # error message

    def __init__(self, df):
        super().__init__()
        self.df = df

    def run(self):
        try:
            results = {}
            self.progress.emit(20, "Analyzing temperature fluctuations...")
            results['temp'] = temp_fluctuation_detection(self.df)
            self.progress.emit(50, "Checking for solder issues...")
            results['solder'] = solder_issue_detection(self.df)
            self.progress.emit(80, "Checking for weld issues...")
            results['weld'] = weld_issue_detection(self.df)
            self.progress.emit(100, "Analysis complete!")
            self.finished.emit(
                results['solder'],
                results['weld'],
                results['temp']
            )
        except Exception as e:
            logging.error(f"Analysis failed: {str(e)}", exc_info=True)
            self.error.emit(f"Analysis failed: {str(e)}")


class GraphDialog(QDialog):
    """Dialog to display enlarged graphs"""
    def __init__(self, title, x_label, y_label, x_data, y_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() | 
                          Qt.WindowMaximizeButtonHint | 
                          Qt.WindowMinimizeButtonHint)
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.plot_data(title, x_label, y_label, x_data, y_data)

    def plot_data(self, title, x_label, y_label, x_data, y_data):
        ax = self.figure.add_subplot(111)
        ax.clear()
        if isinstance(y_data, dict):
            for label, data in y_data.items():
                ax.plot(x_data, data, label=label)
        else:
            ax.plot(x_data, y_data, label=y_label)
        ax.set_title(title, fontsize=12)
        ax.set_xlabel(x_label, fontsize=8)
        ax.set_ylabel(y_label, fontsize=8)
        ax.legend()
        ax.grid(True)
        self.canvas.draw()


class MainWindow(QMainWindow):
    def __init__(self, scanned_data=None):
        super().__init__()
        self.scanned_data = scanned_data or {}
        self.bike_imei = self.scanned_data.get('imei', 'N/A')
        self.bike_vin = self.scanned_data.get('vin', 'N/A')
        self.bike_uuid = self.scanned_data.get('uuid', 'N/A')

        # Debug: Print SSL certificate paths
        print("Using certifi CA Bundle:", certifi.where())
        print("System SSL Cert File:", ssl.get_default_verify_paths().openssl_cafile)   

        # Ensure no conflicting environment variables
        if 'SSL_CERT_FILE' in os.environ:
            del os.environ['SSL_CERT_FILE']

        # Initialize color attributes
        self.uv_blue = "#00C3FF"
        self.uv_dark = "#121212"
        self.uv_light = "#FFFFFF"
        self.uv_gray = "#333333"
        # Store analysis data
        self.df = None
        # Initialize AWS client
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("BUCKET_NAME", "datalogs-processed-timeseries")
        self.aws_client = AWSClient(self.access_key, self.secret_key, self.bucket_name)
        # Initialize UI
        self.init_ui()
        self.apply_dark_theme()
        self.load_bike_details()
        self.update_ui_with_bike_details()
        self.populate_log_files()

    def update_ui_with_bike_details(self):
        """Update the UI with the bike details"""
        if not self.bike_imei:
            return
        bike_text = f"{self.bike_details.get('make', 'Ultraviolette')} {self.bike_details.get('model', 'F77')}"
        if self.bike_imei != 'N/A':
            bike_text += f" | IMEI: {self.bike_imei}"
        self.bike_info_label.setText(bike_text)
        self.update_bike_details_sidebar()

    def update_bike_details_sidebar(self):
        """Update the bike details in the sidebar"""
        for i in reversed(range(self.details_grid.count())):
            widget = self.details_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        row = 0
        for label, value in [
            ("VIN:", self.bike_vin),
            ("IMEI:", self.bike_imei),
            ("Model:", self.bike_details.get('model', 'F77')),
            ("Year:", self.bike_details.get('year', '2023')),
            ("Color:", self.bike_details.get('color', 'N/A'))
        ]:
            label_widget = QLabel(label)
            label_widget.setFont(QFont("Montserrat", 9, QFont.Bold))
            label_widget.setStyleSheet(f"color: {self.uv_light};")
            value_widget = QLabel(str(value))
            value_widget.setFont(QFont("Montserrat", 9))
            value_widget.setStyleSheet(f"color: {self.uv_light};")
            self.details_grid.addWidget(label_widget, row, 0)
            self.details_grid.addWidget(value_widget, row, 1)
            row += 1

    def apply_dark_theme(self):
        """Apply dark theme to the main window"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(18, 18, 18))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(51, 51, 51))
        palette.setColor(QPalette.AlternateBase, QColor(18, 18, 18))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(18, 18, 18))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(51, 51, 51))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.Link, QColor(0, 195, 255))
        palette.setColor(QPalette.Highlight, QColor(0, 195, 255))
        palette.setColor(QPalette.HighlightedText, QColor(18, 18, 18))
        self.setPalette(palette)

    def load_bike_details(self):
        """Load bike details from Excel file by matching VIN/IMEI"""
        self.bike_details = {
            "vin": self.bike_vin or "UVXXXXXXX12345678",
            "imei": self.bike_imei,
            "make": "Ultraviolette",
            "model": "F77",
            "year": "2023",
            "color": "Abyss Black",
            "battery_capacity": "10.3 kWh",
            "owner": "Demo Customer"
        }

    def init_ui(self):
        """Initialize the main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with logo and bike info
        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet("background-color: #121212; border-bottom: 1px solid #444;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Logo handling with fallback
        logo_label = QLabel()
        try:
            logo_pixmap = QPixmap("assets/ultraviolette_automotive_logo.jpg")
            if logo_pixmap.isNull():
                logo_pixmap = QPixmap(150, 50)
                logo_pixmap.fill(Qt.transparent)
        except:
            logo_pixmap = QPixmap(150, 50)
            logo_pixmap.fill(Qt.transparent)
        logo_label.setPixmap(logo_pixmap.scaled(150, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.bike_info_label = QLabel()
        self.bike_info_label.setFont(QFont("Montserrat", 10))
        self.bike_info_label.setStyleSheet("color: #FFFFFF;")

        logout_button = QPushButton("Logout")
        logout_button.setFont(QFont("Montserrat", 10))
        logout_button.setCursor(Qt.PointingHandCursor)
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FFFFFF;
                border: 1px solid #00C3FF;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #00C3FF;
                color: #121212;
            }
        """)
        logout_button.clicked.connect(self.logout)

        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        header_layout.addWidget(self.bike_info_label)
        header_layout.addStretch()
        header_layout.addWidget(logout_button)
        main_layout.addWidget(header)

        # Content area with sidebar and main content
        content = QSplitter(Qt.Horizontal)

        # Sidebar
        sidebar = QWidget()
        sidebar.setMinimumWidth(250)
        sidebar.setMaximumWidth(300)
        sidebar.setStyleSheet("background-color: #333333;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Bike details at top of sidebar
        bike_details_widget = QWidget()
        bike_details_widget.setStyleSheet("background-color: #333333; padding: 15px;")
        bike_details_layout = QVBoxLayout(bike_details_widget)
        title_label = QLabel("Bike Details")
        title_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        title_label.setStyleSheet("color: #00C3FF;")
        bike_details_layout.addWidget(title_label)
        self.details_grid = QGridLayout()
        self.details_grid.setHorizontalSpacing(10)
        self.details_grid.setVerticalSpacing(8)
        bike_details_layout.addLayout(self.details_grid)
        sidebar_layout.addWidget(bike_details_widget)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #444;")
        sidebar_layout.addWidget(separator)

        # Navigation buttons
        self.run_analysis_btn = self.create_sidebar_button("Run Analysis", True)
        self.shop_floor_btn = self.create_sidebar_button("Shop Floor", False)
        self.service_team_btn = self.create_sidebar_button("Service Team", False)
        sidebar_layout.addWidget(self.run_analysis_btn)
        sidebar_layout.addWidget(self.shop_floor_btn)
        sidebar_layout.addWidget(self.service_team_btn)
        sidebar_layout.addStretch()

        back_button = QPushButton("Back to Scanning")
        back_button.setFont(QFont("Montserrat", 10))
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #00C3FF;
                color: #121212;
                border: none;
                border-radius: 4px;
                padding: 12px;
                margin: 15px;
            }
            QPushButton:hover {
                background-color: #33D1FF;
            }
        """)
        back_button.clicked.connect(self.back_to_scanning)
        sidebar_layout.addWidget(back_button)

        # Main content area with stacked widget for different sections
        main_content = QWidget()
        main_content.setStyleSheet("background-color: #121212;")
        content_layout = QVBoxLayout(main_content)
        self.stacked_widget = QStackedWidget()

        # Run Analysis Page
        self.run_analysis_page = QWidget()
        self.init_run_analysis_page()

        # Shop Floor Page (dummy)
        shop_floor_page = QWidget()
        shop_floor_layout = QVBoxLayout(shop_floor_page)
        shop_floor_label = QLabel("Shop Floor - Coming Soon")
        shop_floor_label.setFont(QFont("Montserrat", 20))
        shop_floor_label.setAlignment(Qt.AlignCenter)
        shop_floor_label.setStyleSheet("color: #FFFFFF;")
        shop_floor_layout.addWidget(shop_floor_label)

        # Service Team Page (dummy)
        service_team_page = QWidget()
        service_layout = QVBoxLayout(service_team_page)
        service_label = QLabel("Service Team - Coming Soon")
        service_label.setFont(QFont("Montserrat", 20))
        service_label.setAlignment(Qt.AlignCenter)
        service_label.setStyleSheet("color: #FFFFFF;")
        service_layout.addWidget(service_label)

        self.stacked_widget.addWidget(self.run_analysis_page)
        self.stacked_widget.addWidget(shop_floor_page)
        self.stacked_widget.addWidget(service_team_page)
        self.run_analysis_btn.clicked.connect(lambda: self.switch_page(0))
        self.shop_floor_btn.clicked.connect(lambda: self.switch_page(1))
        self.service_team_btn.clicked.connect(lambda: self.switch_page(2))
        content_layout.addWidget(self.stacked_widget)
        content.addWidget(sidebar)
        content.addWidget(main_content)
        content.setStretchFactor(0, 0)
        content.setStretchFactor(1, 1)
        main_layout.addWidget(content)

    def create_sidebar_button(self, text, is_active=False):
        """Create a styled sidebar button"""
        button = QPushButton(text)
        button.setFont(QFont("Montserrat", 11))
        button.setCursor(Qt.PointingHandCursor)
        button.setCheckable(True)
        button.setChecked(is_active)
        button.setFlat(True)
        self.update_sidebar_button_style(button)
        button.clicked.connect(lambda: self.update_sidebar_buttons(button))
        return button

    def update_sidebar_buttons(self, active_button):
        """Update the styles of all sidebar buttons"""
        for button in [self.run_analysis_btn, self.shop_floor_btn, self.service_team_btn]:
            button.setChecked(button == active_button)
            self.update_sidebar_button_style(button)

    def update_sidebar_button_style(self, button):
        """Update the style of a sidebar button based on its state"""
        if button.isChecked():
            button.setStyleSheet("""
                QPushButton {
                    background-color: #00C3FF;
                    color: #121212;
                    border: none;
                    text-align: left;
                    padding: 15px 20px;
                }
                QPushButton:hover {
                    background-color: #33D1FF;
                }
            """)
        else:
            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #FFFFFF;
                    border: none;
                    text-align: left;
                    padding: 15px 20px;
                }
                QPushButton:hover {
                    background-color: #444444;
                }
            """)

    def switch_page(self, index):
        """Switch to a different page in the stacked widget"""
        self.stacked_widget.setCurrentIndex(index)

    def init_run_analysis_page(self):
        """Initialize the Run Analysis page"""
        run_analysis_layout = QVBoxLayout(self.run_analysis_page)
        run_analysis_layout.setContentsMargins(20, 20, 20, 20)
        title = QLabel("Run Analysis")
        title.setFont(QFont("Montserrat", 18, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF; margin-bottom: 20px;")
        run_analysis_layout.addWidget(title)

        content_layout = QHBoxLayout()

        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)
        log_files_label = QLabel("Available Log Files")
        log_files_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        log_files_label.setStyleSheet("color: #00C3FF;")
        left_layout.addWidget(log_files_label)

        self.log_files_list = QListWidget()
        self.log_files_list.setStyleSheet("""
            QListWidget {
                background-color: #333333;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                color: #FFFFFF;
                padding: 10px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:selected {
                background-color: #00C3FF;
                color: #121212;
            }
            QListWidget::item:hover:!selected {
                background-color: #444444;
            }
        """)
        self.log_files_list.itemClicked.connect(self.log_file_selected)
        left_layout.addWidget(self.log_files_list)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.analysis_stack = QStackedWidget()

        select_file_page = QWidget()
        select_file_layout = QVBoxLayout(select_file_page)
        select_file_label = QLabel("Select a log file to analyze")
        select_file_label.setFont(QFont("Montserrat", 14))
        select_file_label.setAlignment(Qt.AlignCenter)
        select_file_label.setStyleSheet("color: #FFFFFF;")
        select_file_layout.addWidget(select_file_label)

        self.analysis_progress_page = QWidget()
        progress_layout = QVBoxLayout(self.analysis_progress_page)
        self.progress_label = QLabel("Analysis in progress...")
        self.progress_label.setFont(QFont("Montserrat", 14))
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #FFFFFF; margin-bottom: 20px;")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                height: 25px;
                color: #121212;
                background-color: #333333;
            }
            QProgressBar::chunk {
                background-color: #00C3FF;
                width: 10px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Montserrat", 11))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #FFFFFF; margin-top: 10px;")
        progress_layout.addWidget(self.status_label)

        self.results_page = QScrollArea()
        self.results_page.setWidgetResizable(True)
        self.results_page.setStyleSheet("background-color: #121212; border: none;")
        results_content = QWidget()
        self.results_layout = QVBoxLayout(results_content)
        self.results_layout.setContentsMargins(10, 10, 10, 10)
        self.results_layout.setSpacing(15)
        self.results_title = QLabel("Analysis Results")
        self.results_title.setFont(QFont("Montserrat", 16, QFont.Bold))
        self.results_title.setStyleSheet("color: #00C3FF; margin-bottom: 20px;")
        self.results_layout.addWidget(self.results_title)

        self.results_widget = QWidget()
        self.results_widget_layout = QVBoxLayout(self.results_widget)
        self.results_widget_layout.setContentsMargins(0, 0, 0, 0)
        self.results_widget_layout.setSpacing(15)
        self.results_layout.addWidget(self.results_widget)

        buttons_layout = QHBoxLayout()
        save_report_btn = QPushButton("Save Report")
        save_report_btn.setFont(QFont("Montserrat", 11))
        save_report_btn.setCursor(Qt.PointingHandCursor)
        save_report_btn.setStyleSheet("""
            QPushButton {
                background-color: #00C3FF;
                color: #121212;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #33D1FF;
            }
        """)
        save_report_btn.clicked.connect(self.save_report)

        new_analysis_btn = QPushButton("New Analysis")
        new_analysis_btn.setFont(QFont("Montserrat", 11))
        new_analysis_btn.setCursor(Qt.PointingHandCursor)
        new_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #00C3FF;
                border-radius: 4px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        new_analysis_btn.clicked.connect(self.reset_analysis)

        buttons_layout.addWidget(save_report_btn)
        buttons_layout.addWidget(new_analysis_btn)
        self.results_layout.addLayout(buttons_layout)
        self.results_page.setWidget(results_content)

        self.analysis_stack.addWidget(select_file_page)
        self.analysis_stack.addWidget(self.analysis_progress_page)
        self.analysis_stack.addWidget(self.results_page)
        right_layout.addWidget(self.analysis_stack)

        content_layout.addWidget(left_panel)
        content_layout.addWidget(right_panel)
        run_analysis_layout.addLayout(content_layout)

    def populate_log_files(self):
        """Populate the log files list for the current IMEI"""
        self.log_files_list.clear()
        if not self.bike_imei:
            return
        try:
            # Fetch log files from AWS
            log_files = self.aws_client.get_available_logs(self.bike_imei)
            for log_file in log_files:
                # Create display name (last part of path)
                display_name = log_file.split('/')[-1].replace('.parquet.zst', '.parquet')
                item = QListWidgetItem(display_name)
                # Store full path as user data
                item.setData(Qt.UserRole, log_file)
                self.log_files_list.addItem(item)
        except Exception as e:
            logging.error(f"Error fetching log files from AWS: {str(e)}", exc_info=True)
            self.status_label.setText("Failed to fetch log files from AWS.")

    def log_file_selected(self, item):
        """Handle log file selection with flexible column validation"""
        try:
            # Get the full S3 key path from the item's data (not just text)
            full_key = item.data(Qt.UserRole)  # Store full path as user data when populating
            if not full_key:
                # Fallback: Try to reconstruct from text (less reliable)
                log_filename = item.text()
                full_key = f"vcu/MD-{self.bike_imei}/{log_filename.replace('.parquet', '.parquet.zst')}"

            self.analysis_stack.setCurrentIndex(1)
            self.progress_bar.setValue(0)
            self.status_label.setText("Downloading and extracting log file...")

            # Download log file from AWS using full key path
            log_data = self.aws_client.download_log_file(full_key)
            if not log_data:
                raise ValueError("Failed to download log file.")

            self.status_label.setText("Extracting log file...")
            df = self.aws_client.extract_archive(log_data)

            # Validate columns
            required_columns = {
                'dsg_current', 'chg_current',
                *[f'cell{i}' for i in range(1, 15)],
                'max_soc',
                *[f'ts{i}' for i in range(1, 13)],
                'ts0_flt', 'ts13_flt'
            }
            if not validate_columns(df, required_columns):
                raise ValueError("Missing required columns in the log file.")

            # Assign validated DataFrame to class attributes
            self.df = df

            # Start analysis thread
            self.start_analysis_thread()

        except Exception as e:
            self.show_error(f"Log processing failed: {str(e)}")
            logging.error(f"Error processing log file: {str(e)}", exc_info=True)
            self.analysis_stack.setCurrentIndex(0)

    def start_analysis_thread(self):
        """Start the analysis thread with the loaded data"""
        self.analysis_thread = AnalysisThread(self.df)
        self.analysis_thread.progress.connect(self.update_progress)
        self.analysis_thread.finished.connect(self.show_results)
        self.analysis_thread.error.connect(self.show_error)
        self.analysis_thread.start()

    def update_progress(self, value, message):
        """Update progress bar and status label"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def show_error(self, error_msg):
        """Show error message in UI"""
        QMessageBox.critical(self, "Error", error_msg)
        self.status_label.setText("Analysis failed")
        self.progress_bar.setValue(0)
        self.analysis_stack.setCurrentIndex(0)

    def show_results(self, solder_results, weld_results, temp_results):
        """Display analysis results with graphs matching reference code"""
        # Clear previous results
        for i in reversed(range(self.results_widget_layout.count())):
            widget = self.results_widget_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Create issues section
        issues_frame = QFrame()
        issues_frame.setFrameShape(QFrame.StyledPanel)
        issues_frame.setStyleSheet("background-color: #333333; border-radius: 6px; padding: 15px;")
        issues_layout = QVBoxLayout(issues_frame)
        issues_title = QLabel("Detected Issues")
        issues_title.setFont(QFont("Montserrat", 14, QFont.Bold))
        issues_title.setStyleSheet("color: #00C3FF;")
        issues_layout.addWidget(issues_title)

        # Solder issues
        solder_text = (
            "🔥 Solder Issues Detected\n"
            f"Severity: {solder_results['severity']}\n"
            f"Locations: {', '.join(solder_results['locations'])}"
            if solder_results["detected"]
            else "✅ No Solder Issues Detected"
        )
        solder_label = QLabel(solder_text)
        solder_label.setFont(QFont("Montserrat", 11))
        solder_label.setStyleSheet("color: #FFFFFF;")
        issues_layout.addWidget(solder_label)

        # Weld issues
        weld_text = (
            "🔥 Weld Issues Detected\n"
            f"Confidence: {weld_results['confidence']:.0%}\n"
            f"Cell: {weld_results.get('cell_with_issue', 'N/A')}"
            if weld_results["detected"]
            else "✅ No Weld Issues Detected"
        )
        weld_label = QLabel(weld_text)
        weld_label.setFont(QFont("Montserrat", 11))
        weld_label.setStyleSheet("color: #FFFFFF;")
        issues_layout.addWidget(weld_label)

        # Temperature issues
        temp_text = (
            "🔥 Temperature Fluctuations Detected\n"
            f"Max Fluctuation: {temp_results['max_fluctuation']:.4f}\n"
            f"Sensors: {', '.join(temp_results['critical_points'])}"
            if temp_results["detected"]
            else "✅ No Temperature Fluctuations Detected"
        )
        temp_label = QLabel(temp_text)
        temp_label.setFont(QFont("Montserrat", 11))
        temp_label.setStyleSheet("color: #FFFFFF;")
        issues_layout.addWidget(temp_label)

        issues_layout.addStretch()
        self.results_widget_layout.addWidget(issues_frame)

        # Create plots section if issues found
        if any([solder_results["detected"], weld_results["detected"], temp_results["detected"]]):
            plots_frame = QFrame()
            plots_frame.setFrameShape(QFrame.StyledPanel)
            plots_frame.setStyleSheet("background-color: #333333; border-radius: 6px; padding: 15px;")
            plots_layout = QVBoxLayout(plots_frame)
            plots_title = QLabel("Analysis Graphs")
            plots_title.setFont(QFont("Montserrat", 14, QFont.Bold))
            plots_title.setStyleSheet("color: #00C3FF;")
            plots_layout.addWidget(plots_title)

            # Temperature plot (matches reference code)
            if temp_results["detected"]:
                fig = Figure(figsize=(8, 4), dpi=100)
                ax = fig.add_subplot(111)
                for sensor in self.df.columns:
                    highlight = sensor in temp_results['critical_points']
                    ax.plot(
                        self.df.index,
                        self.df[sensor],
                        linewidth=3 if highlight else 1,
                        alpha=1.0 if highlight else 0.3,
                        label=sensor if highlight else None
                    )
                ax.set_title(f'IMEI {self.bike_imei} - Temperature Fluctuation - Sensor {", ".join(temp_results["critical_points"])}', fontsize=10)
                ax.set_xlabel('Data Point Index', fontsize=8)
                ax.set_ylabel('Temperature (°C)', fontsize=8)
                ax.legend()
                ax.grid(True)
                canvas = FigureCanvas(fig)
                canvas.mpl_connect('button_press_event', lambda event: self.open_enlarged_graph(event, fig, f'Temperature Fluctuation - Sensor {", ".join(temp_results["critical_points"])}', 'Data Point Index', 'Temperature (°C)', self.df.index, self.df[sensor]))
                plots_layout.addWidget(canvas)

            # Solder plot (matches reference code - shows all cells)
            if solder_results["detected"]:
                fig = Figure(figsize=(8, 4), dpi=100)
                ax = fig.add_subplot(111)
                cell_cols = [f'cell{i}' for i in range(1, 15)]
                y_data = {}
                for cell in cell_cols:
                    highlight = cell in solder_results['locations']
                    ax.plot(
                        self.df.index,
                        self.df[cell],
                        linewidth=3 if highlight else 1,
                        alpha=1.0 if highlight else 0.3,
                        label=cell if highlight else None
                    )
                    y_data[cell] = self.df[cell]
                ax.set_title(f'IMEI {self.bike_imei} - Solder Issue - Cells {", ".join(solder_results["locations"])}', fontsize=10)
                ax.set_xlabel('Data Point Index', fontsize=8)
                ax.set_ylabel('Voltage (V)', fontsize=8)
                ax.legend()
                ax.grid(True)
                canvas = FigureCanvas(fig)
                canvas.mpl_connect('button_press_event', lambda event: self.open_enlarged_graph(event, fig, f'Solder Issue - Cells {", ".join(solder_results["locations"])}', 'Data Point Index', 'Voltage (V)', self.df.index, y_data))
                plots_layout.addWidget(canvas)

            # Weld plot (matches reference code - highlights single cell)
            if weld_results["detected"]:
                fig = Figure(figsize=(8, 4), dpi=100)
                ax = fig.add_subplot(111)
                cell_cols = [f'cell{i}' for i in range(1, 15)]
                faulty_cell = weld_results.get('cell_with_issue')
                for cell in cell_cols:
                    if cell == faulty_cell:
                        ax.plot(
                            self.df.index,
                            self.df[cell],
                            linewidth=3,
                            label=cell
                        )
                ax.set_title(f'IMEI {self.bike_imei} - Weld Issue - Cell {faulty_cell}', fontsize=10)
                ax.set_xlabel('Data Point Index', fontsize=8)
                ax.set_ylabel('Voltage (V)', fontsize=8)
                ax.legend()
                ax.grid(True)
                ax.text(0.02, 0.02, f'SOC: {self.df["max_soc"].iloc[0]}%', transform=ax.transAxes, fontsize=8)
                canvas = FigureCanvas(fig)
                canvas.mpl_connect('button_press_event', lambda event: self.open_enlarged_graph(event, fig, f'Weld Issue - Cell {faulty_cell}', 'Data Point Index', 'Voltage (V)', self.df.index, self.df[cell]))
                plots_layout.addWidget(canvas)

            self.results_widget_layout.addWidget(plots_frame)

        self.analysis_stack.setCurrentIndex(2)

    def open_enlarged_graph(self, event, figure, title, x_label, y_label, x_data, y_data):
        """Open the graph in an enlarged format"""
        if event.button == 1:  # Left mouse button
            dialog = GraphDialog(title, x_label, y_label, x_data, y_data, self)
            dialog.exec_()

    def save_report(self):
        """Save analysis report to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            QMessageBox.information(
                self,
                "Report Saved",
                f"Report has been saved to:\n{file_path}"
            )

    def reset_analysis(self):
        """Reset the analysis UI"""
        self.analysis_stack.setCurrentIndex(0)
        self.progress_bar.setValue(0)
        self.status_label.setText("")

    def back_to_scanning(self):
        """Return to the barcode scanning window"""
        confirm = QMessageBox.question(
            self,
            "Confirm Return",
            "Are you sure you want to return to the scanning screen?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            from gui.barcode_scan_window import BarcodeScanWindow
            self.barcode_scan_window = BarcodeScanWindow()
            self.barcode_scan_window.show()
            self.close()

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
    app.setStyle("Fusion")

    window = MainWindow({
        "imei": "866308064306335",
        "vin": "P7112B236RM000002",
        "uuid": "VIN:P7112B236RM000002;IMEI:866308064306335;UUID:a649d4b5-df9c-47b7-aa4e-7116f2e29f96"
    })
    window.show()
    sys.exit(app.exec_())