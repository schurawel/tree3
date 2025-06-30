import logging
from PyQt6 import QtWidgets, QtCore, QtGui
import os

logger = logging.getLogger(__name__)

class FormManager:
    """Manages form field creation, updates, and value extraction."""
    
    def __init__(self, parent, form_layout):
        """Initialize the form manager."""
        self.parent = parent
        self.form_layout = form_layout
        self.file_fields = {}  # Keep track of file fields for special handling
        self.edit_mode = False  # Track whether we're in edit mode

    def set_edit_mode(self, is_edit_mode):
        """Set whether the form is in edit mode."""
        self.edit_mode = is_edit_mode
    
    def clear_form(self):
        """Clear all form fields thoroughly."""
        # First get the current row count
        row_count = self.form_layout.rowCount()
        
        # Remove rows from the bottom up to avoid index issues
        for i in range(row_count-1, -1, -1):
            # Get widgets at this row
            label_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.LabelRole)
            field_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.FieldRole)
            
            # Clean up widgets
            for item in [label_item, field_item]:
                if item and item.widget():
                    widget = item.widget()
                    widget.setParent(None)
                    widget.deleteLater()
            
            # Remove row from layout
            self.form_layout.removeRow(i)
        
        # Reset file fields dictionary
        self.file_fields = {}
        
        # Force immediate UI update
        QtCore.QCoreApplication.processEvents()
        logger.debug(f"Form cleared - removed {row_count} rows")
    
    def add_form_field(self, param, initial_value=None):
        """Add a form field based on parameter definition."""
        # Validate the parameter has required fields
        if not isinstance(param, dict) or "name" not in param:
            logger.error(f"Invalid parameter format: {param}")
            return None, None
        
        # Set default display name if not provided and ensure it's proper
        if "display_name" not in param:
            param["display_name"] = param["name"].capitalize()
        display_name = param["display_name"]
        
        # Ensure label text is clean and consistent
        label_text = f"{display_name}:"
        label = QtWidgets.QLabel(label_text, self.parent)
        
        if param.get("required", False):
            font = label.font()
            font.setBold(True)
            label.setFont(font)
        
        # Choose appropriate field type
        field_type = param.get("type", "string").lower()
        
        # Use initial_value if provided, otherwise use default from parameter definition
        value = initial_value if initial_value is not None else param.get("default_value")
        
        # Create appropriate widget based on UI element type and parameter type
        ui_element = param.get("ui_element", "").lower()
        field_type = param.get("type", "string").lower()
        
        # Debug logging to help identify issues
        logger.debug(f"Adding field: name={param['name']}, type={field_type}, ui_element={ui_element}, edit_mode={self.edit_mode}")
        logger.debug(f"Field value: {value}")
        
        # Check for file type fields specifically - both from ui_element and field_type
        is_file_field = (ui_element == "file_upload" or field_type == "file" or param['name'].lower() == 'file_path')
        
        # Use UI element if specified, otherwise fall back to field type
        if ui_element == "textarea":
            input_field = QtWidgets.QTextEdit(self.parent)
            if value:
                input_field.setPlainText(str(value))
        elif ui_element == "dropdown" and "options" in param:
            input_field = QtWidgets.QComboBox(self.parent)
            for option in param.get("options", []):
                input_field.addItem(str(option))
            if value:
                index = input_field.findText(str(value))
                if index >= 0:
                    input_field.setCurrentIndex(index)
        elif is_file_field:
            # Enhanced file field handling with proper existence check
            file_exists = False
            if value and value != "Select File":
                # Check if the file exists in the database
                file_exists = self.check_file_exists_in_backend(value)
                logger.info(f"File field check: path={value}, exists={file_exists}")
            
            if self.edit_mode and file_exists:
                # We're in edit mode and have an existing file
                # Create a container for file controls
                file_container = QtWidgets.QWidget(self.parent)
                file_layout = QtWidgets.QVBoxLayout(file_container)
                file_layout.setSpacing(5)
                file_layout.setContentsMargins(0, 0, 0, 0)
                
                # Add current file info
                file_info = QtWidgets.QLabel(f"Current file: {os.path.basename(value)}", self.parent)
                file_layout.addWidget(file_info)
                
                # Add buttons container
                buttons_container = QtWidgets.QWidget(self.parent)
                buttons_layout = QtWidgets.QHBoxLayout(buttons_container)
                buttons_layout.setContentsMargins(0, 0, 0, 0)
                buttons_layout.setSpacing(10)
                
                # Add replace button
                replace_button = QtWidgets.QPushButton("Replace File", self.parent)
                replace_button.clicked.connect(lambda: self.handle_file_action("replace", param["name"], value))
                buttons_layout.addWidget(replace_button)
                
                # Add download button
                download_button = QtWidgets.QPushButton("Download File", self.parent)
                download_button.clicked.connect(lambda: self.handle_file_action("download", param["name"], value))
                buttons_layout.addWidget(download_button)
                
                file_layout.addWidget(buttons_container)
                input_field = file_container
                
                # Register this field for later access
                self.file_fields[param["display_name"]] = {
                    "path": value,
                    "replace_button": replace_button,
                    "download_button": download_button,
                    "info_label": file_info
                }
                
                logger.info(f"Created replace/download buttons for existing file: {value}")
            else:
                # Regular file selection (no existing file or add mode)
                input_field = QtWidgets.QPushButton("Select File", self.parent)
                if value and value != "Select File":
                    input_field.setText(str(value))
                    
                # Register this field for later access
                self.file_fields[param["display_name"]] = input_field
                
                # Connect to file dialog
                input_field.clicked.connect(self.select_file)
                
                logger.info(f"Created upload file button (edit_mode={self.edit_mode}, file_exists={file_exists})")
        elif ui_element == "date_picker" or field_type == "date":
            input_field = QtWidgets.QDateEdit(self.parent)
            input_field.setCalendarPopup(True)
            if value:
                input_field.setDate(QtCore.QDate.fromString(str(value), QtCore.Qt.DateFormat.ISODate))
        elif ui_element == "tags":
            input_field = QtWidgets.QLineEdit(self.parent)
            if value:
                input_field.setText(str(value))
            # Add placeholder text
            input_field.setPlaceholderText("Comma.separated, Name.Spaces")
            
            # Check if this is a namespaces field
            if param["name"].lower() == "namespaces":
                # Add tooltip for namespaces field with explanation about quotes
                input_field.setToolTip("Enter namespaces separated by commas.\n"
                                      "Example: research.papers,tech.ai,project.2023\n\n"
                                      "For namespaces with spaces or dots, use quotes:\n"
                                      "'Research Papers','tech.examples.2023'\n\n"
                                      "Namespaces can be used to organize and filter nodes.")
                # Style to show it's special (optional light blue background)
        elif ui_element == "slider" and field_type in ["int", "float"]:
            input_field = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self.parent)
            input_field.setRange(param.get("min_value", 0), param.get("max_value", 100))
            if value is not None:
                try:
                    input_field.setValue(int(value))
                except (ValueError, TypeError):
                    pass
            # Add value label
            value_label = QtWidgets.QLabel(str(input_field.value()), self.parent)
            input_field.valueChanged.connect(lambda val, label=value_label: label.setText(str(val)))
            # Create a container for slider and value
            container = QtWidgets.QWidget(self.parent)
            container_layout = QtWidgets.QHBoxLayout(container)
            container_layout.addWidget(input_field)
            container_layout.addWidget(value_label)
            input_field = container
        elif ui_element == "checkbox" or field_type == "bool":
            input_field = QtWidgets.QCheckBox(self.parent)
            if value is not None:
                input_field.setChecked(bool(value))
        elif ui_element == "email":
            input_field = QtWidgets.QLineEdit(self.parent)
            if value:
                input_field.setText(str(value))
            # Add validation for email format
            input_field.setPlaceholderText("example@example.com")
        elif field_type == "string":
            input_field = QtWidgets.QLineEdit(self.parent)
            if initial_value is not None:
                input_field.setText(str(initial_value))
                logger.debug(f"Set text for {param['name']}: '{initial_value}'")
            else:
                # Set empty string explicitly to avoid "None" showing up
                input_field.setText("")
                
            # Check specifically for namespaces field
            if param["name"].lower() == "namespaces":
                # Add tooltip for namespaces field
                input_field.setToolTip("Enter namespaces separated by commas.\n"
                                      "Example: research.papers,tech.ai,project.2023\n\n"
                                      "Namespaces can be used to organize and filter nodes.")
        elif field_type == "int":
            input_field = QtWidgets.QSpinBox(self.parent)
            input_field.setRange(param.get("min_value", -2147483648), param.get("max_value", 2147483647))
            if value is not None:
                try:
                    input_field.setValue(int(value))
                except (ValueError, TypeError):
                    pass
        elif field_type == "float":
            input_field = QtWidgets.QDoubleSpinBox(self.parent)
            input_field.setRange(param.get("min_value", -1e10), param.get("max_value", 1e10))
            if value is not None:
                try:
                    input_field.setValue(float(value))
                except (ValueError, TypeError):
                    pass
        else:
            # Default to text field
            input_field = QtWidgets.QLineEdit(self.parent)
            if value:
                input_field.setText(str(value))
        
        # Add styling to input field
        if isinstance(input_field, QtWidgets.QLineEdit):
            input_field.setMinimumWidth(200)
        elif isinstance(input_field, QtWidgets.QTextEdit):
            input_field.setMinimumHeight(80)
        elif isinstance(input_field, QtWidgets.QComboBox):
            input_field.setMinimumWidth(200)
        
        # Add to layout - simple approach
        self.form_layout.addRow(label, input_field)
        QtCore.QCoreApplication.processEvents()
        
        return label, input_field

    def select_file(self):
        """Open file dialog when file button is clicked."""
        # Get the button that triggered the signal
        button = self.parent.sender()
        
        # Ensure it's a button before proceeding
        if not isinstance(button, QtWidgets.QPushButton):
            logger.error(f"select_file called with invalid button type: {type(button)}")
            return
        
        file_dialog = QtWidgets.QFileDialog(self.parent)
        file_path, _ = file_dialog.getOpenFileName()
        if file_path:
            button.setText(file_path)
    
    def handle_file_action(self, action, field_name, file_path):
        """Handle file actions: replace or download."""
        logger.info(f"File action: {action} for field {field_name}, path: {file_path}")
        
        if not hasattr(self.parent, "file_manager"):
            logger.error("Parent has no file_manager")
            return
            
        file_manager = self.parent.file_manager
        node_id = self.parent.get_selected_node_id() if hasattr(self.parent, "get_selected_node_id") else None
        
        logger.info(f"Node ID for file action: {node_id}")
        
        if action == "replace":
            # Replace will call file_manager.replace_file which now handles upload immediately
            success = file_manager.replace_file(node_id)
            if success and field_name in self.file_fields:
                if isinstance(self.file_fields[field_name], dict) and "info_label" in self.file_fields[field_name]:
                    new_file = file_manager.get_file_updates().get("file_path", "")
                    if new_file:
                        self.file_fields[field_name]["info_label"].setText(f"Replacing with: {os.path.basename(new_file)}")
                        logger.info(f"Updated info label for replacement: {os.path.basename(new_file)}")
        
        elif action == "download":
            # Download happens immediately when button is pressed
            logger.info(f"Initiating download for node {node_id}, file {file_path}")
            file_manager.download_file(node_id, file_path)
    
    def get_values(self):
        """Get values from all form fields."""
        values = {}
        
        # Get values from form fields
        for i in range(self.form_layout.rowCount()):
            # Add null checks to prevent NoneType errors
            label_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.LabelRole)
            field_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.FieldRole)
            
            if label_item is None or field_item is None:
                logger.warning(f"Missing form item at row {i}")
                continue
                
            label_widget = label_item.widget()
            field_widget = field_item.widget()
            
            if label_widget is None or field_widget is None:
                logger.warning(f"Missing widget at row {i}")
                continue
            
            label_text = label_widget.text().strip(':')
            field_value = None
            
            # Get the field value based on widget type
            if isinstance(field_widget, QtWidgets.QLineEdit):
                field_value = field_widget.text()
            elif isinstance(field_widget, QtWidgets.QTextEdit):
                field_value = field_widget.toPlainText()
            elif isinstance(field_widget, QtWidgets.QSpinBox):
                field_value = field_widget.value()
            elif isinstance(field_widget, QtWidgets.QDoubleSpinBox):
                field_value = field_widget.value()
            elif isinstance(field_widget, QtWidgets.QCheckBox):
                field_value = field_widget.isChecked()
            elif isinstance(field_widget, QtWidgets.QDateEdit):
                field_value = field_widget.date().toString(QtCore.Qt.DateFormat.ISODate)
            elif isinstance(field_widget, QtWidgets.QComboBox):
                field_value = field_widget.currentText()
            elif isinstance(field_widget, QtWidgets.QPushButton):
                field_value = field_widget.text()
            elif isinstance(field_widget, QtWidgets.QWidget) and field_widget.layout():
                # Handle compound widgets like the slider+label
                slider = field_widget.layout().itemAt(0).widget()
                if isinstance(slider, QtWidgets.QSlider):
                    field_value = slider.value()
            
            # Special handling for namespaces field - SIMPLIFIED VERSION
            if field_value is not None and label_text.lower() in ['namespaces', 'namespace']:
                if isinstance(field_value, str):
                    logger.info(f"Processing namespaces field: '{field_value}'")
                    
                    # Simply split by commas and create a list of trimmed namespaces
                    # This matches how namespace_viewer.py expects the data
                    namespaces = [ns.strip() for ns in field_value.split(',') if ns.strip()]
                    field_value = namespaces
                    logger.info(f"Processed namespaces as list: {field_value}")
            
            if field_value is not None:
                values[label_text] = field_value
        
        # Process any file fields specially to ensure they're included
        for field_name, field_data in self.file_fields.items():
            # Convert field name format (e.g., "File Path" -> "file_path")
            field_key = field_name.lower().replace(' ', '_')
            
            # Handle both regular file buttons and compound file widgets
            if isinstance(field_data, dict) and "path" in field_data:
                # For edit mode with existing files
                values[field_key] = field_data["path"]
            elif isinstance(field_data, QtWidgets.QPushButton):
                # For add mode or edit mode with no existing file
                file_path = field_data.text()
                if file_path and file_path != "Select File":
                    values[field_key] = file_path
        
        logger.info(f"Collected form values: {values}")
        return values

    def check_file_exists_in_backend(self, file_path):
        """Check if the file exists in the backend database."""
        # Skip file system check, always use database check
        
        # For paths that might be in the database,
        # we need to first check if this seems like a valid path
        if not file_path or len(file_path) < 5:  # Simple validation
            return False
            
        # We'll need to use a communication channel to actually check the database
        # Since we can't make async calls here, we'll assume the database has the file
        # if the file_path looks valid
        return True

    def add_node_id_field(self, node_id):
        """Add a node ID field with a copy button."""
        if not node_id:
            return None, None
            
        # Create a container for the ID and copy buttons
        container = QtWidgets.QWidget(self.parent)
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a read-only line edit for the ID
        id_field = QtWidgets.QLineEdit(self.parent)
        id_field.setText(str(node_id))
        id_field.setReadOnly(True)
        
        # Create a copy button
        copy_button = QtWidgets.QPushButton("Copy ID", self.parent)
        copy_button.setToolTip("Copy node ID to clipboard")
        copy_button.clicked.connect(lambda: self.copy_to_clipboard(str(node_id)))
        
        # Create a copy link button
        copy_link_button = QtWidgets.QPushButton("Copy Link", self.parent)
        copy_link_button.setToolTip("Copy markdown link [title](node_id) to clipboard")
        copy_link_button.clicked.connect(lambda: self.copy_link_to_clipboard(str(node_id)))
        
        # Add widgets to layout
        layout.addWidget(id_field, 1)  # 1 = stretch factor
        layout.addWidget(copy_button)
        layout.addWidget(copy_link_button)
        
        # Add to form layout
        label = QtWidgets.QLabel("Node ID:", self.parent)
        self.form_layout.insertRow(0, label, container)
        
        return label, container

    def copy_link_to_clipboard(self, node_id):
        """Copy markdown link [title](node_id) to clipboard and show feedback."""
        # Get title directly from node attributes or use node_id as fallback
        title = None
        
        # Check if parent has direct access to node attributes
        if hasattr(self.parent, 'node_attributes'):
            # node_attributes is a dictionary with node_id as key
            if node_id in self.parent.node_attributes:
                # Get the attributes dictionary for this specific node
                attributes = self.parent.node_attributes[node_id]
                
                # Determine the node type
                node_type = attributes.get('node_type', '')
                
                # Choose the appropriate attribute based on node type
                if node_type == 'page':
                    title = attributes.get('title')
                elif node_type == 'text_block':
                    content = attributes.get('content', '')
                    if content and len(content) > 30:
                        title = content[:27] + '...'
                    else:
                        title = content
                else:
                    # First try name, then title for most node types
                    title = attributes.get('name') or attributes.get('title')
        
        # If no title found, use node_id as fallback
        if not title or not isinstance(title, str) or not title.strip():
            title = node_id
        
        # Format markdown link
        link_text = f"[{title}]({node_id})"
        
        # Copy to clipboard
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(link_text)
        
        # Get the button that was clicked
        button = self.parent.sender()
        if not isinstance(button, QtWidgets.QPushButton):
            logger.warning(f"copy_link_to_clipboard called from non-button object: {type(button)}")
            return
            
        # Store the original text and show confirmation
        original_text = button.text()
        button.setText("Copied!")
        
        # Reset button text after short delay
        QtCore.QTimer.singleShot(1500, lambda btn=button: btn.setText(original_text))
        
        logger.info(f"Copied link to clipboard: {link_text}")

    def copy_to_clipboard(self, text):
        """Copy text to clipboard and show feedback."""
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(text)
        
        # Get the button that was clicked
        button = self.parent.sender()
        if not isinstance(button, QtWidgets.QPushButton):
            logger.warning(f"copy_to_clipboard called from non-button object: {type(button)}")
            return
            
        # Store the original text and show confirmation
        original_text = button.text()
        button.setText("Copied!")
        
        # Reset button text after short delay, using captured reference to button
        QtCore.QTimer.singleShot(1500, lambda btn=button: btn.setText(original_text))
        
        logger.info(f"Copied to clipboard: {text}")
    
    def has_field(self, field_name):
        """
        Check if a field with the given name already exists in the form.
        
        Args:
            field_name (str): The name of the field to check
            
        Returns:
            bool: True if the field exists, False otherwise
        """
        # Normalize field name for comparison (lowercase, no colons)
        normalized_name = field_name.lower().rstrip(':')
        
        # Check all rows in the form
        for i in range(self.form_layout.rowCount()):
            label_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.LabelRole)
            if label_item and label_item.widget():
                # Get the label text and normalize it
                label_text = label_item.widget().text().lower().rstrip(':')
                
                # Check if the normalized names match
                if label_text == normalized_name:
                    return True
                    
        return False
