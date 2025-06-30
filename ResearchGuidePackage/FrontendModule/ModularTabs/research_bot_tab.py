"""
Research Bot Tab
===============
A chatbot interface that uses an offline AI model to assist with research tasks.
"""

import os
import logging
import asyncio
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QProgressBar, QLabel, QComboBox, QFileDialog,
    QScrollArea, QFrame, QSplitter, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCursor, QPalette

# Set up logging
logger = logging.getLogger('ResearchBot')

class ModelThread(QThread):
    """Thread for running the AI model without blocking the UI."""
    response_ready = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    generation_started = pyqtSignal()  # New signal to indicate generation has started
    
    def __init__(self, model_path, prompt, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.prompt = prompt
        self.running = True

    def run(self):
        """Run the model inference in a separate thread."""
        try:
            # Check if the model path exists
            if not os.path.exists(self.model_path):
                self.error_occurred.emit(f"Model file not found: {self.model_path}")
                return
                
            # Simulate model loading (will be replaced with actual model loading)
            for i in range(10):
                if not self.running:
                    return
                self.progress_update.emit(i * 10)
                time.sleep(0.1)
            
            # Try importing the llama-cpp-python library
            try:
                from llama_cpp import Llama
                
                # Signal that generation is starting (instead of sending a message)
                self.generation_started.emit()
                
                # Log actual prompt for debugging
                logger.info(f"Using prompt: {self.prompt}")
                
                # Load the model (this might take some time)
                llm = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,  # Context window size
                    n_threads=os.cpu_count(),  # Use all available CPU cores
                )
                
                # Generate a response
                output = llm(
                    self.prompt,
                    max_tokens=1024,
                    temperature=0.7,
                    stop=["User:"],
                    echo=False
                )
                
                # Extract the generated text
                response = output["choices"][0]["text"].strip()
                self.response_ready.emit(response)
                
            except ImportError:
                # If llama-cpp-python is not installed, use a simulated response
                logger.warning("llama-cpp-python not installed. Using simulated AI response.")
                
                # Signal that generation is starting
                self.generation_started.emit()
                
                self.simulate_ai_response()
                
        except Exception as e:
            logger.error(f"Error in model thread: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"Error: {str(e)}")
    
    def simulate_ai_response(self):
        """Simulate an AI response for testing when model can't be loaded."""
        # Extract user message from prompt if possible
        user_message = ""
        try:
            if "User:" in self.prompt:
                parts = self.prompt.split("User:")
                if len(parts) > 1:
                    message_parts = parts[1].split("\n")
                    if message_parts:
                        user_message = message_parts[0].strip()
        except Exception as e:
            logger.error(f"Error extracting user message: {e}")
        
        # Create a customized response based on the user's message
        self.response_ready.emit("⚠️ Using simulated response (model not available) ⚠️\n\n")
        
        if user_message:
            self.response_ready.emit(f"You asked: '{user_message}'\n\n")
            
            # Provide a slightly more helpful simulated response
            if "hello" in user_message.lower() or "hi" in user_message.lower():
                self.response_ready.emit("Hello! I'm a simulated response because the actual AI model couldn't be loaded. ")
            elif "help" in user_message.lower():
                self.response_ready.emit("I see you're asking for help. To use the actual ResearchBot, you need to: ")
                self.response_ready.emit("1. Install llama-cpp-python package\n")
                self.response_ready.emit("2. Download an LLM model file like Llama-7b.gguf\n")
                self.response_ready.emit("3. Place the model in your models directory\n\n")
            else:
                self.response_ready.emit("I noticed your message, but I'm just a simulated response. ")
        
        # Add the standard explanation
        self.response_ready.emit(
            "To use the actual AI model instead of this simulated response, please make sure:\n"
            "1. The llama-cpp-python package is installed (pip install llama-cpp-python)\n"
            "2. You have a compatible language model file (like Llama-7b.gguf)\n"
            "3. The model path is correct in the dropdown above\n\n"
            "When properly configured, ResearchBot can help with research tasks using an offline LLM."
        )

class ResearchBotTab(QWidget):
    """Tab for interacting with a research assistant AI."""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.model_thread = None
        self.chat_history = []
        self.awaiting_first_response = False  # Add flag to track if we're waiting for first response
        
        # Default model paths - include project resources directory
        self.models_dir = os.path.join(os.path.expanduser("~"), "Documents", "models")
        self.model_path = os.path.join(self.models_dir, "ggml-model.bin")
        
        self.setup_ui()
        
        # Auto-select a model if available
        self.auto_select_model()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Create top controls section
        controls_layout = QHBoxLayout()
        
        # Model selection
        model_label = QLabel("Model:")
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(250)
        self.populate_models()
        
        # Browse button
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_for_model)
        
        # Reload button
        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.reload_model)
        
        # Add all to controls layout
        controls_layout.addWidget(model_label)
        controls_layout.addWidget(self.model_combo, 1)  # Give it stretch factor
        controls_layout.addWidget(browse_button)
        controls_layout.addWidget(reload_button)
        
        # Add controls to main layout
        main_layout.addLayout(controls_layout)
        
        # Create a splitter for chat and context areas
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Chat area (left side of splitter)
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat history display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(400)
        chat_layout.addWidget(self.chat_display, 1)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        chat_layout.addWidget(self.progress_bar)
        
        # Input area
        input_layout = QHBoxLayout()
        
        # Input field
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setAcceptRichText(False)
        input_layout.addWidget(self.input_field)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(100)
        input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(input_layout)
        
        # Context area (right side of splitter)
        context_widget = QWidget()
        context_layout = QVBoxLayout(context_widget)
        
        context_label = QLabel("Context Information")
        context_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        context_layout.addWidget(context_label)
        
        # Context text area
        self.context_area = QTextEdit()
        self.context_area.setPlaceholderText("Paste relevant context information here to improve the AI responses...")
        context_layout.addWidget(self.context_area)
        
        # Include context checkbox
        self.include_context_cb = QPushButton("Include Context in Next Query")
        self.include_context_cb.setCheckable(True)
        self.include_context_cb.setChecked(False)
        context_layout.addWidget(self.include_context_cb)
        
        # Add both widgets to the splitter
        splitter.addWidget(chat_widget)
        splitter.addWidget(context_widget)
        
        # Set the initial sizes - chat gets more space
        splitter.setSizes([600, 300])
        
        # Add the splitter to the main layout
        main_layout.addWidget(splitter, 1)  # Give it stretch factor
        
        # Add a welcome message
        self.add_bot_message("Welcome to ResearchBot! I'm an offline AI assistant. Please select a model to begin.")
    
    def populate_models(self):
        """Populate the model dropdown with available models."""
        self.model_combo.clear()
        # First check the specific project resources location
        project_models_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
            "FrontendModule", 
            "resources"
        )
        
        logger.info(f"Checking for models in project path: {project_models_path}")
        
        if os.path.exists(project_models_path) and os.path.isdir(project_models_path):
            for file in os.listdir(project_models_path):
                if file.endswith(".gguf"):
                    model_path = os.path.join(project_models_path, file)
                    self.model_combo.addItem(os.path.basename(model_path), model_path)
                    logger.info(f"Found project model: {model_path}")
        # Add some default locations to check - prioritize project resources
        default_locations = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "resources", "models"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "resources"),
            os.path.join(os.path.expanduser("~"), "Documents", "models"),
            os.path.join(os.path.expanduser("~"), "models"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        ]
        
        # Model extensions to look for
        model_extensions = [".bin", ".gguf", ".ggml"]
        
        found_models = []
        
        # Search for models in default locations
        for location in default_locations:
            if os.path.exists(location) and os.path.isdir(location):
                logger.info(f"Searching for models in: {location}")
                for file in os.listdir(location):
                    for ext in model_extensions:
                        if file.lower().endswith(ext):
                            model_path = os.path.join(location, file)
                            found_models.append(model_path)
                            logger.info(f"Found model: {model_path}")
        
        if found_models:
            for model in found_models:
                self.model_combo.addItem(os.path.basename(model), model)
        else:
            self.model_combo.addItem("No models found", "")
            # Add an example placeholder
            self.model_combo.addItem("Example: llama-7b.gguf (not found)", "")
    
    def auto_select_model(self):
        """Automatically select a model from resources directory if available."""
        # First check if models exist in the dropdown
        if self.model_combo.count() == 0:
            return
            
        # Get the first valid model (that's not "No models found")
        for i in range(self.model_combo.count()):
            model_path = self.model_combo.itemData(i)
            if model_path:
                self.model_combo.setCurrentIndex(i)
                self.model_path = model_path
                self.add_bot_message(f"Automatically selected model: {os.path.basename(model_path)}")
                logger.info(f"Auto-selected model: {model_path}")
                return
                
        logger.info("No valid models found for auto-selection")
    
    def browse_for_model(self):
        """Open a file dialog to browse for a model file."""
        options = QFileDialog.Option.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model File",
            os.path.dirname(self.model_path) if os.path.exists(os.path.dirname(self.model_path)) else os.path.expanduser("~"),
            "Model Files (*.bin *.gguf *.ggml);;All Files (*)",
            options=options
        )
        
        if file_name:
            # Check if the model already exists in the dropdown
            found = False
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == file_name:
                    self.model_combo.setCurrentIndex(i)
                    found = True
                    break
            
            if not found:
                # Add the new model to the dropdown
                self.model_combo.addItem(os.path.basename(file_name), file_name)
                self.model_combo.setCurrentIndex(self.model_combo.count() - 1)
            
            self.model_path = file_name
            self.add_bot_message(f"Selected model: {os.path.basename(file_name)}")
    
    def reload_model(self):
        """Reload the currently selected model."""
        model_path = self.model_combo.currentData()
        if model_path:
            self.model_path = model_path
            self.add_bot_message(f"Model reloaded: {os.path.basename(model_path)}")
        else:
            self.add_bot_message("No model selected. Please select a model first.")
    
    def add_user_message(self, message):
        """Add a user message to the chat display."""
        self.chat_display.setTextColor(QColor("#0000FF"))  # Blue for user
        self.chat_display.append(f"You: {message}")
        self.chat_display.setTextColor(QColor("#000000"))  # Reset color
        self.chat_display.append("")  # Add a blank line
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        
        # Add to chat history
        self.chat_history.append(("user", message))
    
    def add_bot_message(self, message):
        """Add a bot message to the chat display."""
        self.chat_display.setTextColor(QColor("#006400"))  # Dark green for bot
        self.chat_display.append(f"ResearchBot: {message}")
        self.chat_display.setTextColor(QColor("#000000"))  # Reset color
        self.chat_display.append("")  # Add a blank line
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        
        # Add to chat history
        self.chat_history.append(("bot", message))
    
    def append_bot_message(self, partial_message):
        """Append text to the current bot message (for streaming responses)."""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        
        # Append the partial message
        self.chat_display.insertPlainText(partial_message)
        
        # Keep the most recent text visible
        self.chat_display.ensureCursorVisible()
        
        # Update the last chat history item if it's a bot message
        if self.chat_history and self.chat_history[-1][0] == "bot":
            current_message = self.chat_history[-1][1]
            self.chat_history[-1] = ("bot", current_message + partial_message)
        else:
            # If there's no existing bot message, create one
            self.chat_history.append(("bot", partial_message))
    
    def send_message(self):
        """Send the user message to the AI model."""
        message = self.input_field.toPlainText().strip()
        if not message:
            return
        
        # Check if a model is selected
        model_path = self.model_combo.currentData()
        if not model_path:
            QMessageBox.warning(self, "No Model Selected", "Please select an AI model file first.")
            return
        
        # Add user message to display
        self.add_user_message(message)
        
        # Clear input field
        self.input_field.clear()
        
        # Prepare the prompt including context if requested
        if self.include_context_cb.isChecked() and self.context_area.toPlainText().strip():
            context = self.context_area.toPlainText().strip()
            prompt = f"Context: {context}\n\nUser: {message}\nResearchBot:"
        else:
            # Make sure the prompt format is clear
            prompt = f"User: {message}\nResearchBot:"
        
        # Log the constructed prompt
        logger.info(f"Constructed prompt: {prompt}")
        
        # Start the model thread
        self.start_model_thread(model_path, prompt)
    
    def start_model_thread(self, model_path, prompt):
        """Start the model thread."""
        # Clean up any existing thread
        if self.model_thread and self.model_thread.isRunning():
            self.model_thread.stop()
            self.model_thread.wait()
        
        # Set up UI for processing
        self.send_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Create a new thread
        self.model_thread = ModelThread(model_path, prompt, self)
        self.model_thread.response_ready.connect(self.handle_response)
        self.model_thread.progress_update.connect(self.update_progress)
        self.model_thread.error_occurred.connect(self.handle_error)
        self.model_thread.finished.connect(self.processing_finished)
        self.model_thread.generation_started.connect(self.show_generating_message)
        
        # Start the thread
        self.model_thread.start()
    
    def show_generating_message(self):
        """Show a temporary 'Generating response...' message that will be replaced by the actual response."""
        # Set flag to indicate we're waiting for first response to replace this message
        self.awaiting_first_response = True
        
        # Start a new response in the chat display with the generating message
        self.chat_display.setTextColor(QColor("#006400"))  # Dark green for bot
        self.chat_display.append("ResearchBot: Generating response...")
        self.chat_display.setTextColor(QColor("#000000"))  # Reset color
        
        # Keep the text cursor at the end to see the message
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
        self.chat_display.ensureCursorVisible()
    
    @pyqtSlot(str)
    def handle_response(self, response):
        """Handle the model response."""
        # Replace the "Generating response..." text if this is the first response
        if self.awaiting_first_response:
            # Set flag back to False since we're handling the first response
            self.awaiting_first_response = False
            
            # Get the current text
            current_text = self.chat_display.toPlainText()
            
            # Find the last occurrence of "ResearchBot: Generating response..."
            generating_text = "ResearchBot: Generating response..."
            pos = current_text.rfind(generating_text)
            
            if pos >= 0:
                # Create a cursor at the position where "Generating response..." starts
                cursor = self.chat_display.textCursor()
                cursor.setPosition(pos)
                cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                
                # Delete the "Generating response..." part
                cursor.removeSelectedText()
                
                # Insert the actual response text
                self.chat_display.setTextColor(QColor("#006400"))  # Dark green for bot
                cursor.insertText("ResearchBot: " + response)
                self.chat_display.setTextColor(QColor("#000000"))  # Reset color
                
                # Add to chat history
                self.chat_history.append(("bot", response))
                
                # Ensure cursor is at the end and visible
                self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
                self.chat_display.ensureCursorVisible()
            else:
                # If we couldn't find the generating text for some reason
                self.append_bot_message(response)
        else:
            # Not the first response, just append to the existing response
            self.append_bot_message(response)
    
    @pyqtSlot(int)
    def update_progress(self, value):
        """Update the progress bar."""
        self.progress_bar.setValue(value)
    
    @pyqtSlot(str)
    def handle_error(self, error_message):
        """Handle errors from the model thread."""
        self.chat_display.setTextColor(QColor("#FF0000"))  # Red for errors
        self.chat_display.append(f"Error: {error_message}")
        self.chat_display.setTextColor(QColor("#000000"))  # Reset color
        self.chat_display.append("")  # Add a blank line
        
        # Add to chat history
        self.chat_history.append(("error", error_message))
    
    def processing_finished(self):
        """Clean up after the model thread has finished."""
        self.send_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Add a blank line after the response
        self.chat_display.append("")
    
    def refresh(self):
        """Refresh the tab (required for compatibility with modular tabs)."""
        # Just repopulate the models in case any were added
        self.populate_models()
    
    def get_tab_title(self):
        """Return the tab title (required for modular tabs)."""
        return "ResearchBot"

    def closeEvent(self, event):
        """Handle tab closure: clean up the model thread."""
        if self.model_thread and self.model_thread.isRunning():
            self.model_thread.stop()
            self.model_thread.wait()
        super().closeEvent(event)
