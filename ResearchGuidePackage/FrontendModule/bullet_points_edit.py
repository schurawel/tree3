from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor  # Add this import for cursor operations
import logging
import asyncio
import uuid
try:
    from ResearchGuidePackage.FrontendModule.clickable_text_edit import ClickableTextEdit
    from ResearchGuidePackage.FrontendModule.link_handler import handle_link_click
except ImportError:
    from clickable_text_edit import ClickableTextEdit
    from link_handler import handle_link_click

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('AbstractBulletPointsEdit')

class AbstractBulletPointsEdit(QtWidgets.QWidget):
    """Abstract class for editing bullet points."""
    def __init__(self, main_window):
        """Initialize AbstractBulletPointsEdit."""
        super().__init__()
        self.main_window = main_window
        self.section_editors = {}  # Store section editors by name
        self.bullet_editors = {}   # Store bullet point editors
        
        # Main layout with zero margins
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create scroll area
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)  # Remove frame border
        
        # Create a container widget for the scroll area
        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Set white background for content widget
        self.content_widget.setStyleSheet("background-color: white; margin: 0; padding: 0;")
        
        # Add scroll area to main layout
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
        
        # Set default message
        self.default_label = QtWidgets.QLabel("Select a node to view/edit its content...")
        self.content_layout.addWidget(self.default_label)
        
        logger.info("AbstractBulletPointsEdit initialized with zero margins.")

    def clear_content(self):
        """Clear all content sections and editors."""
        # Hide default label first
        self.default_label.setVisible(False)
        
        # Clear all widgets from content layout except the default label
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget and widget != self.default_label:
                widget.setParent(None)
                widget.deleteLater()
        
        # Clear editor references
        self.section_editors.clear()
        self.bullet_editors.clear()

    def add_bullet_point(self, text):
        """Add a bullet point with ClickableTextEdit."""
        # Create text edit for this bullet point
        text_edit = ClickableTextEdit(self.main_window)
        text_edit.setPlaceholderText("Enter text...")
        text_edit.setText(f"• {text}")
        text_edit.set_mode("edit")  # Start in edit mode
        
        # Style the text edit - white background, no border
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: none;
                padding: 0px;
            }
        """)
        
        # Make it auto-size to fit content
        text_edit.document().documentLayout().documentSizeChanged.connect(
            lambda: self.resize_text_edit(text_edit)
        )
        
        # Set initial height based on content
        text_edit.setMinimumHeight(25)
        text_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, 
            QtWidgets.QSizePolicy.Policy.Minimum
        )
        
        # Connect link handler
        text_edit.link_clicked.connect(lambda url: handle_link_click(self.main_window, url))
        
        # Add to content layout
        self.content_layout.addWidget(text_edit)
        
        # Add to bullet editors
        bullet_id = f"bullet_{len(self.bullet_editors)}"
        self.bullet_editors[bullet_id] = text_edit
        
        # Resize after adding to layout
        QtCore.QTimer.singleShot(10, lambda: self.resize_text_edit(text_edit))
        
        return text_edit
    
    def resize_text_edit(self, text_edit):
        """Resize text edit to fit its content."""
        doc_height = text_edit.document().size().height()
        margins = text_edit.contentsMargins()
        height = int(doc_height + margins.top() + margins.bottom())
        text_edit.setMinimumHeight(height)
        text_edit.setMaximumHeight(height)
        
    def create_bullet_points_container(self):
        """Create a container widget for bullet points with zero margins."""
        container = QtWidgets.QWidget()
        container.setStyleSheet("background-color: white;")
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        return container

    def add_bullet_point_to_container(self, container, text):
        """Add a bullet point to a specific container."""
        # Create text edit for this bullet point
        text_edit = ClickableTextEdit(self.main_window)
        text_edit.setPlaceholderText("Enter text...")
        
        # Always ensure text starts with bullet point
        if not text.startswith('•'):
            text = '• ' + text.lstrip()
        
        # Check if this is an empty bullet point that needs a placeholder
        content_text = text[2:].strip()  # Remove bullet and get actual content
        is_empty = not content_text or content_text == "Add your notes about this node here."
        is_placeholder = False
        
        
        # Set initial content
        if is_placeholder:
            # Set placeholder immediately
            text_edit.setProperty("is_placeholder", True)
            text_edit.setText(f"• <i style='color: gray;'>Enter Text...</i>")
        else:
            text_edit.setProperty("is_placeholder", False)
            text_edit.setText(text)
        
        # Style the text edit - white background, no border
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: none;
                padding: 0px;
            }
        """)
        
        # Make it auto-size to fit content
        text_edit.document().documentLayout().documentSizeChanged.connect(
            lambda: self.resize_text_edit(text_edit)
        )
        
        # Set initial height based on content
        text_edit.setMinimumHeight(25)
        text_edit.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, 
            QtWidgets.QSizePolicy.Policy.Minimum
        )
        
        # Connect link handler
        text_edit.link_clicked.connect(lambda url: handle_link_click(self.main_window, url))
        
        # Connect click handler for placeholders
        text_edit.mousePressEvent = lambda event, te=text_edit: self._handle_text_edit_click(event, te)
        
        # Connect text changed signal to check for placeholder restoration
        text_edit.textChanged.connect(lambda: self._check_text_edit_content(text_edit))
        
        # Connect focus out event to check for placeholder
        text_edit.focusOutEvent = lambda event, te=text_edit: self._handle_focus_out(event, te)
        
        # Connect our custom key press handler
        text_edit.keyPressEvent = lambda event, te=text_edit, cont=container: self._handle_key_press(event, te, cont)
        
        # Set edit mode, but don't give it focus immediately
        text_edit.set_mode("edit")
        text_edit.clearFocus()  # Force no focus so placeholder shows initially
        
        # Explicit placeholder check and force after initialization
        QtCore.QTimer.singleShot(0, lambda: self._force_placeholder_check(text_edit))
        
        container.layout().addWidget(text_edit)
        
        # Add to bullet editors
        bullet_id = f"bullet_{len(self.bullet_editors)}"
        self.bullet_editors[bullet_id] = text_edit
        
        # Resize after adding to layout
        QtCore.QTimer.singleShot(10, lambda: self.resize_text_edit(text_edit))
        
        return text_edit
    
    def _handle_text_edit_click(self, event, text_edit):
        """Handle click events on text edits, particularly for placeholders."""
        # Check if this is a placeholder that needs to be replaced
        is_placeholder = text_edit.property("is_placeholder") and text_edit.get_mode() == "edit"
        
        # Call the original event handler for link handling
        ClickableTextEdit.mousePressEvent(text_edit, event)
        
        # If it's a placeholder, replace with just bullet point and position cursor
        if is_placeholder:
            # Block signals to prevent recursive render issues
            text_edit.blockSignals(True)
            # Reset placeholder property
            text_edit.setProperty("is_placeholder", False)
            # Use setText for normal content (not HTML)
            text_edit.setText("• ")
            text_edit.blockSignals(False)
            
            # Position cursor at the end (after bullet and space)
            cursor = text_edit.textCursor()
            cursor.setPosition(2)
            text_edit.setTextCursor(cursor)
            
            # Ensure focus and visibility
            text_edit.setFocus()
            text_edit.ensureCursorVisible()
            
            # Update sizing
            self.resize_text_edit(text_edit)
            
            logger.debug("Replaced placeholder with normal bullet point on click")

    def _check_text_edit_content(self, text_edit):
        """Simple check if text edit has content beyond the bullet point to show/hide placeholder."""
        # Skip if not in edit mode or has focus (never show placeholder while focused)
        if text_edit.get_mode() != "edit" or text_edit.hasFocus():
            return
            
        # Get the actual text content
        rendered_text = text_edit.document().toPlainText().strip()
        
        # Check if there's any content after the bullet point
        if rendered_text.startswith('•'):
            content_after_bullet = rendered_text[1:].strip()
            
            # Case: Empty content and has placeholder text - need to show placeholder
            if not content_after_bullet:
                # Only set placeholder if not already showing
                if not text_edit.property("is_placeholder"):
                    text_edit.blockSignals(True)
                    text_edit.setProperty("is_placeholder", True)
                    
                    # Only use setHtml for the placeholder case
                    html = f"<div style='white-space: pre-wrap;'><p>• <i style='color: gray;'>Enter Text...</i></p></div>"
                    text_edit.setHtml(html)
                    text_edit.blockSignals(False)
                    
                    # Update size
                    self.resize_text_edit(text_edit)

    def _force_placeholder_check(self, text_edit):
        """Force the text edit to check and restore placeholder if needed."""
        # Skip if already has focus or isn't in edit mode
        if text_edit.hasFocus() or text_edit.get_mode() != "edit":
            return
            
        # Get the RENDERED text (not markdown)
        rendered_text = text_edit.document().toPlainText().strip()
        
        # Check if there's content after the bullet point
        if rendered_text.startswith('•'):
            content_after_bullet = rendered_text[1:].strip()
            
            # If nothing after bullet and we have a placeholder text
            if not content_after_bullet and hasattr(text_edit, "_placeholder_text") and text_edit._placeholder_text:
                # Force placeholder to show
                text_edit.blockSignals(True)
                text_edit._markdown_text = f"• <i style='color: gray;'>{text_edit._placeholder_text}</i>"
                text_edit.setProperty("is_placeholder", True)
                text_edit.render_text()
                text_edit.blockSignals(False)
                
                # Log placeholder restoration
                logger.debug(f"Restored placeholder for empty bullet point: {text_edit._placeholder_text}")
                
                # Resize to accommodate placeholder text
                self.resize_text_edit(text_edit)

    def _handle_focus_out(self, event, text_edit):
        """Handle focus out events to restore placeholder if needed."""
        # First, completely deactivate any active links
        self._deactivate_links(text_edit)
        
        # Call the original focus out event
        type(text_edit).focusOutEvent(text_edit, event)
        
        # Check rendered content
        self._check_text_edit_content(text_edit)
    
    def _deactivate_links(self, editor):
        """Helper function for a thorough link deactivation."""
        # Reset all link state variables
        editor._active_link_url = None
        editor._active_link_start = None
        editor._is_cursor_on_link = False
        editor._is_handling_cursor = False  # Reset handling flag too
        
        # Only do a re-render if not in the middle of another process
        if not editor._is_rendering:
            # Force text content to remain the same but links to be reset
            current_content = editor._markdown_text
            editor.blockSignals(True)
            
            # Force cursor away from any link
            c = editor.textCursor()
            c.clearSelection()
            c.movePosition(QTextCursor.MoveOperation.Start)
            editor.setTextCursor(c)
            
            # Force a clean re-render
            editor._markdown_text = current_content
            editor.render_text()
            editor.blockSignals(False)
            
            logger.debug("Link states completely reset on focus out")

    def _handle_key_press(self, event, text_edit, container):
        """Custom key press handler to support splitting text edits and navigation between bullet points."""
        # First check if this is a placeholder
        is_placeholder = text_edit.property("is_placeholder") and text_edit.get_mode() == "edit"
        if is_placeholder:
            # Replace placeholder with just a bullet point
            text_edit.blockSignals(True)
            text_edit._markdown_text = "• "
            text_edit.setProperty("is_placeholder", False)
            text_edit.setText("• ")  # Use setText instead of setHtml for better editing
            
            # Position cursor after bullet point
            cursor = text_edit.textCursor()
            cursor.setPosition(2)  # Position after bullet and space
            text_edit.setTextCursor(cursor)
            text_edit.blockSignals(False)
        
        # Handle arrow key navigation between bullet points
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
            cursor = text_edit.textCursor()
            
            # Find the current text edit's index in its container
            layout = container.layout()
            current_index = -1
            for i in range(layout.count()):
                if layout.itemAt(i).widget() == text_edit:
                    current_index = i
                    break
            
            # Helper function for a thorough link deactivation
            def deactivate_links(editor):
                # Reset all link state variables
                editor._active_link_url = None
                editor._active_link_start = None
                editor._is_cursor_on_link = False
                editor._is_handling_cursor = False  # Reset handling flag too
                
                # Force text content to remain the same but links to be reset
                current_content = editor._markdown_text
                editor.blockSignals(True)
                
                # Force cursor away from any link
                c = editor.textCursor()
                c.clearSelection()
                c.movePosition(QTextCursor.MoveOperation.Start)
                editor.setTextCursor(c)
                
                # Force a clean re-render
                editor._markdown_text = current_content
                editor.render_text()
                editor.blockSignals(False)
                
                logger.debug("Link states completely reset")
            
            # LEFT KEY - move to end of previous bullet point when at start
            if event.key() == Qt.Key.Key_Left and cursor.position() <= 2:
                if current_index > 0:
                    prev_widget = layout.itemAt(current_index - 1).widget()
                    if isinstance(prev_widget, ClickableTextEdit):
                        logger.debug("LEFT: Moving to end of previous bullet point")
                        
                        # Reset any active link state in current widget BEFORE focus change
                        self._deactivate_links(text_edit)
                        
                        # Move to previous widget
                        prev_widget.setFocus()
                        
                        # Set cursor at end of previous widget
                        end_cursor = prev_widget.textCursor()
                        end_cursor.movePosition(QTextCursor.MoveOperation.End)
                        prev_widget.setTextCursor(end_cursor)
                        prev_widget.ensureCursorVisible()
                        return
            
            # RIGHT KEY - move to start of next bullet point when at end
            elif event.key() == Qt.Key.Key_Right and cursor.atEnd():
                if current_index < layout.count() - 1:
                    next_widget = layout.itemAt(current_index + 1).widget()
                    if isinstance(next_widget, ClickableTextEdit):
                        logger.debug("RIGHT: Moving to start of next bullet point")
                        
                        # Reset any active link state in current widget
                        self._deactivate_links(text_edit)
                        
                        # Move to next widget
                        next_widget.setFocus()
                        
                        # Set cursor at beginning of next widget (after bullet)
                        start_cursor = next_widget.textCursor()
                        start_cursor.setPosition(2)  # After bullet
                        next_widget.setTextCursor(start_cursor)
                        next_widget.ensureCursorVisible()
                        return
            
            # UP KEY - move to previous bullet point
            elif event.key() == Qt.Key.Key_Up:
                # Check if we're at the first line
                cursor_pos_before = cursor.position()
                test_cursor = QTextCursor(cursor)
                test_cursor.movePosition(QTextCursor.MoveOperation.Up)
                
                # If can't move up or would go before bullet
                if test_cursor.position() < 2 or test_cursor.position() == cursor_pos_before:
                    # Try to move to previous widget
                    if current_index > 0:
                        prev_widget = layout.itemAt(current_index - 1).widget()
                        if isinstance(prev_widget, ClickableTextEdit):
                            logger.debug("UP: Moving to end of previous bullet point")
                            
                            # Reset any active link state in current widget
                            self._deactivate_links(text_edit)
                            
                            # Move to previous widget - always to the end
                            prev_widget.setFocus()
                            end_cursor = prev_widget.textCursor()
                            end_cursor.movePosition(QTextCursor.MoveOperation.End)
                            prev_widget.setTextCursor(end_cursor)
                            prev_widget.ensureCursorVisible()
                            return
                
                # If we didn't navigate, use default behavior
                ClickableTextEdit.keyPressEvent(text_edit, event)
                return
            
            # DOWN KEY - move to next bullet point
            elif event.key() == Qt.Key.Key_Down:
                # Check if we're at the last line
                cursor_pos_before = cursor.position()
                test_cursor = QTextCursor(cursor)
                test_cursor.movePosition(QTextCursor.MoveOperation.Down)
                
                # If can't move down or at end of text
                if test_cursor.position() == cursor_pos_before or cursor.atEnd():
                    # Try to move to next widget
                    if current_index < layout.count() - 1:
                        next_widget = layout.itemAt(current_index + 1).widget()
                        if isinstance(next_widget, ClickableTextEdit):
                            logger.debug("DOWN: Moving to start of next bullet point")
                            
                            # Reset any active link state in current widget
                            self._deactivate_links(text_edit)
                            
                            # Move to next widget - always to position after bullet
                            next_widget.setFocus()
                            start_cursor = next_widget.textCursor()
                            start_cursor.setPosition(2)  # After bullet point
                            next_widget.setTextCursor(start_cursor)
                            next_widget.ensureCursorVisible()
                            return
                
                # Default behavior
                ClickableTextEdit.keyPressEvent(text_edit, event)
                return
            
            # Default handling for other arrow key cases
            ClickableTextEdit.keyPressEvent(text_edit, event)
            return
        
        # Handle Backspace at position after bullet point - merge with previous bullet
        if event.key() == Qt.Key.Key_Backspace:
            cursor = text_edit.textCursor()
            if cursor.position() == 2 and not cursor.hasSelection():  # Position right after bullet
                layout = container.layout()
                
                # Find the current text edit's index
                current_index = -1
                for i in range(layout.count()):
                    if layout.itemAt(i).widget() == text_edit:
                        current_index = i
                        break
                
                # Check if there's a previous bullet point (don't delete the last bullet)
                if current_index > 0:
                    # Get the MARKDOWN text (not plain text)
                    current_md_text = text_edit._markdown_text
                    content_to_append = current_md_text[2:] if current_md_text.startswith('• ') else current_md_text
                    
                    # Get the previous bullet point
                    prev_text_edit = layout.itemAt(current_index - 1).widget()
                    
                    # Get the MARKDOWN content of the previous bullet point
                    prev_md_text = prev_text_edit._markdown_text
                    join_position = len(prev_md_text)  # Position where texts will join
                    
                    # Store the original content length before joining
                    prev_content_len = len(prev_text_edit.document().toPlainText())
                    
                    # Append the content using markdown text
                    prev_text_edit.blockSignals(True)
                    prev_text_edit._markdown_text = prev_md_text + content_to_append
                    prev_text_edit.render_text()  # Use render_text() not setText()
                    prev_text_edit.blockSignals(False)
                    
                    # Set focus to the previous bullet point
                    prev_text_edit.setFocus()
                    
                    # Position cursor at the join point - where the appended content begins
                    cursor = prev_text_edit.textCursor()
                    cursor.setPosition(prev_content_len)  # Use the actual rendered text length
                    prev_text_edit.setTextCursor(cursor)
                    prev_text_edit.ensureCursorVisible()  # Make sure the cursor is visible
                    
                    # Remove the current bullet point
                    text_edit.setParent(None)
                    text_edit.deleteLater()
                    self.resize_text_edit(prev_text_edit)
                    
                    # Remove from bullet editors
                    for key, editor in list(self.bullet_editors.items()):
                        if editor == text_edit:
                            self.bullet_editors.pop(key)
                            break
                    
                    return  # Skip normal event handling
        
        # Now handle the Enter key specifically
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Get the current content to check if it's empty
            current_text = text_edit.document().toPlainText().strip()
            
            # If content is just a bullet point or empty, ignore Enter key
            if not current_text or current_text == "•" or current_text == "• " or len(current_text.replace('•', '').strip()) == 0:
                # Do nothing - don't even pass to the original handler
                return
                
            # Handle Enter key to create a new bullet point since there's content
            self._split_bullet_point(text_edit, container)
            return
        
        # Pass other keys to the original handler
        ClickableTextEdit.keyPressEvent(text_edit, event)
    
    def _split_bullet_point(self, text_edit, container):
        """Split a bullet point at cursor position and create a new one below."""
        # Get cursor position and map to markdown position
        cursor = text_edit.textCursor()
        html_position = cursor.position()
        md_position = text_edit._map_cursor_to_markdown(html_position)
        
        # Get the current MARKDOWN text
        current_md_text = text_edit._markdown_text
        
        # Extract content before and after cursor in the markdown
        md_text_before = current_md_text[:md_position]
        md_text_after = current_md_text[md_position:]
        
        # Update the current bullet point with text before cursor
        # Keep current bullet point's leading bullet
        if not md_text_before.startswith('•'):
            md_text_before = '• ' + md_text_before
        
        # Set the MARKDOWN text for the current bullet point
        text_edit.blockSignals(True)
        text_edit._markdown_text = md_text_before
        text_edit.render_text()
        text_edit.blockSignals(False)
        
        # Create a new bullet point with the text after cursor
        # Always ensure the new text has a bullet
        if not md_text_after.startswith('•'):
            md_text_after = '• ' + md_text_after
        
        # Find the index of the current text edit in its container
        layout = container.layout()
        index = -1
        for i in range(layout.count()):
            if layout.itemAt(i).widget() == text_edit:
                index = i
                break
        
        # Create and insert the new bullet point
        new_text_edit = self.add_bullet_point_to_container(container, md_text_after)
        
        # Move the new text edit to the position right after the current one
        if index != -1:
            # Remove from current position
            layout.removeWidget(new_text_edit)
            # Insert at the position after the current text edit
            layout.insertWidget(index + 1, new_text_edit)
        
        # Set focus to the new bullet point
        new_text_edit.setFocus()
        
        # Position cursor at the beginning of the new text edit (after bullet)
        cursor = new_text_edit.textCursor()
        cursor.setPosition(2)  # After bullet and space
        new_text_edit.setTextCursor(cursor)
        
        # Resize both text edits
        self.resize_text_edit(text_edit)
        self.resize_text_edit(new_text_edit)
