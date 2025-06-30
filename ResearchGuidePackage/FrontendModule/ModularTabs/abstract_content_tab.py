"""
Abstract Content Tab
===================
Base class for all content tabs, defining the common interface that 
specific content implementations should follow.
"""
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget
from PyQt6.QtCore import Qt

logger = logging.getLogger('AbstractContentTab')

class AbstractContentTab(QWidget):
    """Abstract base class for all content tabs in the application."""
    
    def __init__(self, main_window):
        """Initialize the abstract content tab."""
        super().__init__()
        self.main_window = main_window
        self.tab_title = "Tab"  # Default title
        self.content_type = "abstract"  # Content type identifier
        
        # Create base layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Placeholder content (will be overridden by subclasses)
        self.placeholder = QLabel("Content not implemented")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.placeholder)
    
    def get_tab_title(self):
        """Get the title for this tab."""
        return self.tab_title
    
    def set_tab_title(self, title):
        """Set the tab title and update the parent tab widget if possible."""
        self.tab_title = title
        self.update_tab_title()
    
    def update_tab_title(self):
        """Update the title in the parent tab widget."""
        # Find the parent tab widget and update the tab title
        parent = self.parent()
        while parent:
            if isinstance(parent, QTabWidget):
                # Find the index of this widget in the tab widget
                for i in range(parent.count()):
                    if parent.widget(i) == self:
                        parent.setTabText(i, self.tab_title)
                        break
                break
            parent = parent.parent()
    
    def refresh(self):
        """Refresh the content of this tab."""
        # To be implemented by subclasses
        pass
    
    def get_content_type(self):
        """Get the type of content this tab displays."""
        return self.content_type
