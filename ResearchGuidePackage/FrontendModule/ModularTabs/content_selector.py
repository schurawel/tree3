"""
Content Selector
===============
Widget displaying a button matrix for selecting what content to display in a tab.
"""
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QGridLayout, 
                            QLabel, QSizePolicy, QDialog, QComboBox, 
                            QDialogButtonBox, QHBoxLayout, QMessageBox, QLineEdit,
                            QApplication, QScrollArea)  # Added QApplication import
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation
from PyQt6.QtGui import QIcon, QFont
from PyQt6 import QtWidgets
import asyncio

logger = logging.getLogger('ContentSelector')

class PageSelectorDialog(QDialog):
    """Dialog for selecting a page to open."""
    
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.selected_page_id = None
        
        self.setWindowTitle("Select Page")
        self.setMinimumWidth(400)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Add page selection dropdown
        layout.addWidget(QLabel("Select a page to open:"))
        
        self.page_combo = QComboBox()
        self.page_combo.setMinimumWidth(300)
        layout.addWidget(self.page_combo)
        
        # Populate page dropdown
        self.populate_pages()
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def populate_pages(self):
        """Populate the page dropdown with available pages."""
        self.page_combo.clear()
        self.page_combo.addItem("Select a page...", None)
        
        # Check if graph exists
        if hasattr(self.main_window, 'graph') and self.main_window.graph:
            # Get page nodes
            page_nodes = []
            for node_id, node_data in self.main_window.graph.nodes(data=True):
                if node_data.get('node_type') == 'page':
                    display_text = node_data.get('title', 
                                  node_data.get('name', 
                                  node_data.get('label', str(node_id)[:8])))
                    page_nodes.append((display_text, str(node_id)))
            
            # Sort pages alphabetically
            page_nodes.sort()
            
            # Add sorted pages to dropdown
            for display_text, node_id in page_nodes:
                self.page_combo.addItem(display_text, node_id)
    
    def get_selected_page(self):
        """Get the selected page ID."""
        return self.page_combo.currentData()
    
    def accept(self):
        """Handle dialog acceptance."""
        self.selected_page_id = self.get_selected_page()
        super().accept()


