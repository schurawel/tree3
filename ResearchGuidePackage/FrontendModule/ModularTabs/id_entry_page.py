"""
ID Entry Page
============
A simple page for entering a node ID directly in a tab instead of using a dialog.
"""
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QApplication, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
import uuid

logger = logging.getLogger(__name__)

class NodeIDEntryPage(QWidget):
    """Widget for entering a node ID to edit, view, or open a page."""
    
    action_selected = pyqtSignal(str, object)  # action, data
    
    def __init__(self, parent=None, action_type="edit"):
        """Initialize the ID entry page."""
        super().__init__(parent)
        self.action_type = action_type  # "edit", "open_page", etc.
        
        # Configure based on action type
        if action_type == "edit":
            self.title_text = "Edit Object"
            self.placeholder = "Enter object ID"
            self.button_text = "Edit"
        elif action_type == "open_page":
            self.title_text = "Open Page"
            self.placeholder = "Enter page ID"
            self.button_text = "Open"
        else:
            self.title_text = "Enter ID"
            self.placeholder = "Enter ID"
            self.button_text = "Load"
        
        self.setup_ui()
        self.auto_paste_from_clipboard()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 40, 30, 40)
        
        # Add spacer to push content to center vertically
        main_layout.addStretch(1)
        
        # Create a simple container frame
        container = QFrame()
        container.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Container layout
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)
        
        # Add a header label for the box
        header_label = QLabel("Enter Node-ID...")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(header_label)
        
        # ID input field
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText(self.placeholder)
        self.id_input.setMinimumWidth(350)
        self.id_input.textChanged.connect(self.validate_input)
        container_layout.addWidget(self.id_input)
        
        # Validation message
        self.validation_label = QLabel("")
        self.validation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.validation_label)
        
        # Buttons in horizontal layout - now centered
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Center the buttons with stretch on both sides
        buttons_layout.addStretch(1)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.cancel_clicked)
        buttons_layout.addWidget(self.cancel_button)
        
        # Load button - with green styling
        self.load_button = QPushButton(self.button_text)
        self.load_button.setMinimumWidth(100)
        self.load_button.clicked.connect(self.load_clicked)
        self.load_button.setEnabled(False)  # Disabled until valid input
        self.load_button.setStyleSheet("background-color: #4CAF50; color: white;")
        buttons_layout.addWidget(self.load_button)
        
        # Equal stretch on both sides centers the buttons
        buttons_layout.addStretch(1)
        
        container_layout.addLayout(buttons_layout)
        
        # Add container to main layout, centered horizontally
        container_wrapper = QHBoxLayout()
        container_wrapper.addStretch(1)
        container_wrapper.addWidget(container)
        container_wrapper.addStretch(1)
        
        main_layout.addLayout(container_wrapper)
        
        # Add spacer to push content to center vertically
        main_layout.addStretch(1)
    
    def auto_paste_from_clipboard(self):
        """Attempt to paste the clipboard content into the input field."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        # Check if clipboard text looks like a UUID
        if text and len(text) >= 32:  # UUIDs are 32-36 chars depending on format
            self.id_input.setText(text)
            self.id_input.selectAll()  # Select all for easy replacement
    
    def validate_input(self):
        """Validate the input as a proper UUID."""
        input_text = self.id_input.text().strip()
        
        if not input_text:
            self.validation_label.setText("")
            self.load_button.setEnabled(False)
            return
        
        try:
            # Try to parse as UUID
            uuid_obj = uuid.UUID(input_text)
            self.validation_label.setText("")
            self.load_button.setEnabled(True)
        except ValueError:
            self.validation_label.setText("Invalid UUID format")
            self.validation_label.setStyleSheet("color: red")
            self.load_button.setEnabled(False)
    
    def load_clicked(self):
        """Handle Load button click."""
        node_id = self.id_input.text().strip()
        
        try:
            # Convert to UUID to ensure validity
            uuid_obj = uuid.UUID(node_id)
            
            # Emit signal with action type and node ID
            self.action_selected.emit(self.action_type, str(uuid_obj))
        except ValueError:
            self.validation_label.setText("Invalid UUID format")
            self.validation_label.setStyleSheet("color: red")
    
    def cancel_clicked(self):
        """Handle Cancel button click."""
        # Emit signal to return to the selector
        self.action_selected.emit("cancel", None)
    
    def get_tab_title(self):
        """Return the tab title."""
        return self.title_text
