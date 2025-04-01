import sys
import os
import time
from datetime import datetime
import pandas as pd
import py7zr
import io
from dotenv import load_dotenv
import certifi
print(certifi.where())
# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
    QSplitter, QGridLayout, QFrame, QStackedWidget, QListWidget, QProgressBar, QScrollArea
)
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
# Matplotlib imports for graph embedding
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Add the root directory to sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Points to the root directory (bike_os)
sys.path.append(base_dir)

# Import the AWSClient class from custom_aws_client
from custom_aws_client import AWSClient

# Import analysis functions after adding parent_dir to sys.path
from analysis.run_analysis import solder_issue_detection, weld_issue_detection, temp_fluctuation_detection

# Construct the path to the .env file
env_file_path = os.path.join(base_dir, ".env")

# Load environment variables from the .env file
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)


class MainWindow(QMainWindow):  # Replace with the actual class name
    def __init__(self, scanned_data=None):
        super().__init__()
        # Initialize scanned data
        self.scanned_data = scanned_data or {}
        self.bike_imei = self.scanned_data.get('imei', None)
        self.bike_vin = self.scanned_data.get('vin', None)
        self.bike_uuid = self.scanned_data.get('uuid', None)
        # Debug: Print received scanned data
        print(f"Received scanned data: {self.scanned_data}")
        # Load AWS credentials and bucket name from environment variables
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("BUCKET_NAME", "vehiclelogs.ultraviolette.com")  # Default bucket name
        # Initialize AWS client
        try:
            self.aws_client = AWSClient(self.access_key, self.secret_key, self.bucket_name)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize AWS client: {e}")
        # Initialize bike details
        self.bike_details = {}
        # Ultraviolette brand colors
        self.uv_blue = "#00C3FF"  # Electric blue accent
        self.uv_dark = "#121212"  # Dark background
        self.uv_light = "#FFFFFF"  # White text
        self.uv_gray = "#333333"  # Secondary dark
        # Setup window
        self.setWindowTitle("Ultraviolette Dashboard")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        self.setWindowIcon(QIcon("assets/small_icon.PNG"))
        self.apply_dark_theme()
        # Initialize UI
        self.init_ui()
        # Populate log files for the current IMEI
        self.populate_log_files()
        # Load bike details if IMEI is available
        if self.bike_imei:
            self.load_bike_details()
            self.update_ui_with_bike_details()

    def apply_dark_theme(self):
        """Apply Ultraviolette's dark theme to the main window"""
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

    def load_bike_details(self):
        """Load bike details from Excel file by matching VIN/IMEI"""
        # In real implementation, read from Excel file
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

    def update_ui_with_bike_details(self):
        """Update the UI with the bike details"""
        self.bike_info_label.setText(f"{self.bike_details.get('make', 'Ultraviolette')} {self.bike_details.get('model', 'F77')} | IMEI: {self.bike_imei}")
        self.update_bike_details_sidebar()

    def update_bike_details_sidebar(self):
        """Update the bike details in the sidebar"""
        for i in reversed(range(self.details_grid.count())):
            self.details_grid.itemAt(i).widget().setParent(None)
        row = 0
        for label, key in [
            ("VIN:", "vin"),
            ("IMEI:", "imei"),
            ("Model:", "model"),
            ("Year:", "year"),
            ("Color:", "color")
        ]:
            label_widget = QLabel(label)
            label_widget.setFont(QFont("Montserrat", 9, QFont.Bold))
            label_widget.setStyleSheet(f"color: {self.uv_light};")
            value_widget = QLabel(self.bike_details.get(key, "N/A"))
            value_widget.setFont(QFont("Montserrat", 9))
            value_widget.setStyleSheet(f"color: {self.uv_light};")
            self.details_grid.addWidget(label_widget, row, 0)
            self.details_grid.addWidget(value_widget, row, 1)
            row += 1

    def init_ui(self):
        """Initialize the main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with logo and logout button
        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet(f"background-color: {self.uv_dark}; border-bottom: 1px solid #444;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/ultraviolette_automotive_logo.jpg")
        logo_label.setPixmap(logo_pixmap.scaled(150, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Bike details summary
        self.bike_info_label = QLabel(f"{self.bike_details.get('make', 'Ultraviolette')} {self.bike_details.get('model', 'F77')} | IMEI: {self.bike_imei}")
        self.bike_info_label.setFont(QFont("Montserrat", 10))
        self.bike_info_label.setStyleSheet(f"color: {self.uv_light};")

        # Logout button
        logout_button = QPushButton("Logout")
        logout_button.setFont(QFont("Montserrat", 10))
        logout_button.setCursor(Qt.PointingHandCursor)
        logout_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.uv_light};
                border: 1px solid {self.uv_blue};
                border-radius: 4px;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
            }}
        """)
        logout_button.clicked.connect(self.logout)

        # Add widgets to header
        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        header_layout.addWidget(self.bike_info_label)
        header_layout.addStretch()
        header_layout.addWidget(logout_button)

        # Add header to main layout
        main_layout.addWidget(header)

        # Content area with sidebar and main content
        content = QSplitter(Qt.Horizontal)

        # Sidebar
        sidebar = QWidget()
        sidebar.setMinimumWidth(250)
        sidebar.setMaximumWidth(300)
        sidebar.setStyleSheet(f"background-color: {self.uv_gray};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Bike details at top of sidebar
        bike_details_widget = QWidget()
        bike_details_widget.setStyleSheet(f"background-color: {self.uv_gray}; padding: 15px;")
        bike_details_layout = QVBoxLayout(bike_details_widget)
        title_label = QLabel("Bike Details")
        title_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        title_label.setStyleSheet(f"color: {self.uv_blue};")
        bike_details_layout.addWidget(title_label)

        # Create grid for bike details
        self.details_grid = QGridLayout()
        self.details_grid.setHorizontalSpacing(10)
        self.details_grid.setVerticalSpacing(8)
        row = 0
        for label, key in [
            ("VIN:", "vin"),
            ("IMEI:", "imei"),
            ("Model:", "model"),
            ("Year:", "year"),
            ("Color:", "color")
        ]:
            label_widget = QLabel(label)
            label_widget.setFont(QFont("Montserrat", 9, QFont.Bold))
            label_widget.setStyleSheet(f"color: {self.uv_light};")
            value_widget = QLabel(self.bike_details.get(key, "N/A"))
            value_widget.setFont(QFont("Montserrat", 9))
            value_widget.setStyleSheet(f"color: {self.uv_light};")
            self.details_grid.addWidget(label_widget, row, 0)
            self.details_grid.addWidget(value_widget, row, 1)
            row += 1
        bike_details_layout.addLayout(self.details_grid)
        sidebar_layout.addWidget(bike_details_widget)

        # Separator
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

        # Add spacer at bottom of sidebar
        sidebar_layout.addStretch()

        # Back to scanning button
        back_button = QPushButton("Back to Scanning")
        back_button.setFont(QFont("Montserrat", 10))
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
                border: none;
                border-radius: 4px;
                padding: 12px;
                margin: 15px;
            }}
            QPushButton:hover {{
                background-color: #33D1FF;
            }}
        """)
        back_button.clicked.connect(self.back_to_scanning)
        sidebar_layout.addWidget(back_button)

        # Main content area with stacked widget for different sections
        main_content = QWidget()
        main_content.setStyleSheet(f"background-color: {self.uv_dark};")
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
        shop_floor_label.setStyleSheet(f"color: {self.uv_light};")
        shop_floor_layout.addWidget(shop_floor_label)

        # Service Team Page (dummy)
        service_team_page = QWidget()
        service_layout = QVBoxLayout(service_team_page)
        service_label = QLabel("Service Team - Coming Soon")
        service_label.setFont(QFont("Montserrat", 20))
        service_label.setAlignment(Qt.AlignCenter)
        service_label.setStyleSheet(f"color: {self.uv_light};")
        service_layout.addWidget(service_label)

        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.run_analysis_page)
        self.stacked_widget.addWidget(shop_floor_page)
        self.stacked_widget.addWidget(service_team_page)

        # Connect buttons to switch pages
        self.run_analysis_btn.clicked.connect(lambda: self.switch_page(0))
        self.shop_floor_btn.clicked.connect(lambda: self.switch_page(1))
        self.service_team_btn.clicked.connect(lambda: self.switch_page(2))

        content_layout.addWidget(self.stacked_widget)

        # Add sidebar and main content to splitter
        content.addWidget(sidebar)
        content.addWidget(main_content)
        content.setStretchFactor(0, 0)  # Sidebar doesn't stretch
        content.setStretchFactor(1, 1)  # Main content stretches

        # Add splitter to main layout
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
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.uv_blue};
                    color: {self.uv_dark};
                    border: none;
                    text-align: left;
                    padding: 15px 20px;
                }}
                QPushButton:hover {{
                    background-color: #33D1FF;
                }}
            """)
        else:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {self.uv_light};
                    border: none;
                    text-align: left;
                    padding: 15px 20px;
                }}
                QPushButton:hover {{
                    background-color: #444444;
                }}
            """)

    def switch_page(self, index):
        """Switch to a different page in the stacked widget"""
        self.stacked_widget.setCurrentIndex(index)

    def init_run_analysis_page(self):
        """Initialize the Run Analysis page"""
        run_analysis_layout = QVBoxLayout(self.run_analysis_page)
        run_analysis_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Run Analysis")
        title.setFont(QFont("Montserrat", 18, QFont.Bold))
        title.setStyleSheet(f"color: {self.uv_light}; margin-bottom: 20px;")
        run_analysis_layout.addWidget(title)

        # Main content with log files and analysis
        content_layout = QHBoxLayout()

        # Left panel - Log files list
        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)

        # Log files label
        log_files_label = QLabel("Available Log Files")
        log_files_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        log_files_label.setStyleSheet(f"color: {self.uv_blue};")
        left_layout.addWidget(log_files_label)

        # List of log files
        self.log_files_list = QListWidget()
        self.log_files_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.uv_gray};
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
            }}
            QListWidget::item {{
                color: {self.uv_light};
                padding: 10px;
                border-bottom: 1px solid #444;
            }}
            QListWidget::item:selected {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
            }}
            QListWidget::item:hover:!selected {{
                background-color: #444444;
            }}
        """)
        self.log_files_list.itemClicked.connect(self.log_file_selected)
        left_layout.addWidget(self.log_files_list)

        # Right panel - Analysis area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Analysis content with stacked widget
        self.analysis_stack = QStackedWidget()

        # Initial page - Select a log file
        select_file_page = QWidget()
        select_file_layout = QVBoxLayout(select_file_page)
        select_file_label = QLabel("Select a log file to analyze")
        select_file_label.setFont(QFont("Montserrat", 14))
        select_file_label.setAlignment(Qt.AlignCenter)
        select_file_label.setStyleSheet(f"color: {self.uv_light};")
        select_file_layout.addWidget(select_file_label)

        # Analysis in progress page
        self.analysis_progress_page = QWidget()
        progress_layout = QVBoxLayout(self.analysis_progress_page)
        self.progress_label = QLabel("Analysis in progress...")
        self.progress_label.setFont(QFont("Montserrat", 14))
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet(f"color: {self.uv_light}; margin-bottom: 20px;")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                height: 25px;
                color: {self.uv_dark};
                background-color: {self.uv_gray};
            }}
            QProgressBar::chunk {{
                background-color: {self.uv_blue};
                width: 10px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Montserrat", 11))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {self.uv_light}; margin-top: 10px;")
        progress_layout.addWidget(self.status_label)

        # Results page
        self.results_page = QScrollArea()
        self.results_page.setWidgetResizable(True)
        self.results_page.setStyleSheet(f"background-color: {self.uv_dark}; border: none;")
        results_content = QWidget()
        self.results_layout = QVBoxLayout(results_content)

        # Results title
        self.results_title = QLabel("Analysis Results")
        self.results_title.setFont(QFont("Montserrat", 16, QFont.Bold))
        self.results_title.setStyleSheet(f"color: {self.uv_blue}; margin-bottom: 20px;")
        self.results_layout.addWidget(self.results_title)

        # Results widget
        self.results_widget = QWidget()
        self.results_widget_layout = QVBoxLayout(self.results_widget)
        self.results_layout.addWidget(self.results_widget)

        # Buttons for saving report
        buttons_layout = QHBoxLayout()
        save_report_btn = QPushButton("Save Report")
        save_report_btn.setFont(QFont("Montserrat", 11))
        save_report_btn.setCursor(Qt.PointingHandCursor)
        save_report_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_blue};
                color: {self.uv_dark};
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: #33D1FF;
            }}
        """)
        save_report_btn.clicked.connect(self.save_report)

        new_analysis_btn = QPushButton("New Analysis")
        new_analysis_btn.setFont(QFont("Montserrat", 11))
        new_analysis_btn.setCursor(Qt.PointingHandCursor)
        new_analysis_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.uv_gray};
                color: {self.uv_light};
                border: 1px solid {self.uv_blue};
                border-radius: 4px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: #444444;
            }}
        """)
        new_analysis_btn.clicked.connect(self.reset_analysis)

        buttons_layout.addWidget(save_report_btn)
        buttons_layout.addWidget(new_analysis_btn)
        self.results_layout.addLayout(buttons_layout)

        self.results_page.setWidget(results_content)

        # Add pages to analysis stack
        self.analysis_stack.addWidget(select_file_page)
        self.analysis_stack.addWidget(self.analysis_progress_page)
        self.analysis_stack.addWidget(self.results_page)

        right_layout.addWidget(self.analysis_stack)

        # Add panels to content layout
        content_layout.addWidget(left_panel)
        content_layout.addWidget(right_panel)

        run_analysis_layout.addLayout(content_layout)

    def populate_log_files(self):
        """Populate the log files list for the current IMEI"""
        self.log_files_list.clear()
        if not self.bike_imei:
            return

        # Get available logs from AWS
        log_files = self.aws_client.get_available_logs(self.bike_imei)
        processed_logs = self.load_processed_logs()

        for log_file in log_files:
            if log_file not in processed_logs:
                item = QListWidgetItem(log_file)

                # Add icon based on log type
                if "diagnostic" in log_file:
                    item.setIcon(QIcon("assets/diagnostic_icon.png"))
                elif "performance" in log_file:
                    item.setIcon(QIcon("assets/performance_icon.png"))
                elif "error" in log_file:
                    item.setIcon(QIcon("assets/error_icon.png"))
                elif "temperature" in log_file:
                    item.setIcon(QIcon("assets/temperature_icon.png"))
                elif "battery" in log_file:
                    item.setIcon(QIcon("assets/battery_icon.png"))
                else:
                    item.setIcon(QIcon("assets/log_icon.png"))

                self.log_files_list.addItem(item)

    def load_processed_logs(self):
        """Load the list of processed log files for the current IMEI."""
        processed_logs_file = os.path.join(base_dir, f"processed_logs_{self.bike_imei}.txt")
        if os.path.exists(processed_logs_file):
            with open(processed_logs_file, "r") as f:
                return set(line.strip() for line in f)
        return set()

    def save_processed_log(self, log_path):
        """Save a processed log file for the current IMEI."""
        processed_logs_file = os.path.join(base_dir, f"processed_logs_{self.bike_imei}.txt")
        with open(processed_logs_file, "a") as f:
            f.write(f"{log_path}\n")

    def log_file_selected(self, item):
        """Handle log file selection"""
        log_filename = item.text()

        # Reset UI to analysis progress page
        self.analysis_stack.setCurrentIndex(1)
        self.progress_bar.setValue(0)
        self.status_label.setText("Downloading log file...")

        # Download the selected log file
        log_data = self.aws_client.download_log_file(self.bike_imei, log_filename)

        if log_data:
            self.status_label.setText("Extracting log file...")
            try:
                extracted_files = self.aws_client.extract_archive(io.BytesIO(log_data))

                # Validate required files
                required_files = {"pack0_log_emcm.csv", "pack0_log_fgaux.csv", "pack0_log_ts.csv"}
                if not required_files.issubset(extracted_files.keys()):
                    raise ValueError("Missing required files in archive.")

                # Convert extracted files to DataFrames
                emcm_df = pd.read_csv(io.BytesIO(extracted_files["pack0_log_emcm.csv"]))
                fgaux_df = pd.read_csv(io.BytesIO(extracted_files["pack0_log_fgaux.csv"]))
                ts_df = pd.read_csv(io.BytesIO(extracted_files["pack0_log_ts.csv"]))

                # Start analysis thread
                self.analysis_thread = AnalysisThread(self.bike_imei, log_data)
                self.analysis_thread.progress_updated.connect(self.update_progress)
                self.analysis_thread.analysis_complete.connect(self.show_results)
                self.analysis_thread.start()

                # Save the processed log file
                self.save_processed_log(log_filename)
            except Exception as e:
                print(f"Error processing log file: {e}")
                self.status_label.setText("Error processing log file.")
        else:
            self.status_label.setText("Failed to download log file.")

    def update_progress(self, value, status):
        """Update the progress bar and status label"""
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def show_results(self, analysis_results, plot_data):
        """Display analysis results"""
        # Clear previous results
        for i in reversed(range(self.results_widget_layout.count())):
            self.results_widget_layout.itemAt(i).widget().setParent(None)

        # Create new results widgets
        self.create_summary_section(analysis_results)
        self.create_issues_section(analysis_results)
        self.create_plots_section(plot_data)

        # Switch to results page
        self.analysis_stack.setCurrentIndex(2)

    def create_summary_section(self, results):
        """Create the summary section of the results"""
        summary_frame = QFrame()
        summary_frame.setFrameShape(QFrame.StyledPanel)
        summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 6px;
                padding: 15px;
            }}
        """)
        summary_layout = QVBoxLayout(summary_frame)

        # Summary title
        summary_title = QLabel("Overall Summary")
        summary_title.setFont(QFont("Montserrat", 14, QFont.Bold))
        summary_title.setStyleSheet(f"color: {self.uv_light};")
        summary_layout.addWidget(summary_title)

        # Health score
        health_score = results.get('overall_health', {}).get('score', 0)
        score_color = "#4CAF50" if health_score >= 80 else "#FFC107" if health_score >= 60 else "#F44336"
        health_layout = QHBoxLayout()
        health_label = QLabel("Health Score:")
        health_label.setFont(QFont("Montserrat", 12))
        health_label.setStyleSheet(f"color: {self.uv_light};")
        health_value = QLabel(f"{health_score}%")
        health_value.setFont(QFont("Montserrat", 24, QFont.Bold))
        health_value.setStyleSheet(f"color: {score_color};")
        health_layout.addWidget(health_label)
        health_layout.addWidget(health_value)
        health_layout.addStretch()
        summary_layout.addLayout(health_layout)

        # Issues found
        issues_found = results.get('overall_health', {}).get('issues_found', 0)
        issues_label = QLabel(f"Issues Found: {issues_found}")
        issues_label.setFont(QFont("Montserrat", 12))
        issues_label.setStyleSheet(f"color: {self.uv_light};")
        summary_layout.addWidget(issues_label)

        # Recommendation
        recommendation = results.get('overall_health', {}).get('recommendation', "No recommendation available")
        rec_label = QLabel(f"Recommendation: {recommendation}")
        rec_label.setFont(QFont("Montserrat", 12))
        rec_label.setStyleSheet(f"color: {self.uv_light};")
        rec_label.setWordWrap(True)
        summary_layout.addWidget(rec_label)

        self.results_widget_layout.addWidget(summary_frame)

    def create_issues_section(self, results):
        """Create the issues section of the results"""
        issues_frame = QFrame()
        issues_frame.setFrameShape(QFrame.StyledPanel)
        issues_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 6px;
                padding: 15px;
                margin-top: 20px;
            }}
        """)
        issues_layout = QVBoxLayout(issues_frame)

        # Issues title
        issues_title = QLabel("Detected Issues")
        issues_title.setFont(QFont("Montserrat", 14, QFont.Bold))
        issues_title.setStyleSheet(f"color: {self.uv_light};")
        issues_layout.addWidget(issues_title)

        # Solder issues
        solder_issues = results.get('solder_issues', {})
        if solder_issues.get('detected', False):
            solder_frame = self.create_issue_item(
                "Solder Issues",
                f"Severity: {solder_issues.get('severity', 'Unknown')}",
                f"Locations: {', '.join(solder_issues.get('locations', ['Unknown']))}"
            )
            issues_layout.addWidget(solder_frame)

        # Weld issues
        weld_issues = results.get('weld_issues', {})
        if weld_issues.get('detected', False):
            weld_frame = self.create_issue_item(
                "Weld Issues",
                f"Confidence: {int(weld_issues.get('confidence', 0) * 100)}%",
                ""
            )
            issues_layout.addWidget(weld_frame)

        # Temperature fluctuations
        temp_issues = results.get('temperature_fluctuations', {})
        if temp_issues.get('detected', False):
            temp_frame = self.create_issue_item(
                "Temperature Fluctuations",
                f"Max Fluctuation: {temp_issues.get('max_fluctuation', 0)}°C",
                f"Critical Points: {', '.join(map(str, temp_issues.get('critical_points', [])))}"
            )
            issues_layout.addWidget(temp_frame)

        # If no issues detected
        if not (solder_issues.get('detected', False) or
                weld_issues.get('detected', False) or
                temp_issues.get('detected', False)):
            no_issues = QLabel("No significant issues detected")
            no_issues.setFont(QFont("Montserrat", 12))
            no_issues.setStyleSheet("color: #4CAF50;")
            issues_layout.addWidget(no_issues)

        self.results_widget_layout.addWidget(issues_frame)

    def create_issue_item(self, title, detail1, detail2):
        """Create a frame for an individual issue"""
        issue_frame = QFrame()
        issue_frame.setFrameShape(QFrame.StyledPanel)
        issue_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(244, 67, 54, 0.1);
                border-left: 4px solid #F44336;
                border-radius: 4px;
                padding: 10px;
                margin: 5px 0;
            }}
        """)
        issue_layout = QVBoxLayout(issue_frame)
        issue_layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel(title)
        title_label.setFont(QFont("Montserrat", 12, QFont.Bold))
        title_label.setStyleSheet("color: #F44336;")
        issue_layout.addWidget(title_label)

        if detail1:
            detail1_label = QLabel(detail1)
            detail1_label.setFont(QFont("Montserrat", 10))
            detail1_label.setStyleSheet(f"color: {self.uv_light};")
            issue_layout.addWidget(detail1_label)

        if detail2:
            detail2_label = QLabel(detail2)
            detail2_label.setFont(QFont("Montserrat", 10))
            detail2_label.setStyleSheet(f"color: {self.uv_light};")
            issue_layout.addWidget(detail2_label)

        return issue_frame

    def create_plots_section(self, plot_data):
        """Create the plots section of the results"""
        plots_frame = QFrame()
        plots_frame.setFrameShape(QFrame.StyledPanel)
        plots_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.uv_gray};
                border-radius: 6px;
                padding: 15px;
                margin-top: 20px;
            }}
        """)
        plots_layout = QVBoxLayout(plots_frame)

        # Plots title
        plots_title = QLabel("Analysis Graphs")
        plots_title.setFont(QFont("Montserrat", 14, QFont.Bold))
        plots_title.setStyleSheet(f"color: {self.uv_light};")
        plots_layout.addWidget(plots_title)

        # Grid for plots
        plots_grid = QGridLayout()
        plots_grid.setSpacing(20)

        # Temperature plot
        if "temperature" in plot_data:
            temp_plot = self.create_plot(
                "Temperature Over Time",
                "Time (s)",
                "Temperature (°C)",
                plot_data["temperature"]["x"],
                plot_data["temperature"]["y"]
            )
            plots_grid.addWidget(temp_plot, 0, 0)

        # Voltage/Current plot
        if "voltage_current" in plot_data:
            voltage_plot = self.create_plot(
                "Voltage and Current",
                "Time (s)",
                "Voltage (V) / Current (A)",
                plot_data["voltage_current"]["x"],
                plot_data["voltage_current"]["y"]
            )
            plots_grid.addWidget(voltage_plot, 0, 1)

        plots_layout.addLayout(plots_grid)
        self.results_widget_layout.addWidget(plots_frame)

    def create_plot(self, title, x_label, y_label, x_data, y_data):
        """Create an actual plot using Matplotlib"""
        plot_frame = QFrame()
        plot_frame.setFixedHeight(200)
        plot_layout = QVBoxLayout(plot_frame)

        # Create a Matplotlib figure
        fig = Figure()
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.plot(x_data, y_data, label=y_label)
        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.legend()
        ax.grid(True)

        # Add the canvas to the layout
        plot_layout.addWidget(canvas)

        return plot_frame

    def save_report(self):
        """Save the analysis report"""
        # In a real implementation, generate a PDF or other report format
        # For now, just show a dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            QMessageBox.information(self, "Report Saved", f"Report has been saved to:\n{file_path}")

    def reset_analysis(self):
        """Reset the analysis UI to allow for new analysis"""
        self.analysis_stack.setCurrentIndex(0)  # Switch back to the log file selection page
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
            from gui.barcode_scan_window import BarcodeScanWindow  # Import dynamically to avoid circular dependency
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
            from gui.login_window import LoginWindow  # Import dynamically to avoid circular dependency
            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()


