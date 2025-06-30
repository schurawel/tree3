"""
Transcribe Tab
=============
A tab for transcribing audio and video files to text using OpenAI Whisper offline.
"""

import os
import logging
import time
import tempfile
import subprocess
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, 
    QProgressBar, QFileDialog, QComboBox, QSplitter, QFrame, QMessageBox,
    QApplication, QStyle, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QTextCursor, QFont, QColor

from ResearchGuidePackage.FrontendModule.ModularTabs.abstract_content_tab import AbstractContentTab
import sys

# Set up logging
logger = logging.getLogger('TranscribeTab')

class TranscriptionThread(QThread):
    """Thread for running Whisper transcription without blocking the UI."""
    progress_update = pyqtSignal(int)  # Progress percentage
    status_update = pyqtSignal(str)    # Status text
    result_ready = pyqtSignal(str)     # Transcription result
    error_occurred = pyqtSignal(str)   # Error message
    generation_started = pyqtSignal()  # Signal for when generation starts
    
    def __init__(self, file_path, model_size="base", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.model_size = model_size
        self.running = True
        self.temp_audio_file = None
        self.process = None
    
    def run(self):
        """Run the transcription process in a separate Python process."""
        try:
            # Prepare the file
            self.status_update.emit("Preparing file...")
            self.progress_update.emit(5)
            
            # Extract audio if it's a video file
            file_ext = os.path.splitext(self.file_path)[1].lower()
            if file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                self.status_update.emit("Extracting audio from video...")
                self._extract_audio()
                # Use the extracted audio file
                target_file = self.temp_audio_file
            else:
                # Use the original file
                target_file = self.file_path
            
            self.progress_update.emit(10)
            
            # Check if the worker script exists
            worker_script = os.path.join(os.path.dirname(__file__), "whisper_worker.py")
            if not os.path.exists(worker_script):
                self.error_occurred.emit(f"Worker script not found: {worker_script}")
                self._simulate_transcription()
                return
                
            self.status_update.emit(f"Loading {self.model_size} Whisper model in separate process...")
            
            # Run transcription in a separate process using the worker script
            import subprocess
            import json
            
            self.generation_started.emit()
            
            # Use subprocess instead of importing whisper directly
            cmd = [sys.executable, worker_script, target_file, self.model_size]
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # Wait for the process to complete
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode != 0:
                self.error_occurred.emit(f"Transcription process failed: {stderr}")
                self._simulate_transcription()
                return
                
            # Parse the JSON result
            try:
                result = json.loads(stdout)
                if not result["success"]:
                    self.error_occurred.emit(f"Transcription error: {result['error']}")
                    self._simulate_transcription()
                    return
                    
                text = result["text"]
                self.progress_update.emit(100)
                self.result_ready.emit(text)
                
            except json.JSONDecodeError:
                self.error_occurred.emit("Failed to parse transcription result")
                self._simulate_transcription()
                
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"Error during transcription: {str(e)}")
            self._simulate_transcription()
        finally:
            # Clean up temp files
            self._cleanup_temp_files()
    
    def _extract_audio(self):
        """Extract audio from video file using FFmpeg."""
        try:
            # Create a temporary file for the audio
            fd, temp_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            self.temp_audio_file = temp_path
            
            # Check if FFmpeg is available
            if shutil.which('ffmpeg'):
                # Use FFmpeg to extract audio
                cmd = ['ffmpeg', '-i', self.file_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', temp_path]
                subprocess.run(cmd, check=True, capture_output=True)
                return True
            else:
                raise RuntimeError("FFmpeg not found. Please install FFmpeg to process video files.")
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}", exc_info=True)
            raise
    
    def _cleanup_temp_files(self):
        """Clean up temporary files."""
        if self.temp_audio_file and os.path.exists(self.temp_audio_file):
            try:
                os.unlink(self.temp_audio_file)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")
    
    def stop(self):
        """Stop the transcription process."""
        self.running = False
        # Terminate the subprocess if it's running
        if self.process:
            try:
                self.process.terminate()
                # Give it a moment to terminate gracefully
                import time
                time.sleep(0.1)
                # Force kill if still running
                if self.process.poll() is None:
                    self.process.kill()
            except Exception as e:
                logger.warning(f"Failed to terminate process: {e}")
    
    def _simulate_transcription(self):
        """Simulate a transcription response for testing or fallback."""
        self.status_update.emit("Simulating transcription (Whisper not installed)...")
        
        # Simulate processing steps
        for i in range(30, 100, 10):
            if not self.running:
                return
            self.progress_update.emit(i)
            time.sleep(0.5)
        
        # Create a mock transcript
        mock_transcript = (
            "This is a simulated transcript because OpenAI Whisper is not installed.\n\n"
            "To use actual transcription, please install Whisper with:\n"
            "pip install openai-whisper\n\n"
            f"Selected file: {os.path.basename(self.file_path)}\n"
            f"Selected model: {self.model_size}\n\n"
            "When properly installed, this tab will transcribe audio and video files to text."
        )
        
        self.result_ready.emit(mock_transcript)
    
    def stop(self):
        """Stop the transcription process."""
        self.running = False