class ContentSelector(QWidget):
    """Widget displaying a matrix of buttons for content type selection."""
    
    content_selected = pyqtSignal(str, object, object)

    ORIGINAL_BUTTON_STYLE = """
        QPushButton {
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
            border-color: #ccc;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        /* Make sure all child elements are transparent */
        QPushButton QLabel {
            background-color: transparent;
        }
        QPushButton QWidget {
            background-color: transparent;
        }
    """

    HIGHLIGHT_BUTTON_STYLE = """
        QPushButton {
            background-color: #d4edda; /* Light green for match */
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #c3e6cb;
            border-color: #b1dfbb;
        }
        QPushButton:pressed {
            background-color: #b1dfbb;
        }
        /* Make sure all child elements are transparent */
        QPushButton QLabel {
            background-color: transparent;
        }
        QPushButton QWidget {
            background-color: transparent;
        }
    """
    
    def __init__(self, main_window):
        """Initialize the content selector widget."""
        super().__init__()
        self.main_window = main_window
        self.all_buttons_data = [] # To store {'widget': QPushButton, 'text': str}
        self.grid_columns = 3  # Changed from 2 to 3 columns
        self._last_matching_widgets = [] # Store currently highlighted/matching button widgets
        self.current_loading_button = None # Track which button is currently loading
        self.overlay = None # Overlay widget to block UI during loading
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10) 
        main_layout.setSpacing(10) 

        # Add Search Bar Container (ABOVE button grid)
        search_bar_container_widget = QWidget()
        search_bar_layout = QHBoxLayout(search_bar_container_widget)
        search_bar_layout.setContentsMargins(0,0,0,0)

        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search options...")
        self.search_bar.textChanged.connect(self._filter_buttons)
        self.search_bar.returnPressed.connect(self._handle_search_enter_pressed)
        self.search_bar.setFixedWidth(450) 
        
        search_bar_layout.addStretch(1) 
        search_bar_layout.addWidget(self.search_bar)
        search_bar_layout.addStretch(1)
        main_layout.addSpacing(80) 
        main_layout.addWidget(search_bar_container_widget) # Search bar added first

        # Spacing between search bar and button grid
        main_layout.addSpacing(30) 

        # Button Grid Container with Scroll Area - Now centered and smaller
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameStyle(QScrollArea.Shape.NoFrame)  # Remove frame
        scroll_area.viewport().setStyleSheet("background-color: white;")
        # Set fixed size for scroll area to make it smaller
        scroll_area.setFixedWidth(650)  # Increased from 450 to accommodate 3 columns
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: white;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # Create content widget for the scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)
        
        # Create button grid with fixed spacing
        self.button_grid = QGridLayout()
        self.button_grid.setSpacing(15)  # Fixed spacing between buttons
        self.button_grid.setContentsMargins(5, 5, 5, 5)  # Fixed margins
        
        buttons_config = [
            {"text": "Open Page", "icon": "📄", "tooltip": "Open and edit a page from the graph", "callback": self.select_page},
            {"text": "New Page", "icon": "📄+", "tooltip": "Create a new page (Not Implemented)", "callback": lambda: self._show_not_implemented_message("New Page")},
            {"text": "Index", "icon": "🗂️", "tooltip": "Browse nodes organized by index and namespace", "callback": lambda: self.emit_content_selection("namespaces", None)},
            {"text": "Search", "icon": "🔍", "tooltip": "Search for nodes in the graph", "callback": lambda: self.emit_content_selection("search", None)},
            {"text": "Discover", "icon": "🔭", "tooltip": "Interactive graph exploration", "callback": lambda: self.emit_content_selection("discover", None)},
            {"text": "Bird View", "icon": "🦅", "tooltip": "High-level view of the entire graph", "callback": lambda: self.emit_content_selection("birdview", None)},
            {"text": "Database", "icon": "🗄️", "tooltip": "Manage database connections", "callback": lambda: self.emit_content_selection("databases", None)},
            {"text": "Draw", "icon": "✏️", "tooltip": "Draw and create new content", "callback": lambda: self.emit_content_selection_with_loading("draw", None)},
            {"text": "Import/Export", "icon": "🔄", "tooltip": "Import and export data in various formats", "callback": lambda: self.emit_content_selection("import_export", None)},
            {"text": "Bookmarks", "icon": "🔖", "tooltip": "Access bookmarked content (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Bookmarks")},
            {"text": "Library", "icon": "📚", "tooltip": "Browse your document library (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Library")},
            {"text": "Add Object", "icon": "➕", "tooltip": "Add a new object to the graph", "callback": self.open_add_object_tab},
            {"text": "Edit Object", "icon": "📦", "tooltip": "Edit an existing object", "callback": self.open_edit_object_tab},
            {"text": "Docs", "icon": "📖", "tooltip": "View application documentation", "callback": lambda: self.emit_content_selection("documentation", None)},
            {"text": "Versioning", "icon": "🔀", "tooltip": "Manage document versions (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Version Control")},
            {"text": "New Theory", "icon": "💡", "tooltip": "Create a new theory document (Not Implemented)", "callback": lambda: self._show_not_implemented_message("New Theory")},
            {"text": "New Raw File", "icon": "📝", "tooltip": "Create a new raw file (Not Implemented)", "callback": lambda: self._show_not_implemented_message("New Raw File")},
            {"text": "Latex Editor", "icon": "📐", "tooltip": "Open the Latex editor (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Latex Editor")},
            {"text": "Issues", "icon": "❗", "tooltip": "Track project issues (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Issues")},
            {"text": "ResearchBot", "icon": "💬", "tooltip": "Interact with the Research Bot", 
             "callback": lambda: self.emit_content_selection("researchbot", None)},
            {"text": "Voyage", "icon": "🚢", "tooltip": "Plan and track research voyages (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Voyage")},
            {"text": "CAS", "icon": "∑", "tooltip": "Manage Content Addressable Storage (Not Implemented)", "callback": lambda: self._show_not_implemented_message("CAS")},
            {"text": "Console", "icon": "❯_", "tooltip": "Open developer console (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Console")},
            {"text": "Outline", "icon": "📑", "tooltip": "View project outline (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Outline")},
            {"text": "Agents", "icon": "🤖", "tooltip": "Use AI agent for research tasks (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Agent")},
            {"text": "Transcribe", "icon": "🎤", "tooltip": "Transcribe audio to text (Not Implemented)", "callback": lambda: self.emit_content_selection("transcribe", None)},
            {"text": "Translate", "icon": "🌐", "tooltip": "Translate content between languages (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Translate")},
            {"text": "Imagine", "icon": "🎨", "tooltip": "Generate images with AI (Not Implemented)", "callback": lambda: self._show_not_implemented_message("Imagine")},
            {"text": "OCR", "icon": "📷", "tooltip": "Extract text from images (Not Implemented)", "callback": lambda: self._show_not_implemented_message("OCR")},
        ]

        self.all_buttons_data.clear()
        for idx, config in enumerate(buttons_config):
            button = self.create_button(
                config["text"], 
                config["icon"], 
                config["tooltip"],
                config["callback"]
            )
            self.all_buttons_data.append({'widget': button, 'text': config["text"]})
            row = idx // self.grid_columns
            col = idx % self.grid_columns
            self.button_grid.addWidget(button, row, col)
        
        # Add the grid to the scroll content
        scroll_layout.addLayout(self.button_grid)
        
        # Add stretching space at bottom to keep buttons at the top if there's extra space
        scroll_layout.addStretch(1)
        
        # Set the content widget for the scroll area
        scroll_area.setWidget(scroll_content)
        
        # Add center container to horizontally center the scroll area
        center_container = QHBoxLayout()
        center_container.addStretch(1)  # Push scroll area to center
        center_container.addWidget(scroll_area)
        center_container.addStretch(1)  # Push scroll area to center
        
        # Add the centered scroll area to the main layout
        main_layout.addLayout(center_container)
        
        # Create overlay widget for blocking UI during loading
        self.create_overlay()
        
        # Ensure buttons maintain their size regardless of window size
        for button_data in self.all_buttons_data:
            button_data['widget'].setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    
    def create_overlay(self):
        """Create an extremely subtle overlay that doesn't block UI visually."""
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)
        self.overlay.hide()
        self.overlay.setGeometry(self.rect())
        
        # Make sure overlay resizes with the parent
        self.resizeEvent = self.resize_overlay
    
    def resize_overlay(self, event):
        """Handle resize events to ensure overlay covers the entire widget."""
        if self.overlay:
            self.overlay.setGeometry(self.rect())
        
        # Call original resize event
        super().resizeEvent(event)
    
    def create_button(self, text, icon_text, tooltip, callback):
        """Create a styled content button with an icon and text."""
        button = QPushButton()
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.setMinimumSize(180, 90)
        button.setMaximumSize(200, 100)
        button.setToolTip(tooltip)
        button.clicked.connect(lambda: self._handle_button_click(button, callback))
        
        # Create a custom layout to properly position loading indicator later
        button_widget = QWidget()
        button_layout = QVBoxLayout(button)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(10, 10, 10, 10)
        
        # Store original text and icon for loading state handling
        button.setProperty("original_icon", icon_text)
        button.setProperty("original_text", text)
        
        # Set all internal widgets to have transparent backgrounds
        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet("background-color: transparent;")
        icon_font = icon_label.font()
        icon_font.setPointSize(20)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setObjectName("icon_label")
        button_layout.addWidget(icon_label)
        
        text_label = QLabel(text)
        text_label.setStyleSheet("background-color: transparent;")
        text_font = text_label.font()
        text_font.setPointSize(10)
        text_font.setBold(True)
        text_label.setFont(text_font)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setObjectName("text_label")
        button_layout.addWidget(text_label)
        
        # Apply the button style
        button.setStyleSheet(self.ORIGINAL_BUTTON_STYLE)
        
        return button
    
    def _handle_button_click(self, button, callback):
        """Handle button click with loading state management."""
        # Don't allow clicking if we're already loading
        if self.current_loading_button:
            return
            
        # Set loading state
        self.show_loading_indicator(button)
        
        # Execute the callback
        callback()
    
    def show_loading_indicator(self, button):
        """Show loading indicator on a button and block UI."""
        # Track the current loading button
        self.current_loading_button = button
        
        # Delete any existing loading widget first
        if hasattr(button, "loading_widget") and button.loading_widget:
            button.loading_widget.deleteLater()
        
        # Create the loading widget - much more visible now
        loading_widget = QWidget(button)
        loading_widget.setObjectName("loading_indicator")
        loading_widget.setFixedSize(70, 70)  # Larger size
        loading_widget.setStyleSheet("background-color: transparent; border: none;")
        
        # Create solid dark background circle first
        circle_bg = QWidget(loading_widget)
        circle_bg.setObjectName("circle_bg")
        circle_bg.setGeometry(5, 5, 60, 60)  # Positioned within the loading_widget
        circle_bg.setStyleSheet("""
            background-color: rgba(40, 40, 40, 0.85);
            border-radius: 30px;
            border: 1px solid white;
        """)
        circle_bg.show()
        
        # Create arrow label inside loading widget with bold white arrow
        arrow_label = QLabel("↻", loading_widget)  # Using an arrow character
        arrow_label.setObjectName("arrow_label")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setGeometry(0, 0, 70, 70)  # Cover the full loading_widget
        arrow_label.setStyleSheet("""
            color: white;
            font-size: 48px;
            font-weight: bold;
            background-color: transparent;
        """)
        
        # Store reference to loading widget on button
        button.loading_widget = loading_widget
        button.arrow_label = arrow_label
        
        # Position loading widget in center of button
        loading_widget.move(
            (button.width() - loading_widget.width()) // 2,
            (button.height() - loading_widget.height()) // 2
        )
        loading_widget.show()
        loading_widget.raise_()
        
        # Create and start timer-based rotation animation instead of CSS transform
        self.start_rotation_timer(arrow_label)
        
        # Disable button to prevent multiple clicks
        button.setEnabled(False)
        
        # Force immediate update of the UI
        button.update()
        loading_widget.update()
        arrow_label.update()
        self.repaint()
        QApplication.processEvents()
        
        logger.debug("Loading indicator displayed")

    def start_rotation_timer(self, label):
        """Start a timer that updates the rotation by changing the arrow character."""
        # We'll use a sequence of Unicode arrows for rotation effect
        rotation_chars = ["↻", "⟳", "↺", "⥀", "↻"]
        timer = QTimer(label)
        label.rotation_index = 0
        
        def update_rotation():
            try:
                # Update the arrow character to create rotation illusion
                label.rotation_index = (label.rotation_index + 1) % len(rotation_chars)
                label.setText(rotation_chars[label.rotation_index])
                
                # Briefly increase font size for emphasis using a safer approach
                try:
                    label.setStyleSheet("""
                        color: white;
                        font-size: 52px;
                        font-weight: bold;
                        background-color: transparent;
                    """)
                    
                    # Create a local function that captures the label in a safer way
                    def reset_style():
                        try:
                            label.setStyleSheet("""
                                color: white;
                                font-size: 48px;
                                font-weight: bold;
                                background-color: transparent;
                            """)
                        except RuntimeError:
                            # Object deleted, nothing to do
                            pass
                    
                    # Schedule the reset with the safer function
                    QTimer.singleShot(50, reset_style)
                except RuntimeError:
                    # Label was deleted during the animation
                    if timer.isActive():
                        timer.stop()
            except RuntimeError:
                # Label has been deleted, stop the timer
                if timer.isActive():
                    timer.stop()
        
        # Connect timer to update function
        timer.timeout.connect(update_rotation)
        timer.start(150)  # Update every 150ms
        
        # Store reference to timer
        label.rotation_timer = timer
    
    def hide_loading_indicator(self, button=None):
        """Hide loading indicator and unblock UI."""
        if not button and self.current_loading_button:
            button = self.current_loading_button
            
        if button:
            # Remove loading widget if it exists
            if hasattr(button, "loading_widget") and button.loading_widget:
                # Stop the rotation timer
                if hasattr(button, "arrow_label") and hasattr(button.arrow_label, "rotation_timer"):
                    button.arrow_label.rotation_timer.stop()
                    button.arrow_label.rotation_timer = None
                    
                # Delete the loading widget
                button.loading_widget.deleteLater()
                button.loading_widget = None
            
            # Restore original button style
            button.setStyleSheet(self.ORIGINAL_BUTTON_STYLE)
            
            # Re-enable button
            button.setEnabled(True)
        
        # Reset current loading button
        self.current_loading_button = None
    
    def emit_content_selection_with_loading(self, content_type, data=None):
        """Emit content selection with loading indicator."""
        # Schedule emission for better visual feedback
        QTimer.singleShot(100, lambda: self._delayed_emit(content_type, data))
        
        # Force immediate update of UI
        self.repaint()
        QApplication.processEvents()
    
    def _delayed_emit(self, content_type, data=None):
        """Helper method to emit content selection with the source widget after a delay."""
        # Emit the signal with proper parameters
        self.content_selected.emit(content_type, data, self)
        
        # Keep loading indicator visible for a reasonable time
        QTimer.singleShot(800, self.hide_loading_indicator)
    
    def emit_content_selection(self, content_type, data=None):
        """Helper method to emit content selection with the source widget."""
        # Show loading indicator first (regular buttons also show loading)
        if not self.current_loading_button and content_type != "documentation":
            # Documentation is usually fast, don't show loading for it
            button = self._find_button_by_text(content_type.capitalize())
            if button:
                self.show_loading_indicator(button)
                
            # Use delayed emission for better visual feedback
            QTimer.singleShot(100, lambda: self._delayed_emit(content_type, data))
        else:
            # Direct emission for documentation or if already in loading state
            self.content_selected.emit(content_type, data, self)
    
    def _find_button_by_text(self, text):
        """Find a button by its text."""
        for button_data in self.all_buttons_data:
            if button_data['text'].lower() == text.lower():
                return button_data['widget']
        return None

    def _clear_grid_layout(self):
        """Removes all widgets from the button_grid."""
        while self.button_grid.count():
            item = self.button_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                # widget.deleteLater() # No, we are reusing them

    def _repopulate_grid(self, button_widgets_ordered):
        """Repopulates the grid with the given list of button widgets."""
        self._clear_grid_layout()
        for idx, btn_widget in enumerate(button_widgets_ordered):
            row = idx // self.grid_columns
            col = idx % self.grid_columns
            self.button_grid.addWidget(btn_widget, row, col)

    def _filter_buttons(self):
        search_text = self.search_bar.text().lower().strip()

        if not search_text:
            self._clear_filter_and_restore_grid()
            return

        matching_buttons_widgets = []
        non_matching_buttons_widgets = []

        for btn_data in self.all_buttons_data:
            widget = btn_data['widget']
            text_content = btn_data['text'].lower()

            if search_text in text_content:
                widget.setStyleSheet(self.HIGHLIGHT_BUTTON_STYLE)
                matching_buttons_widgets.append(widget)
            else:
                widget.setStyleSheet(self.ORIGINAL_BUTTON_STYLE)
                non_matching_buttons_widgets.append(widget)
        
        self._last_matching_widgets = matching_buttons_widgets # Store matches
        
        ordered_widgets_for_grid = matching_buttons_widgets + non_matching_buttons_widgets
        self._repopulate_grid(ordered_widgets_for_grid)

    def _clear_filter_and_restore_grid(self):
        self._last_matching_widgets = [] # Clear matches
        ordered_widgets_for_grid = []
        for btn_data in self.all_buttons_data:
            widget = btn_data['widget']
            widget.setStyleSheet(self.ORIGINAL_BUTTON_STYLE)
            ordered_widgets_for_grid.append(widget)
        self._repopulate_grid(ordered_widgets_for_grid)

    def _handle_search_enter_pressed(self):
        """Handles the Enter key press in the search bar."""
        if len(self._last_matching_widgets) == 1:
            # If exactly one button is highlighted, "click" it.
            self._last_matching_widgets[0].click()

    def select_page(self):
        """Open a page by ID entry or dialog selection."""
        # Use ID entry page for direct page opening
        from ResearchGuidePackage.FrontendModule.ModularTabs.id_entry_page import NodeIDEntryPage
        id_entry_page = NodeIDEntryPage(self.main_window, action_type="open_page")
        
        # Connect its signal to our handler
        id_entry_page.action_selected.connect(self._handle_id_entry_action)
        
        # Emit signal to show the ID entry page
        self.content_selected.emit("custom_widget", id_entry_page, self)
        
        # Hide the loading indicator
        if self.current_loading_button:
            self.hide_loading_indicator()

    def emit_content_selection(self, content_type, data=None):
        """Helper method to emit content selection with the source widget."""
        self.content_selected.emit(content_type, data, self)

    def _show_not_implemented_message(self, feature_name):
        """Display a message indicating the feature is not implemented."""
        QMessageBox.information(
            self,
            "Feature Not Implemented",
            f"The '{feature_name}' feature is not yet implemented.",
            QMessageBox.StandardButton.Ok
        )
        logger.info(f"'{feature_name}' button clicked, but feature is not implemented.")

    def open_add_object_tab(self):
        """Open a new node editor tab in add mode."""
        self.emit_content_selection("node_editor", {"mode": "add"})

    def open_edit_object_tab(self):
        """Open a node ID entry page for editing an object."""
        # Create the ID entry page
        from ResearchGuidePackage.FrontendModule.ModularTabs.id_entry_page import NodeIDEntryPage
        id_entry_page = NodeIDEntryPage(self.main_window, action_type="edit")
        
        # Connect its signal to our handler
        id_entry_page.action_selected.connect(self._handle_id_entry_action)
        
        # Emit signal to show the ID entry page
        self.content_selected.emit("custom_widget", id_entry_page, self)
        
        # Hide the loading indicator
        if self.current_loading_button:
            self.hide_loading_indicator()

    def _handle_id_entry_action(self, action, data):
        """Handle actions from the ID entry page."""
        if action == "cancel":
            # Create a new ContentSelector and use custom_widget
            new_selector = ContentSelector(self.main_window)
            new_selector.content_selected.connect(self._on_content_selected_from_replacement)
            self.content_selected.emit("custom_widget", new_selector, self)
        elif action == "edit":
            # Open the node editor tab with the selected node ID
            self.emit_content_selection("node_editor", {"mode": "edit", "node_id": data})
        elif action == "open_page":
            # Open the page with the selected ID
            self.emit_content_selection("page", data)

    def _on_content_selected_from_replacement(self, content_type, data, source_tab):
        """Handle content selection from a replacement ContentSelector."""
        # Forward the signal but with ourselves as the source_tab
        self.content_selected.emit(content_type, data, self)

    async def _select_node_then_edit(self):
        """Show a dialog to select a node, then open the node editor tab."""
        try:
            # Create API client instance
            from ResearchGuidePackage.FrontendModule.client import APIClient
            comm = APIClient()
            
            # Get all nodes
            success, content, error = await comm.request_and_get_response(
                operation="get_nodes",
                params={},
                sender="Frontend"
            )
            
            if not success or not content or not content.get("result"):
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Failed to get nodes: {error or 'Unknown error'}"
                )
                # Hide loading indicator if active
                self.hide_loading_indicator()
                return
            
            nodes_data = content.get("result", {}).get("nodes", [])
            if not nodes_data:
                QtWidgets.QMessageBox.information(
                    self,
                    "No Nodes",
                    "There are no nodes available to edit."
                )
                # Hide loading indicator if active
                self.hide_loading_indicator()
                return
            
            # Create node labels mapping for dialog
            node_labels = {node["id"]: node.get("label", node.get("name", node["id"])) for node in nodes_data}
            
            # Show node selection dialog
            from ResearchGuidePackage.FrontendModule.dialogs import SelectNodeDialog
            dialog = SelectNodeDialog(self, node_labels, title="Edit Object")
            
            # Hide loading indicator before showing dialog
            self.hide_loading_indicator()
            
            if dialog.exec():
                selected_node_id = dialog.get_selected_node_id()
                if selected_node_id:
                    # Open the node editor tab with the selected node
                    self.emit_content_selection("node_editor", {"mode": "edit", "node_id": str(selected_node_id)})
                else:
                    logger.warning("No node selected for editing")
            else:
                logger.info("Node selection cancelled")
        
        except Exception as e:
            logger.error(f"Error selecting node for editing: {e}", exc_info=True)
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Error selecting node: {str(e)}"
            )
            # Hide loading indicator if active
            self.hide_loading_indicator()