class AnalysisThread(QThread):
    """
    Thread to handle log file analysis without freezing the UI.
    """
    progress_updated = pyqtSignal(int, str)  # Signal to update progress (value, status message)
    analysis_complete = pyqtSignal(dict, dict)  # Signal to emit analysis results and plot data

    def __init__(self, imei, log_data):
        super().__init__()
        self.imei = imei
        self.log_data = log_data

    def run(self):
        try:
            # Simulate downloading and extracting the log file
            self.progress_updated.emit(10, "Extracting log file...")
            time.sleep(1)  # Simulate extraction delay

            # Load extracted data into DataFrames
            self.progress_updated.emit(30, "Loading extracted data...")
            emcm_df = pd.read_csv(io.BytesIO(self.log_data), usecols=["timestamp", "cell_voltage"])
            fgaux_df = pd.read_csv(io.BytesIO(self.log_data), usecols=["timestamp", "current"])
            ts_df = pd.read_csv(io.BytesIO(self.log_data), usecols=["timestamp", "temperature"])

            # Run analysis functions
            self.progress_updated.emit(50, "Running solder issue detection...")
            solder_results = solder_issue_detection(emcm_df, self.imei)

            self.progress_updated.emit(70, "Running weld issue detection...")
            weld_results = weld_issue_detection(emcm_df, fgaux_df, self.imei)

            self.progress_updated.emit(85, "Running temperature fluctuation detection...")
            temp_results = temp_fluctuation_detection(ts_df, self.imei)

            # Prepare plot data
            plot_data = {
                "temperature": {
                    "x": ts_df["timestamp"].values.tolist(),
                    "y": ts_df["temperature"].values.tolist()
                },
                "voltage_current": {
                    "x": emcm_df["timestamp"].values.tolist(),
                    "y": emcm_df["cell_voltage"].values.tolist()
                }
            }

            # Combine results
            analysis_results = {
                "overall_health": {
                    "score": 85,  # Example health score
                    "issues_found": len(solder_results.get("locations", [])) + weld_results.get("detected", 0),
                    "recommendation": "Perform maintenance on detected issues."
                },
                "solder_issues": solder_results,
                "weld_issues": weld_results,
                "temperature_fluctuations": temp_results
            }

            # Emit completion signal with results
            self.progress_updated.emit(100, "Analysis complete!")
            self.analysis_complete.emit(analysis_results, plot_data)

        except Exception as e:
            print(f"Error during analysis: {str(e)}")
            self.progress_updated.emit(0, "Error during analysis. Please try again.")
            self.analysis_complete.emit({}, {})


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for better dark theme support
    window = MainWindow(scanned_data={"imei": "866308064306335", "vin": "P7112B236RM000002", "uuid": "VIN:P7112B236RM000002;IMEI:866308064306335;UUID:a649d4b5-df9c-47b7-aa4e-7116f2e29f96"})
    window.show()
    sys.exit(app.exec_())