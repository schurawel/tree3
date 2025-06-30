"""
Node Editor Tab
==============
A tab-based wrapper for the existing node editor dialog.
"""
import logging
import asyncio
import uuid
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import pyqtSignal, QTimer

from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_dialog import AsyncNodeDialog
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_operations import create_node_in_backend, edit_node_in_backend
from ResearchGuidePackage.FrontendModule.client import APIClient

logger = logging.getLogger(__name__)

class NodeEditorTab(QWidget):
    """Tab wrapper for the node editor dialog."""
    
    operation_completed = pyqtSignal(object)  # Signal emitted when operation completes
    
    def __init__(self, main_window, mode="add", node_id=None):
        """
        Initialize the node editor tab.
        
        Args:
            main_window: Reference to the main window
            mode: Either "add" or "edit"
            node_id: For edit mode, the ID of the node to edit
        """
        super().__init__()
        self.main_window = main_window
        self.mode = mode
        self.node_id = node_id
        self.dialog = None
        self.result = None
        
        # Set up UI
        self.setup_ui()
        
        # Initialize the dialog
        self.initialize_dialog()
        
    def setup_ui(self):
        """Set up the tab layout."""
        # Main layout with margins for spacing
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Create header section - title on left, buttons on right
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        # Title on the left
        self.title_label = QLabel("Add Object" if self.mode == "add" else "Edit Object")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch(1)  # Push buttons to the right
        
        # Buttons on the right
        buttons_layout = QHBoxLayout()
        
        # Add Remove button only in edit mode
        if self.mode == "edit":
            self.remove_button = QPushButton("Remove")
            self.remove_button.setMinimumWidth(80)
            self.remove_button.setStyleSheet("background-color: #d9534f; color: white;")
            self.remove_button.clicked.connect(self.confirm_remove)
            buttons_layout.addWidget(self.remove_button)
        
        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.setMinimumWidth(80)
        self.save_button.clicked.connect(self.save_changes)
        buttons_layout.addWidget(self.save_button)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(80)
        self.cancel_button.clicked.connect(self.cancel_edit)
        buttons_layout.addWidget(self.cancel_button)
        
        header_layout.addLayout(buttons_layout)
        self.layout.addLayout(header_layout)
        
        # Horizontal line divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(line)
        
        # Container widget to center the form and limit its width
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 10, 0, 0)
        
        # This will hold the dialog
        self.dialog_container = QWidget()
        dialog_layout = QVBoxLayout(self.dialog_container)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.dialog_container)
        
        # Set maximum width for the form
        center_container.setMaximumWidth(800)
        
        # Add spacers on left and right to center the container
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(center_container)
        h_layout.addStretch(1)
        
        self.layout.addLayout(h_layout, 1)  # 1 = stretch factor
        
        # Add status label at bottom
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        self.layout.addWidget(self.status_label)
    
    def initialize_dialog(self):
        """Create and embed the dialog."""
        # Start a task to fetch node data and create the dialog
        asyncio.create_task(self._setup_dialog())
    
    async def _setup_dialog(self):
        """Asynchronously set up the node editor dialog."""
        try:
            # For edit mode, we need to fetch node data first
            node_labels = {}
            node_attributes = {}
            
            if self.mode == "edit" and self.node_id:
                # Create API client instance
                client = APIClient()
                
                # Fetch node data
                success, content, error = await client.request_and_get_response(
                    operation="get_nodes",
                    params={},
                    sender="Frontend"
                )
                
                if success and content and "result" in content and "nodes" in content["result"]:
                    nodes = content["result"]["nodes"]
                    
                    # Find our specific node
                    target_node_id = str(self.node_id)
                    for node in nodes:
                        if str(node.get("id")) == target_node_id:
                            # Make a clean copy and filter out system attributes
                            node_data = {}
                            excluded_fields = ['id', '_id', 'node_id', 'pos', 'position', 'index', 'status']
                            for k, v in node.items():
                                if k not in excluded_fields:
                                    node_data[k] = v
                            
                            # Store node data
                            label = node_data.get("label", node_data.get("name", str(self.node_id)))
                            node_labels = {str(self.node_id): label}
                            node_attributes = {str(self.node_id): node_data}
                            break
            
            # Create the node dialog - using the existing AsyncNodeDialog
            self.dialog = AsyncNodeDialog(
                parent=self.main_window,
                mode=self.mode,
                node_labels=node_labels,
                node_attributes=node_attributes,
                selected_node_id=self.node_id if self.mode == "edit" else None
            )
            
            # Remove window decoration since we're in a tab
            self.dialog.setWindowFlags(self.dialog.windowFlags() & ~self.dialog.windowType())
            
            # Remove dialog's button box since we have our own buttons
            if hasattr(self.dialog, 'button_box'):
                self.dialog.button_box.setParent(None)
                self.dialog.button_box.deleteLater()
            
            # Update title in our header if available
            if self.node_id and hasattr(self, 'title_label'):
                node_name = ""
                if node_attributes and str(self.node_id) in node_attributes:
                    attr = node_attributes[str(self.node_id)]
                    node_name = attr.get("name", attr.get("title", ""))
                
                if node_name:
                    self.title_label.setText(f"Edit Object: {node_name}")
            
            # Add dialog to our container
            self.dialog_container.layout().addWidget(self.dialog)
            
            # Show dialog within the tab
            self.dialog.show()
            
        except Exception as e:
            logger.error(f"Error setting up node editor dialog: {e}")
            self.status_label.setText(f"Error: {e}")
    
    def _on_dialog_finished(self, values):
        """Handle dialog completion."""
        if values is None:
            # Dialog was cancelled
            self.operation_completed.emit({"action": "cancel"})
            # Close the tab after a short delay
            QTimer.singleShot(300, self.close_tab)
            return
        
        # Store the result
        self.result = values
        
        # Process based on mode
        if self.mode == "add":
            # Get name from values
            name = None
            for key, value in list(values.items()):
                if key.lower() == "name":
                    name = value
                    break
            
            if not name:
                name = f"New {values.get('node_type', 'Document').capitalize()} Node"
            
            # Start create task - result will trigger tab closing
            asyncio.create_task(self._create_node(values, name))
        else:  # edit mode
            # Get node ID
            node_id = values.get("node_id") or self.node_id
            if not node_id:
                self.operation_completed.emit({"action": "error", "error": "No node ID provided"})
                return
            
            # Start update task - result will trigger tab closing
            asyncio.create_task(self._update_node(values, node_id))
    
    async def _create_node(self, values, name):
        """Create a new node using the existing backend logic."""
        try:
            # Validate essential values
            node_type = values.pop("node_type", "document")
            if not name or not name.strip():
                self.status_label.setText("Error: Node name cannot be empty")
                return
            
            # Get color based on node type
            from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_types_manager import NodeTypesManager
            type_manager = NodeTypesManager(self.main_window)
            color = await type_manager.get_default_color(node_type)
            
            # If no color from backend, use a default
            if not color:
                color = "skyblue"
                
            # Log the values we're sending to the backend
            logger.info(f"Creating node with name={name}, type={node_type}, color={color}")
            logger.info(f"Additional attributes: {values}")
            
            # Set status to inform user
            self.status_label.setText("Creating node...")
            
            # Create node
            result = await create_node_in_backend(
                name=name,
                color=color,
                size=10,
                attribute_updates=values
            )
            
            # Check for explicit error
            if result and "error" in result and result["error"] is not None:
                error_msg = result["error"]
                logger.error(f"Explicit error creating node: {error_msg}")
                self.status_label.setText(f"Error: {error_msg}")
                
                # Signal failure
                self.operation_completed.emit({
                    "action": "create",
                    "success": False,
                    "result": result
                })
                return
            
            # Check if result has a graph (success indicator)
            if result and "graph" in result and result["graph"]:
                # We have a successful node creation with updated graph
                logger.info("Node created successfully, updating main graph")
                self.status_label.setText("Node created successfully!")
                
                # Update the main window graph
                if hasattr(self.main_window, 'show_graph'):
                    try:
                        await self.main_window.show_graph(result["graph"])
                        logger.info("Main graph updated successfully")
                    except Exception as graph_e:
                        logger.error(f"Error updating graph: {graph_e}")
                        # Continue anyway since node creation was successful
                
                # Signal success
                self.operation_completed.emit({
                    "action": "create",
                    "success": True,
                    "result": result
                })
                
                # Now it's safe to close the tab
                QTimer.singleShot(500, self.close_tab)
                return
            else:
                # No graph returned but also no explicit error - this is the problematic case
                logger.error(f"Failed to create node: Backend returned no graph and no error. Full result: {result}")
                self.status_label.setText("Error: Failed to create node (no data returned)")
                
                # Try to update graph anyway to ensure UI is fresh
                if hasattr(self.main_window, 'refresh_graph'):
                    try:
                        await self.main_window.refresh_graph()
                    except Exception:
                        pass  # Ignore refresh errors
                        
                # Signal failure with more details
                self.operation_completed.emit({
                    "action": "create",
                    "success": False,
                    "result": {"error": "Backend returned no graph data", "original_result": result}
                })
                
                # Do not close the tab so user can see error and try again
                
        except Exception as e:
            logger.error(f"Exception in node creation: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            
            # Signal error
            self.operation_completed.emit({
                "action": "error",
                "error": str(e)
            })
            
            # Do not close the tab on exception
    
    async def _update_node(self, values, node_id):
        """Update an existing node using the existing backend logic."""
        try:
            # Remove node type from values
            if "node_type" in values:
                values.pop("node_type")
            
            # Update node
            logger.info(f"Updating node: id={node_id}")
            result = await edit_node_in_backend(
                node_id=node_id,
                attribute_updates=values
            )
            
            # Update graph first before emitting signal
            if "error" not in result and result.get("graph") and hasattr(self.main_window, 'show_graph'):
                await self.main_window.show_graph(result["graph"])
            
            # Emit completion signal with result
            self.operation_completed.emit({
                "action": "update",
                "success": "error" not in result,
                "result": result
            })
            
            # Close the tab after a short delay on success
            if "error" not in result:
                QTimer.singleShot(500, self.close_tab)
        
        except Exception as e:
            logger.error(f"Error updating node: {e}")
            self.operation_completed.emit({
                "action": "error",
                "error": str(e)
            })
    
    def close_tab(self):
        """Close this tab."""
        # Find the parent content tabs widget
        if hasattr(self.main_window, 'content_tabs'):
            content_tabs = self.main_window.content_tabs
            
            # First check if we're in the content_tabs list
            if self in content_tabs.content_tabs:
                # In tabbed mode
                if content_tabs.layout_mode == 'tabs':
                    # Find the tab index and close it
                    index = content_tabs.tab_widget.indexOf(self)
                    if index >= 0:
                        content_tabs.close_tab(index)
                else:
                    # In side-by-side mode
                    if self in content_tabs.tab_widget_dict:
                        container = content_tabs.tab_widget_dict[self]
                        # Find our index in the container
                        for i in range(container.count()):
                            if container.widget(i) == self:
                                content_tabs.close_side_by_side_tab(container, i)
                                break
    
    def get_tab_title(self):
        """Return the tab title."""
        if self.mode == "edit" and self.node_id:
            return f"Edit Object ({self.node_id[:8]}...)"
        return "Add Object"
    
    def refresh(self):
        """Refresh the editor (for ModularTabs integration)."""
        if self.dialog and hasattr(self.dialog, 'refresh'):
            self.dialog.refresh()
    
    def save_changes(self):
        """Save changes - replaces dialog's accept() method."""
        if self.dialog and hasattr(self.dialog, 'get_values'):
            values = self.dialog.get_values()
            self._on_dialog_finished(values)
        else:
            logger.error("Cannot save: Dialog not initialized or missing get_values method")
            self.status_label.setText("Error: Cannot save changes")
    
    def cancel_edit(self):
        """Cancel edit - replaces dialog's reject() method."""
        self._on_dialog_finished(None)
    
    def confirm_remove(self):
        """Show a confirmation dialog and remove the node if confirmed."""
        if not self.node_id:
            return
            
        # Create confirmation dialog
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove this object? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        # If confirmed, remove the node
        if reply == QMessageBox.StandardButton.Yes:
            asyncio.create_task(self._remove_node(self.node_id))

    async def _remove_node(self, node_id):
        """Remove a node using the backend API."""
        try:
            self.status_label.setText("Removing object...")
            
            # Create API client
            client = APIClient()
            
            # Use the correct operation name "delete_node"
            success, content, error = await client.request_and_get_response(
                operation="delete_node",
                params={"node_id": str(node_id)},
                sender="Frontend"
            )
            
            if success and content and "result" in content:
                # Check if result is a boolean or a dictionary
                if isinstance(content["result"], dict) and content["result"].get("graph") and hasattr(self.main_window, 'show_graph'):
                    # If result contains a graph, update the main window graph
                    await self.main_window.show_graph(content["result"]["graph"])
                    logger.info(f"Node {node_id} removed successfully, graph updated")
                else:
                    # Result is a simple boolean or doesn't contain graph
                    # Refresh the graph to ensure deleted node is removed from UI
                    logger.info(f"Node {node_id} removed successfully, refreshing graph")
                    if hasattr(self.main_window, 'refresh_graph'):
                        await self.main_window.refresh_graph()
                    elif hasattr(self.main_window, 'show_graph'):
                        await self.main_window.show_graph()  # Call without arguments to refresh
                
                # Emit completion signal with the result we have
                self.operation_completed.emit({
                    "action": "remove",
                    "success": True,
                    "result": content["result"]
                })
                
                # Close the tab after a short delay
                QTimer.singleShot(300, self.close_tab)
            else:
                error_msg = error or content.get("error", "Unknown error during node removal")
                logger.error(f"Error removing node: {error_msg}")
                self.status_label.setText(f"Error: {error_msg}")
                
                # Emit error signal
                self.operation_completed.emit({
                    "action": "remove",
                    "success": False,
                    "error": error_msg
                })
        except Exception as e:
            logger.error(f"Exception during node removal: {e}")
            self.status_label.setText(f"Error: {str(e)}")
            
            # Emit error signal
            self.operation_completed.emit({
                "action": "error",
                "error": str(e)
            })
