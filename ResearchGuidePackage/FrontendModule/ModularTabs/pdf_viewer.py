"""
PDF Viewer Module
================
Displays PDF files in a viewer tab with basic navigation controls.
Downloads PDF content directly from the database.
"""
import os
import logging
import tempfile
import base64
from pathlib import Path
import asyncio
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QSpinBox, QProgressBar, QMessageBox, QSplitter, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile

from ResearchGuidePackage.FrontendModule.client import APIClient

logger = logging.getLogger('PDFViewer')

class PDFViewer(QWidget):
    """Widget for displaying PDF files directly from the database."""
    
    def __init__(self, main_window):
        """Initialize PDF viewer."""
        super().__init__()
        self.main_window = main_window
        self.file_path = None
        self.node_id = None
        self.temp_file = None
        self.web_view = None
        self.loading = False  # Flag to track loading state
        self.original_file_name = "Document.pdf"  # Default fallback name
        self.current_page = 1
        self.total_pages = 1
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 5, 10, 5)
        
        # Navigation controls
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self._go_previous)
        toolbar.addWidget(self.prev_button)
        
        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self._go_next)
        toolbar.addWidget(self.next_button)
        
        # Page navigation
        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("Page:"))
        
        self.page_spinner = QSpinBox()
        self.page_spinner.setMinimum(1)
        self.page_spinner.setMaximum(999)
        self.page_spinner.setValue(1)
        self.page_spinner.valueChanged.connect(self._go_to_page)
        page_layout.addWidget(self.page_spinner)
        
        self.page_count_label = QLabel("/ 1")
        page_layout.addWidget(self.page_count_label)
        
        toolbar.addLayout(page_layout)
        toolbar.addStretch(1)  # Push remaining controls to the right
        
        # Zoom controls
        self.zoom_out_button = QPushButton("🔍-")
        self.zoom_out_button.clicked.connect(self._zoom_out)
        toolbar.addWidget(self.zoom_out_button)
        
        self.zoom_in_button = QPushButton("🔍+")
        self.zoom_in_button.clicked.connect(self._zoom_in)
        toolbar.addWidget(self.zoom_in_button)
        
        # Download button
        self.download_button = QPushButton("📥 Download")
        self.download_button.clicked.connect(self._download_pdf)
        toolbar.addWidget(self.download_button)
        
        main_layout.addLayout(toolbar)
        
        # Add a horizontal separator
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #ccc;")
        main_layout.addWidget(line)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Main content area with WebEngineView - configure for PDF viewing
        self.web_view = QWebEngineView()
        
        # Configure WebEngine settings for PDF viewing
        profile = QWebEngineProfile.defaultProfile()
        settings = self.web_view.settings()
        
        # Enable PDF viewer plugin and JavaScript
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        
        # Connect signals
        self.web_view.loadProgress.connect(self._update_load_progress)
        self.web_view.loadFinished.connect(self._load_finished)
        
        main_layout.addWidget(self.web_view, 1)  # 1 = stretch factor
        
        # Status bar
        self.status_bar = QLabel("Ready")
        self.status_bar.setStyleSheet("padding: 3px; font-size: 11px; color: #666;")
        main_layout.addWidget(self.status_bar)
    
    def setup_pdf_viewer(self, pdf_data):
        """Set up the PDF viewer with the provided data."""
        self.loading = True
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        # Get parameters from pdf_data
        self.file_path = pdf_data.get('file_path', '')
        self.node_id = pdf_data.get('node_id')
        
        if not self.node_id:
            self._show_error("No node ID provided.")
            return
        
        # Get the original filename for display
        self.original_file_name = os.path.basename(self.file_path) if self.file_path else f"node_{self.node_id}.pdf"
        
        # Always download the file from the database
        self.status_bar.setText(f"Loading {self.original_file_name}...")
        
        # Start the download process
        asyncio.create_task(self._download_and_load_pdf())
    
    async def _download_and_load_pdf(self):
        """Download the PDF file from the database and load it into the viewer."""
        try:
            # Create a temp file to store the PDF
            fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='researchguide_')
            os.close(fd)  # Close the file descriptor
            self.temp_file = temp_path
            
            # Update status
            self.status_bar.setText("Connecting to backend...")
            self.progress_bar.setValue(20)
            
            # Create communication channel
            comm = APIClient()
            
            self.status_bar.setText("Requesting file content...")
            self.progress_bar.setValue(30)
            
            # Request file content directly from the backend
            success, content, error = await comm.request_and_get_response(
                operation="get_node_file",
                params={"node_id": str(self.node_id)},
                sender="Frontend",
                timeout=60  # Longer timeout for large PDFs
            )
            
            if not success or not content or not content.get("result"):
                error_msg = error or content.get("error") or "Unknown error"
                logger.error(f"Download failed: {error_msg}")
                self._show_error(f"Unable to download PDF: {error_msg}")
                return
                
            self.status_bar.setText("Received file data, processing...")
            self.progress_bar.setValue(50)
            
            # Get file content from response
            file_content = content.get("file_content", "")
            if not file_content:
                self._show_error("Received empty file content from server")
                return
                
            # Decode base64 content
            try:
                file_bytes = base64.b64decode(file_content)
                self.progress_bar.setValue(70)
                
                # Write to temporary file
                with open(temp_path, 'wb') as f:
                    f.write(file_bytes)
                    
                self.status_bar.setText("File downloaded, preparing viewer...")
                self.progress_bar.setValue(80)
                
                # Load the file into the viewer
                self._load_file(temp_path)
                
            except Exception as e:
                logger.exception(f"Error processing file content: {e}")
                self._show_error(f"Error processing PDF file: {e}")
            
        except Exception as e:
            logger.exception(f"Error downloading PDF: {e}")
            self._show_error(f"Error downloading PDF: {e}")
    
    def _load_file(self, file_path):
        """Load the PDF file into the web view."""
        try:
            # Update status
            self.status_bar.setText(f"Loading PDF viewer...")
            
            # Convert path to URL format
            file_url = QUrl.fromLocalFile(file_path)
            
            # Load the PDF using the built-in PDF viewer
            logger.info(f"Loading PDF from URL: {file_url.toString()}")
            self.web_view.load(file_url)
            
        except Exception as e:
            logger.exception(f"Error loading PDF: {e}")
            self._show_error(f"Error loading PDF file: {e}")
    
    def _update_load_progress(self, progress):
        """Update the load progress bar."""
        if self.loading:
            # Scale progress to 80-100% range (since we already got to 80% in download)
            scaled_progress = 80 + (progress / 5)  # 20% of progress bar for loading
            self.progress_bar.setValue(int(scaled_progress))
    
    def _load_finished(self, success):
        """Handle PDF load completion."""
        self.loading = False
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_bar.setText(f"Loaded: {self.original_file_name}")
            
            # Try to get page count from PDF.js if it's being used
            self.web_view.page().runJavaScript(
                "if (typeof PDFViewerApplication !== 'undefined') { "
                "   PDFViewerApplication.pdfDocument?.numPages || 1; "
                "} else { 1; }",
                self._update_page_count
            )
        else:
            self._show_error("Failed to load PDF file.")
    
    def _update_page_count(self, count):
        """Update the page count after getting it from JavaScript."""
        try:
            if isinstance(count, (int, float)) and count > 0:
                self.total_pages = int(count)
                self.page_spinner.setMaximum(self.total_pages)
                self.page_count_label.setText(f"/ {self.total_pages}")
                logger.info(f"PDF has {self.total_pages} pages")
        except Exception as e:
            logger.warning(f"Error updating page count: {e}")
    
    def _go_previous(self):
        """Go to the previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self.page_spinner.setValue(self.current_page)
            self._navigate_to_page(self.current_page)
    
    def _go_next(self):
        """Go to the next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.page_spinner.setValue(self.current_page)
            self._navigate_to_page(self.current_page)
    
    def _go_to_page(self, page):
        """Handle page spinner value change."""
        if page != self.current_page:
            self.current_page = page
            self._navigate_to_page(page)
    
    def _navigate_to_page(self, page):
        """Navigate to a specific page using JavaScript."""
        script = (
            "if (typeof PDFViewerApplication !== 'undefined') {"
            f"    PDFViewerApplication.page = {page};"
            "}"
        )
        self.web_view.page().runJavaScript(script)
    
    def _zoom_in(self):
        """Zoom in on the PDF."""
        script = (
            "if (typeof PDFViewerApplication !== 'undefined') {"
            "    PDFViewerApplication.zoomIn();"
            "}"
        )
        self.web_view.page().runJavaScript(script)
    
    def _zoom_out(self):
        """Zoom out on the PDF."""
        script = (
            "if (typeof PDFViewerApplication !== 'undefined') {"
            "    PDFViewerApplication.zoomOut();"
            "}"
        )
        self.web_view.page().runJavaScript(script)
    
    def _download_pdf(self):
        """Download the PDF file to a user-selected location."""
        if not self.temp_file or not os.path.exists(self.temp_file):
            self._show_error("PDF file not available for download.")
            return
            
        try:
            # Let user select save location
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save PDF As", 
                self.original_file_name,
                "PDF Files (*.pdf)"
            )
            
            if save_path:
                # Copy the temporary file to the selected location
                import shutil
                shutil.copy2(self.temp_file, save_path)
                self.status_bar.setText(f"PDF saved to: {save_path}")
                
        except Exception as e:
            logger.exception(f"Error saving PDF: {e}")
            self._show_error(f"Error saving PDF: {e}")
    
    def _show_error(self, message):
        """Show an error message to the user."""
        self.loading = False
        self.progress_bar.setVisible(False)
        self.status_bar.setText(f"Error: {message}")
        logger.error(message)
        
        QMessageBox.critical(
            self,
            "PDF Viewer Error",
            message
        )
    
    def cleanup(self):
        """Clean up temporary files on tab close."""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
                logger.info(f"Removed temporary file: {self.temp_file}")
            except Exception as e:
                logger.error(f"Error removing temporary file {self.temp_file}: {e}")
    
    def get_tab_title(self):
        """Get the title for this tab."""
        if self.original_file_name:
            return self.original_file_name
        return "PDF Viewer"
    
    def refresh(self):
        """Refresh the PDF viewer."""
        if self.node_id:
            # Re-download and reload the PDF
            self.progress_bar.setVisible(True)
            self.loading = True
            asyncio.create_task(self._download_and_load_pdf())
