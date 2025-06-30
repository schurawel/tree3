from PyQt6 import QtWidgets, QtCore, QtGui
import logging
import uuid
import asyncio
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_types_manager import NodeTypesManager
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.form_manager import FormManager
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.file_manager import FileManager
import os

# Make sure functions are explicitly exported
__all__ = ['AsyncNodeDialog', 'create_async_dialog']

logger = logging.getLogger(__name__)

class AsyncNodeDialog(QtWidgets.QDialog):
    """Asynchronous dialog for creating or editing nodes."""
    
    # Signal to notify completion
    finished = QtCore.pyqtSignal(object)
    
    def __init__(self, parent=None, mode="add", node_labels=None, node_attributes=None, selected_node_id=None):
        super().__init__(parent)
        self.parent = parent
        self.mode = mode
        self.node_labels = node_labels or {}
        self.node_attributes = node_attributes or {}
        self.selected_node_id = selected_node_id
        self.result_data = None
        self.tasks = set()
        
        # Initialize managers
        self.type_manager = NodeTypesManager(parent)
        
        # Store all node types and their parameters
        self.all_node_types = {}
        self.all_type_parameters = {}
        
        # Setup UI
        self.setup_ui()
        
        # Make dialog non-modal so it doesn't block the event loop
        self.setModal(False)
        
        # Start background tasks
        self.start_init_task(self.initialize_node_types())
        
        # If we have a specific node ID to edit, preload it
        if self.mode == "edit" and self.selected_node_id:
            self.start_init_task(self.load_selected_node())
    
    def start_init_task(self, coro):
        """Start an initialization task and track it."""
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(lambda t: self.tasks.remove(t) if t in self.tasks else None)
        return task
    
    def setup_ui(self):
        """Set up the user interface with an absolute minimal layout."""
        self.setWindowTitle(f"{self.mode.capitalize()} Node")
        self.resize(600, 500)
        
        # Create main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Node selection (edit mode)
        if self.mode == "edit" and self.node_labels:
            layout.addWidget(QtWidgets.QLabel("Select Node:"))
            self.node_dropdown = QtWidgets.QComboBox()
            
            if not self.selected_node_id:
                self.node_dropdown.addItem("-- Select a node --", None)
                
            for node_id, node_label in self.node_labels.items():
                self.node_dropdown.addItem(node_label, node_id)
            
            layout.addWidget(self.node_dropdown)
        
        # Node type section
        layout.addWidget(QtWidgets.QLabel("Node Type:"))
        self.node_type_dropdown = QtWidgets.QComboBox()
        layout.addWidget(self.node_type_dropdown)
        
        self.loading_label = QtWidgets.QLabel("Loading node types...")
        layout.addWidget(self.loading_label)
        
        # Form layout container - give it a border to make it visible
        form_container = QtWidgets.QGroupBox("Node Properties")
        self.form_layout = QtWidgets.QFormLayout(form_container)
        self.form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addWidget(form_container, 1)  # 1 = stretch factor
        
        # Button section
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Initialize managers
        self.form_manager = FormManager(self, self.form_layout)
        self.form_manager.set_edit_mode(self.mode == "edit")
        self.file_manager = FileManager(self)
        
        # Add a temporary label to ensure the form area is visible
        self.form_layout.addRow("", QtWidgets.QLabel("Loading fields...", self))
    
    def eventFilter(self, obj, event):
        """Custom event filter for better layout handling."""
        if obj == self and event.type() == QtCore.QEvent.Type.Resize:
            # Update layout on resize
            QtCore.QTimer.singleShot(10, self.updateGeometry)
        return super().eventFilter(obj, event)
    
    def sizeHint(self):
        """Give the dialog a better size hint based on content."""
        base_size = super().sizeHint()
        # Set a reasonable minimum width
        return QtCore.QSize(max(550, base_size.width()), base_size.height())
    
    # Override accept/reject to emit signals
    def accept(self):
        """Override accept to emit signal with result data."""
        self.result_data = self.get_values()
        super().accept()
        self.finished.emit(self.result_data)
        
    def reject(self):
        """Override reject to emit signal with None."""
        self.result_data = None
        super().reject()
        self.finished.emit(self.result_data)
        
    def closeEvent(self, event):
        """Handle window close event."""
        # Cancel any running tasks
        for task in list(self.tasks):
            task.cancel()
        self.tasks.clear()
        
        # If not already processed, treat as rejection
        if self.result_data is None:
            self.finished.emit(None)  # This will now work with object signal
            
        super().closeEvent(event)
    
    def on_type_changed(self, index):
        """Direct handler for node type selection changes."""
        if index < 0 or not self.node_type_dropdown.count():
            return
            
        # Get type ID
        type_id = self.node_type_dropdown.itemData(index)
        if not type_id:
            return
            
        # Log the change
        logger.info(f"Node type changed to: {self.node_type_dropdown.currentText()} (ID: {type_id})")
        
        # Skip form update for certain conditions
        # Don't update form if we're in edit mode and this update was triggered by
        # populating the form values from the backend
        if hasattr(self, 'skip_form_update') and self.skip_form_update:
            logger.info("Skipping form update due to skip_form_update flag")
            # Reset flag after use
            self.skip_form_update = False
            return
        
        # Update form immediately with cached parameters
        self.update_form_for_type(type_id)
    
    def update_form_for_type(self, type_id):
        """Update form fields for the selected node type."""
        # Make sure UI is responsive
        QtCore.QCoreApplication.processEvents()
        
        # First preserve the current name value if it exists
        name_value = None
        for i in range(self.form_layout.rowCount()):
            label_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.LabelRole)
            field_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.FieldRole)
            
            if (label_item and label_item.widget() and 
                field_item and field_item.widget() and
                label_item.widget().text().lower().startswith("name")):
                
                field_widget = field_item.widget()
                if isinstance(field_widget, QtWidgets.QLineEdit):
                    name_value = field_widget.text()
                    logger.debug(f"Preserved name value: '{name_value}'")
                    break
        
        # Clear existing form - first remove all widgets directly
        self.form_manager.clear_form()
        logger.debug(f"Form cleared for type_id: {type_id}")
        
        # Force immediate UI update
        QtCore.QCoreApplication.processEvents()
        
        # Add fields from cached parameters
        if type_id in self.all_type_parameters:
            parameters = self.all_type_parameters[type_id].copy()
            logger.debug(f"Adding {len(parameters)} parameters for type {type_id}")
            
            # Check if namespaces parameter already exists
            has_namespaces = any(
                isinstance(p, dict) and p.get('name', '').lower() == 'namespaces'
                for p in parameters
            )
            
            # If not, add it
            if not has_namespaces:
                logger.info(f"Adding missing namespaces parameter to {type_id} node")
                namespace_param = {
                    "name": "namespaces",
                    "type": "list",
                    "display_name": "Namespaces",
                    "description": "List of namespaces",
                    "ui_element": "tags",
                    "default_value": []
                }
                parameters.append(namespace_param)
            
            # Sort parameters to ensure 'name' comes first
            sorted_parameters = sorted(
                parameters, 
                key=lambda p: 0 if isinstance(p, dict) and p.get('name', '').lower() == 'name' else 1
            )
            
            for param in sorted_parameters:
                # Add parameter to form if it's valid
                if isinstance(param, dict) and "name" in param:
                    # Special handling for name field to preserve value
                    if param["name"].lower() == "name" and name_value:
                        logger.debug(f"Adding name field with preserved value: {name_value}")
                        self.form_manager.add_form_field(param, name_value)
                        continue
                    
                    # For other fields, use default values    
                    default_value = param.get("default_value", None)
                    logger.debug(f"Adding field {param['name']} with default: {default_value}")
                    self.form_manager.add_form_field(param, default_value)
        else:
            # Always add a name field as fallback
            name_param = {"name": "name", "display_name": "Name", "type": "string", "required": True}
            logger.debug(f"Adding fallback name field with value: {name_value}")
            self.form_manager.add_form_field(name_param, name_value)
            
            # Always add namespaces field
            namespace_param = {
                "name": "namespaces",
                "type": "list",
                "display_name": "Namespaces",
                "description": "List of namespaces",
                "ui_element": "tags",
                "default_value": []
            }
            self.form_manager.add_form_field(namespace_param, None)
        
        # Force layout update after form population and ensure it's visible
        QtCore.QCoreApplication.processEvents()
        self.form_layout.update()
        self.adjustSize()
    
    async def initialize_node_types(self):
        """Load all node types and their parameters at startup."""
        # Show loading indicator
        self.node_type_dropdown.setEnabled(False)
        self.loading_label.setVisible(True)
        
        try:
            # Create a local communication instance for API calls
            from ResearchGuidePackage.FrontendModule.client import APIClient
            comm = APIClient()
            
            # Get all node types
            success, content, error = await comm.request_and_get_response(
                operation="get_node_types",
                params={},
                sender="Frontend"
            )
            
            # Clear previous dropdown items
            if success and content and "result" in content:
                # Store all node types
                self.all_node_types = content["result"]
                self.node_type_dropdown.clear()
                
                # Add node types to dropdown, excluding metadata from the result if available
                for type_id, type_info in self.all_node_types.items():
                    # Skip the metadata section - it's not a real node type
                    if type_id == "_metadata":
                        continue
                    type_name = type_info.get("name", type_id)
                    
                    # Extract parameters directly from the result if available
                    if "parameters" in type_info:
                        self.all_type_parameters[type_id] = type_info["parameters"]
                        logger.info(f"Got {len(type_info['parameters'])} parameters for type {type_id} directly")
                    else:
                        # Default empty parameters if none are found
                        self.all_type_parameters[type_id] = []
                    
                    self.node_type_dropdown.addItem(type_name, type_id)
                
                # Enable dropdown and select first item
                self.node_type_dropdown.setEnabled(True)
                self.loading_label.setVisible(False)
                self.on_type_changed(0)
                if self.node_type_dropdown.count() > 0:
                    # NOW connect the signal AFTER initialization
                    self.node_type_dropdown.currentIndexChanged.connect(self.on_type_changed)
                    
                    # THEN update form for initial selection
                    self.on_type_changed(0)
                    
                    # If in edit mode, also connect the node dropdown signal
                    if self.mode == "edit" and self.node_labels and hasattr(self, "node_dropdown"):
                        self.node_dropdown.currentIndexChanged.connect(self.update_form_for_selected_node)
                    
                    # Force layout updates after form is populated
                    self.form_layout.update()
                    self.adjustSize()
                    self.updateGeometry()
            else:
                logger.error(f"Failed to get node types: {error}")
                self.loading_label.setText("Failed to load node types")
                self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(False)
                self.node_type_dropdown.clear()
        except Exception as e:
            logger.error(f"Error initializing node types: {e}")
            self.loading_label.setText(f"Error: {str(e)} - Using default node type")
            self.node_type_dropdown.clear()
            self.node_type_dropdown.addItem("Document", "document")
            self.all_type_parameters["document"] = [
                {"name": "name", "display_name": "Name", "type": "string", "required": True}
            ]
            self.node_type_dropdown.setEnabled(True)
            self.loading_label.setVisible(False)
            self.on_type_changed(0)
    
    def update_form_for_selected_node(self):
        """Update form fields based on selected node."""
        selected_node_id = self.node_dropdown.currentData()
        
        # Enable/disable OK button based on whether a real node is selected
        if hasattr(self, 'button_box'):
            self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(selected_node_id is not None)
        
        if not selected_node_id:
            # Clear the form if the placeholder or no node is selected
            self.form_manager.clear_form()
            return
        
        # Ensure node_id is a string
        if isinstance(selected_node_id, uuid.UUID):
            selected_node_id = str(selected_node_id)
        
        # Log the selected node
        logger.info(f"Loading attributes for node: {selected_node_id}")
        
        # Start task to get node attributes
        asyncio.create_task(self.populate_form_for_node(selected_node_id))
    async def load_selected_node(self):
        """
        Load data for the selected node from backend and populate form fields.
        Called automatically when a specific node ID is provided for editing.
        """
        if not self.selected_node_id:
            logger.warning("No node ID provided to load")
            return False
            
        try:
            from ResearchGuidePackage.FrontendModule.client import APIClient
            comm = APIClient()
            
            logger.info(f"Loading node {self.selected_node_id} from backend")
            success, content, error = await comm.request_and_get_response(
                operation="get_node",
                params={"node_id": self.selected_node_id},
                sender="NodeDialog"
            )
            
            if not success or not content.get("result"):
                logger.error(f"Failed to load node: {error or 'Unknown error'}")
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to load node data: {error or 'Unknown error'}"
                )
                return False
                
            node_data = content.get("result", {})
            if not node_data:
                logger.error("Empty node data received")
                return False

            # Store the node data
            self.node_attributes[self.selected_node_id] = node_data

            # Ensure node types are loaded before populating the form
            # Wait for node types to be initialized if not already
            if not self.all_type_parameters:
                logger.info("Waiting for node types to be loaded before populating form")
                for _ in range(30):  # Wait up to ~3 seconds
                    await asyncio.sleep(0.1)
                    if self.all_type_parameters:
                        break

            # Set node type dropdown to match node's type
            node_type = node_data.get("node_type", "document")
            for i in range(self.node_type_dropdown.count()):
                if self.node_type_dropdown.itemData(i) == node_type:
                    self.skip_form_update = True
                    self.node_type_dropdown.setCurrentIndex(i)
                    break

            # Now populate the form with node attributes
            return await self.populate_form_for_node(self.selected_node_id)
            
        except Exception as e:
            logger.error(f"Error loading selected node: {e}", exc_info=True)
            return False
            
    async def populate_form_for_node(self, node_id):
        """Populate form fields with node attributes."""
        try:
            if not node_id or node_id not in self.node_attributes:
                logger.error(f"No attributes found for node {node_id}")
                return False
                
            # Get the attributes
            attributes = self.node_attributes[node_id]
            logger.info(f"Populating form with attributes for node {node_id}: {list(attributes.keys())}")
            
            # Clear the form first
            self.form_manager.clear_form()
            
            # Get node type and update form fields based on it
            node_type = attributes.get("node_type", "document")
            logger.info(f"Node type for form population: {node_type}")
            
            # Get parameters for this type
            if node_type in self.all_type_parameters:
                parameters = self.all_type_parameters[node_type]
                
                # Create a set of parameter names defined for this node type (case insensitive)
                allowed_param_names = {param.get("name", "").lower() for param in parameters if isinstance(param, dict)}
                logger.debug(f"Allowed parameters for {node_type}: {allowed_param_names}")
                
                # Add fields based on parameters defined for this node type
                for param in parameters:
                    if isinstance(param, dict) and "name" in param:
                        param_name = param["name"].lower()
                        # Use value from attributes if available, otherwise use default
                        value = None
                        
                        # Look for attribute with matching name (case-insensitive)
                        for attr_name, attr_value in attributes.items():
                            if attr_name.lower() == param_name:
                                value = attr_value
                                break
                        
                        # If still no value found, use default
                        if value is None:
                            value = param.get("default_value")
                            
                        # Add the parameter field to the form
                        self.form_manager.add_form_field(param, value)
                
                # Add node ID field at the top if we're in edit mode
                if self.selected_node_id:
                    self.form_manager.add_node_id_field(self.selected_node_id)
                
                # Force layout update
                self.form_layout.update()
                self.adjustSize()
                return True
            else:
                logger.warning(f"No parameters found for node type: {node_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error populating form: {e}", exc_info=True)
            return False

    def get_values(self):
        """Get all values from form fields."""
        values = {}
        try:
            for i in range(self.form_layout.rowCount()):
                label_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.LabelRole)
                field_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.ItemRole.FieldRole)
                
                if label_item and label_item.widget() and field_item and field_item.widget():
                    label = label_item.widget().text().strip()
                    field = field_item.widget()
                    
                    # Special handling for list fields (tags)
                    if isinstance(field, QtWidgets.QLineEdit) and field.property("ui_element") == "tags":
                        # Split by comma and strip spaces
                        value = [v.strip() for v in field.text().split(",") if v.strip()]
                        values[label] = value
                    else:
                        # Regular field, just get the text
                        values[label] = field.text()
        
        except Exception as e:
            logger.error(f"Error getting values from form: {e}", exc_info=True)
        
        logger.info(f"Form values: {values}")
        return values

# Define create_async_dialog at module level (not inside a class or conditional block)
async def create_async_dialog(parent, mode="add", node_labels=None, node_attributes=None, selected_node_id=None):
    """Create and show an async node dialog with minimal layout processing."""
    try:
        dialog = AsyncNodeDialog(parent, mode, node_labels, node_attributes, selected_node_id)
        future = asyncio.Future()
        dialog.finished.connect(lambda result: future.set_result(result) 
                            if not future.done() else None)
        
        # Show immediately - no extra processing
        dialog.show()
        QtCore.QCoreApplication.processEvents()
        return await future
    except Exception as e:
        QtWidgets.QMessageBox.critical(parent, "Error", f"Error creating dialog: {e}")
        logger.error(f"Error in create_async_dialog: {e}", exc_info=True)
        return None

# Add fallback for non-async usage
def create_dialog(*args, **kwargs):
    """Synchronous version that raises an error to guide developers to use the async version."""
    raise RuntimeError(
        "create_dialog() has been replaced with async create_async_dialog(). " 
        "Please use the async version with 'await create_async_dialog(...)'"
    )