class TranscribeTab(AbstractContentTab):
    """Tab for transcribing audio or video files to text using OpenAI Whisper."""
    
    def __init__(self, main_window):
        super().__init__(main_window)
        self.tab_title = "Transcribe"
        self.content_type = "transcribe"
        
        # Instance variables
        self.current_file = None
        self.transcription_thread = None
        self.transcription_result = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Clear the placeholder from AbstractContentTab
        self.main_layout.removeWidget(self.placeholder)
        self.placeholder.deleteLater()
        
        # Top controls area
        controls_layout = QHBoxLayout()
        
        # File selection button
        self.select_file_btn = QPushButton("Select Audio/Video File")
        self.select_file_btn.clicked.connect(self.select_file)
        self.select_file_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        controls_layout.addWidget(self.select_file_btn)
        
        # Display selected file
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #666;")
        controls_layout.addWidget(self.file_label, 1)  # 1 = stretch factor
        
        # Model selection
        controls_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")  # Default to base model
        self.model_combo.setToolTip("Larger models are more accurate but slower")
        controls_layout.addWidget(self.model_combo)
        
        self.main_layout.addLayout(controls_layout)
        
        # Progress bar
        self.progress_area = QWidget()
        progress_layout = QHBoxLayout(self.progress_area)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.status_label = QLabel("Ready")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        self.progress_area.setVisible(False)
        self.main_layout.addWidget(self.progress_area)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top half: Transcription controls
        self.control_frame = QFrame()
        control_frame_layout = QVBoxLayout(self.control_frame)
        
        # Add transcribe button
        self.transcribe_btn = QPushButton("Transcribe")
        self.transcribe_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.transcribe_btn.clicked.connect(self.start_transcription)
        self.transcribe_btn.setEnabled(False)  # Disable until file selected
        self.transcribe_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.transcribe_btn.setMinimumHeight(50)
        
        # Add a larger font to the button
        font = self.transcribe_btn.font()
        font.setPointSize(font.pointSize() + 2)
        self.transcribe_btn.setFont(font)
        
        control_frame_layout.addWidget(self.transcribe_btn)
        
        # Add cancel button (initially hidden)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.cancel_btn.clicked.connect(self.cancel_transcription)
        self.cancel_btn.setVisible(False)
        control_frame_layout.addWidget(self.cancel_btn)
        
        # Information text
        info_text = (
            "Select an audio or video file, choose a model size, and click 'Transcribe' to convert speech to text.\n"
            "Supported file formats include: WAV, MP3, MP4, FLAC, OGG, AAC, AVI, MOV, MKV, WebM.\n"
            "Larger models are more accurate but require more memory and processing power.\n"
            "Make sure OpenAI Whisper is installed: pip install openai-whisper"
        )
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; background-color: #f8f8f8; padding: 10px; border-radius: 5px;")
        control_frame_layout.addWidget(info_label)
        
        # Add some spacing
        control_frame_layout.addStretch(1)
        
        splitter.addWidget(self.control_frame)
        
        # Bottom half: Results area
        self.result_frame = QFrame()
        result_frame_layout = QVBoxLayout(self.result_frame)
        
        # Results header with controls
        result_header = QHBoxLayout()
        result_header.addWidget(QLabel("Transcription Results:"))
        
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.copy_btn.clicked.connect(self.copy_text)
        self.copy_btn.setEnabled(False)
        result_header.addWidget(self.copy_btn)
        
        result_frame_layout.addLayout(result_header)
        
        # Results text area
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("Transcription results will appear here...")
        result_frame_layout.addWidget(self.result_text)
        
        splitter.addWidget(self.result_frame)
        
        # Set initial splitter sizes - give more space to results
        splitter.setSizes([200, 400])
        
        self.main_layout.addWidget(splitter, 1)  # 1 = stretch factor
    
    def select_file(self):
        """Open file dialog to select an audio or video file."""
        file_filters = (
            "Audio/Video Files (*.wav *.mp3 *.flac *.ogg *.aac *.mp4 *.avi *.mov *.mkv *.webm);;"
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.aac);;"
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm);;"
            "All Files (*)"
        )
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio or Video File",
            os.path.expanduser("~"),
            file_filters
        )
        
        if file_path:
            self.current_file = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.transcribe_btn.setEnabled(True)
            
            # Clear any previous results
            self.result_text.clear()
            self.copy_btn.setEnabled(False)
            self.transcription_result = None
    
    def start_transcription(self):
        """Start the transcription process."""
        if not self.current_file:
            QMessageBox.warning(self, "No File Selected", "Please select an audio or video file first.")
            return
        
        # Update UI for transcription in progress
        self.transcribe_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.progress_area.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting transcription...")
        self.select_file_btn.setEnabled(False)
        self.model_combo.setEnabled(False)
        
        # Clear previous results
        self.result_text.clear()
        
        # Create and start the transcription thread
        self.transcription_thread = TranscriptionThread(
            self.current_file,
            self.model_combo.currentText()
        )
        
        # Connect signals
        self.transcription_thread.progress_update.connect(self.update_progress)
        self.transcription_thread.status_update.connect(self.update_status)
        self.transcription_thread.result_ready.connect(self.display_result)
        self.transcription_thread.error_occurred.connect(self.handle_error)
        self.transcription_thread.generation_started.connect(self.show_loading_message)
        self.transcription_thread.finished.connect(self.transcription_finished)
        
        # Start the thread
        self.transcription_thread.start()
    
    def show_loading_message(self):
        """Show a message that transcription has started."""
        self.result_text.setPlainText("Processing audio... This may take several minutes depending on the file length and model size.")
        
    def cancel_transcription(self):
        """Cancel the transcription process."""
        if self.transcription_thread and self.transcription_thread.isRunning():
            self.transcription_thread.stop()
            self.transcription_thread.wait()
            self.status_label.setText("Transcription cancelled")
            
            # Reset UI after cancellation
            QTimer.singleShot(500, self.transcription_finished)
    
    def update_progress(self, value):
        """Update the progress bar."""
        self.progress_bar.setValue(value)
    
    def update_status(self, status):
        """Update the status label."""
        self.status_label.setText(status)
    
    def display_result(self, text):
        """Display the transcription result."""
        self.result_text.setPlainText(text)
        self.transcription_result = text
        self.copy_btn.setEnabled(True)
    
    def handle_error(self, error_message):
        """Handle transcription errors."""
        # Display error in results area
        error_format = self.result_text.currentCharFormat()
        error_format.setForeground(QColor("red"))
        self.result_text.setCurrentCharFormat(error_format)
        self.result_text.append("Error:")
        self.result_text.append(error_message)
        
        # Reset format
        normal_format = self.result_text.currentCharFormat()
        normal_format.setForeground(QColor("black"))
        self.result_text.setCurrentCharFormat(normal_format)
        
        # Show a message box for important errors
        QMessageBox.warning(self, "Transcription Error", error_message)
    
    def transcription_finished(self):
        """Clean up after transcription is complete."""
        # Reset UI
        self.transcribe_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.select_file_btn.setEnabled(True)
        self.model_combo.setEnabled(True)
        
        # Keep progress area visible with final status
        if self.progress_bar.value() == 100:
            self.status_label.setText("Transcription complete")
        
        # Ensure copy button is enabled if we have results
        if self.transcription_result:
            self.copy_btn.setEnabled(True)
    
    def copy_text(self):
        """Copy the transcription result to clipboard."""
        if not self.transcription_result:
            return
            
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.transcription_result)

    def refresh(self):            
        QTimer.singleShot(1500, lambda: self.copy_btn.setText(original_text))        
        self.copy_btn.setText("Copied!")        
        original_text = self.copy_btn.text()        
        """Refresh the tab content."""
        # Nothing to refresh automatically
        pass
