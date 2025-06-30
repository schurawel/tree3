from PyQt6 import QtWidgets
import logging
import asyncio
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QVBoxLayout, QWidget
from ResearchGuidePackage.FrontendModule.dialogs import AddEdgeDialog, DeleteNodeDialog, DeleteEdgeDialog, EditEdgeDialog
import uuid
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.dialog_operations import show_dialog_for_create

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def create_toolbar(main_window, toolbar_widget, canvas=None):
    """Create toolbar with a vertical layout and logical grouping."""
    # Remove any existing layout
    if toolbar_widget.layout():
        old_layout = toolbar_widget.layout()
        for i in reversed(range(old_layout.count())):
            item = old_layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        del old_layout
    
    # Create a vertical layout for the toolbar
    toolbar_layout = QVBoxLayout(toolbar_widget)
    toolbar_layout.setContentsMargins(4, 4, 4, 4)
    toolbar_layout.setSpacing(6)
    
    # === CONTAINER 1: OPERATION BUTTONS ===
    operations_container = QWidget()
    operations_container.setObjectName("operations_container")
    operations_layout = QHBoxLayout(operations_container)
    operations_layout.setContentsMargins(2, 2, 2, 2)
    operations_layout.setSpacing(6)
    operations_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    
    # Add operation buttons
    add_node_button = QtWidgets.QPushButton("Add Node", main_window)
    add_node_button.clicked.connect(lambda: add_node(main_window))
    operations_layout.addWidget(add_node_button)

    add_edge_button = QtWidgets.QPushButton("Add Edge", main_window)
    add_edge_button.clicked.connect(lambda: add_edge(main_window))
    operations_layout.addWidget(add_edge_button)

    delete_node_button = QtWidgets.QPushButton("Delete Node", main_window)
    delete_node_button.clicked.connect(lambda: delete_node(main_window))
    operations_layout.addWidget(delete_node_button)

    delete_edge_button = QtWidgets.QPushButton("Delete Edge", main_window)
    delete_edge_button.clicked.connect(lambda: delete_edge(main_window))
    operations_layout.addWidget(delete_edge_button)

    edit_node_button = QtWidgets.QPushButton("Edit Node", main_window)
    edit_node_button.clicked.connect(lambda: edit_node(main_window))
    operations_layout.addWidget(edit_node_button)

    edit_edge_button = QtWidgets.QPushButton("Edit Edge", main_window)
    edit_edge_button.clicked.connect(lambda: edit_edge(main_window))
    operations_layout.addWidget(edit_edge_button)
   
    if canvas:
        # Add toggle labels button with simple color styling - set initial state based on current canvas state
        button_text = "Hide Labels" if canvas.labels_visible else "Show Labels"
        button_style = "background-color: #f44336; color: white;" if canvas.labels_visible else "background-color: #4CAF50; color: white;"
        
        toggle_labels_button = QtWidgets.QPushButton(button_text, main_window)
        toggle_labels_button.setStyleSheet(button_style)
        toggle_labels_button.clicked.connect(canvas.toggle_labels)
        toggle_labels_button.clicked.connect(lambda: update_button_text(toggle_labels_button, not canvas.labels_visible))
        operations_layout.addWidget(toggle_labels_button)
    
    # Add stretch to push everything to the left in the operations container
    operations_layout.addStretch(1)
    
    # Add the operations container to the main toolbar layout
    toolbar_layout.addWidget(operations_container)
    
    # Set the overall layout
    toolbar_widget.setLayout(toolbar_layout)

    logging.info("Toolbar created with vertical layout and logical grouping of controls")

def update_button_text(button, labels_visible):
    """Update button text based on label visibility."""
    if labels_visible:
        button.setText("Hide Labels")
        button.setStyleSheet("background-color: #f44336; color: white;")
    else:
        button.setText("Show Labels")
        button.setStyleSheet("background-color: #4CAF50; color: white;")

def add_node(main_window):
    """Add a new node to the graph using node dialog."""
    # Create async task to show the create node dialog
    asyncio.create_task(show_create_node_dialog(main_window))

async def show_create_node_dialog(main_window):
    """Show dialog for creating a new node."""
    # Show the dialog and get the result
    result = await show_dialog_for_create(main_window)
    
    # If dialog was cancelled (result is None), do nothing and return early
    if result is None:
        logging.info("Node creation cancelled by user")
        return
        
    # Process the result
    if result.get("graph"):
        # Update the UI with the new graph
        await main_window.show_graph(result["graph"])
    elif result.get("error"):
        # Log the error
        logging.error(f"Error during node creation: {result['error']}")
        # The dialog already showed an error message to the user
        # Just refresh the UI
        await main_window.show_graph()
    else:
        # No data returned, just refresh
        await main_window.show_graph()

def add_edge(main_window):
    """Add a new edge to the graph using ticket system."""
    async def get_nodes_and_show_dialog():
        try:
            # Get all nodes using ticket system
            success, content, error = await main_window.communication.request_and_get_response(
                operation="get_nodes",
                params={},
                sender="Frontend"
            )
            
            if not content:
                logging.error("Failed to retrieve nodes: Result is None")
                QtWidgets.QMessageBox.critical(
                    main_window, 
                    "Error", 
                    "Failed to retrieve node information from the backend."
                )
                return  # Exit the function early
            
            if success and content.get("result"):
                nodes_data = content.get("result", {}).get("nodes", [])
                node_labels = {uuid.UUID(node["id"]): node["label"] for node in nodes_data}
                
                # Now show the dialog
                dialog = AddEdgeDialog(main_window, node_labels=node_labels)
                result = dialog.exec()
                if result == QtWidgets.QDialog.DialogCode.Accepted:
                    node1_label, node2_label, weight, edge_type, color = dialog.get_values()
                    
                    # Find the UUIDs corresponding to the labels
                    node1_uuid = None
                    node2_uuid = None
                    for node_id, label in node_labels.items():
                        if label == node1_label:
                            node1_uuid = node_id
                        if label == node2_label:
                            node2_uuid = node_id
                    
                    if node1_uuid and node2_uuid:
                        # Create the edge using ticket system
                        await create_edge_async(main_window, str(node1_uuid), str(node2_uuid), weight, edge_type, color)
                    else:
                        QtWidgets.QMessageBox.critical(main_window, "Error", "Invalid nodes selected.")
                        logging.error("Invalid nodes selected.")
            else:
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Error getting nodes: {error or 'Unknown error'}")
                logging.error(f"Error getting nodes: {error or 'Unknown error'}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error adding edge: {e}")
            logging.error(f"Error adding edge: {e}")
    
    # Start the async task
    asyncio.create_task(get_nodes_and_show_dialog())

async def create_edge_async(main_window, source_id, target_id, weight, edge_type, color):
    """Asynchronously create an edge using the ticket system."""
    try:
        success, content, error = await main_window.communication.request_and_get_response(
            operation="add_edge",
            params={
                "source_id": source_id,
                "target_id": target_id,
                "weight": weight,
                "edge_type": edge_type,
                "update_page": True
            },
            sender="Frontend"
        )
        
        if success and content.get("result"):
            logging.info(f"Edge added between {source_id} and {target_id} with weight {weight}, type '{edge_type}'")
            await main_window.show_graph()
        else:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error adding edge: {error or 'Unknown error'}")
            logging.error(f"Error adding edge: {error or 'Unknown error'}")
    except Exception as e:
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error adding edge: {e}")
        logging.error(f"Error adding edge: {e}")

def delete_node(main_window):
    """Delete a node from the graph using ticket system."""
    async def get_nodes_and_show_dialog():
        try:
            # Get all nodes using ticket system
            success, content, error = await main_window.communication.request_and_get_response(
                operation="get_nodes",
                params={},
                sender="Frontend"
            )
            
            if success and content.get("result"):
                nodes_data = content.get("result", {}).get("nodes", [])
                node_labels = {uuid.UUID(node["id"]): node["label"] for node in nodes_data}
                
                dialog = DeleteNodeDialog(main_window, node_labels)
                if dialog.exec():
                    selected_node_label = dialog.get_selected_node()
                    
                    # Find the UUID corresponding to the selected label
                    node_to_delete = None
                    for node_uuid, label in node_labels.items():
                        if label == selected_node_label:
                            node_to_delete = node_uuid
                            break
                    
                    if node_to_delete:
                        await delete_node_async(main_window, str(node_to_delete))
                    else:
                        QtWidgets.QMessageBox.warning(main_window, "Warning", "Invalid node selected.")
            else:
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Error getting nodes: {error or 'Unknown error'}")
                logging.error(f"Error getting nodes: {error or 'Unknown error'}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error deleting node: {e}")
            logging.error(f"Error deleting node: {e}")
    
    # Start the async task
    asyncio.create_task(get_nodes_and_show_dialog())

async def delete_node_async(main_window, node_id):
    """Asynchronously delete a node using the ticket system."""
    try:
        success, content, error = await main_window.communication.request_and_get_response(
            operation="delete_node",
            params={
                "node_id": node_id,
                "update_page": True
            },
            sender="Frontend"
        )
        
        if success and content.get("result"):
            logging.info(f"Node deleted: {node_id}")
            await main_window.show_graph()
        else:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error deleting node: {error or 'Unknown error'}")
            logging.error(f"Error deleting node: {error or 'Unknown error'}")
    except Exception as e:
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error deleting node: {e}")
        logging.error(f"Error deleting node: {e}")

def delete_edge(main_window):
    """Delete an edge from the graph using ticket system."""
    async def get_graph_and_show_dialog():
        try:
            # Get the current graph to extract edges
            graph = await main_window.get_graph()
            if not graph:
                QtWidgets.QMessageBox.critical(main_window, "Error", "Failed to get graph data")
                return
                
            edge_labels = []
            edge_map = {}  # Store a mapping from edge label to (node1_uuid, node2_uuid)
            
            # Get node labels using ticket system
            success, content, error = await main_window.communication.request_and_get_response(
                operation="get_nodes",
                params={},
                sender="Frontend"
            )
            
            if success and content.get("result"):
                nodes_data = content.get("result", {}).get("nodes", [])
                node_label_map = {uuid.UUID(node["id"]): node["label"] for node in nodes_data}
                
                # Iterate through the edges and get the UUIDs directly
                for node1, node2, data in graph.edges(data=True):
                    node1_label = node_label_map.get(node1, str(node1))
                    node2_label = node_label_map.get(node2, str(node2))
                    edge_label = f"({node1_label}, {node2_label})"
                    edge_labels.append(edge_label)
                    edge_map[edge_label] = (node1, node2)  # Store the UUIDs
                
                dialog = DeleteEdgeDialog(main_window, edge_labels)
                if dialog.exec():
                    selected_edge_label = dialog.get_selected_edge()
                    
                    if selected_edge_label in edge_map:
                        node1_uuid, node2_uuid = edge_map[selected_edge_label]
                        await delete_edge_async(main_window, str(node1_uuid), str(node2_uuid))
                    else:
                        QtWidgets.QMessageBox.warning(main_window, "Warning", "Invalid edge selected.")
            else:
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Error getting nodes: {error or 'Unknown error'}")
                logging.error(f"Error getting nodes: {error or 'Unknown error'}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error deleting edge: {e}")
            logging.error(f"Error deleting edge: {e}")
    
    # Start the async task
    asyncio.create_task(get_graph_and_show_dialog())

async def delete_edge_async(main_window, source_id, target_id):
    """Asynchronously delete an edge using the ticket system."""
    try:
        success, content, error = await main_window.communication.request_and_get_response(
            operation="delete_edge",
            params={
                "source_id": source_id,
                "target_id": target_id,
                "update_page": True
            },
            sender="Frontend"
        )
        
        if success and content.get("result"):
            logging.info(f"Edge deleted between {source_id} and {target_id}")
            await main_window.show_graph()
        else:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error deleting edge: {error or 'Unknown error'}")
            logging.error(f"Error deleting edge: {error or 'Unknown error'}")
    except Exception as e:
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error deleting edge: {e}")
        logging.error(f"Error deleting edge: {e}")

def edit_node(main_window):
    """Edit an existing node in the graph using node dialog."""
    async def get_nodes_and_show_dialog():
        try:
            # Get all nodes using ticket system
            success, content, error = await main_window.communication.request_and_get_response(
                operation="get_nodes",
                params={},
                sender="Frontend"
            )
            
            if success and content.get("result"):
                nodes_data = content.get("result", {}).get("nodes", [])
                node_labels = {uuid.UUID(node["id"]): node["label"] for node in nodes_data}
                
                # Show node selection dialog
                from ResearchGuidePackage.FrontendModule.dialogs import SelectNodeDialog
                dialog = SelectNodeDialog(main_window, node_labels, title="Edit Node")
                if dialog.exec():
                    selected_node_uuid = dialog.get_selected_node_id()
                    
                    if selected_node_uuid:
                        # Use edit_node_by_id to edit the selected node
                        from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_operations import edit_node_by_id
                        result = await edit_node_by_id(main_window, selected_node_uuid)
                        
                        # If result is None, it could mean user canceled, so just return silently
                        if result is None:
                            logging.info("Edit dialog closed or canceled by user")
                            return
                        
                        # Process the result
                        if result.get("graph"):
                            # Update the UI with the edited graph
                            await main_window.show_graph(result["graph"])
                        elif result.get("error"):
                            # Log the error
                            logging.error(f"Error during node edit: {result['error']}")
                            # Show error message to the user
                            QtWidgets.QMessageBox.critical(main_window, "Error", f"Failed to edit node: {result['error']}")
                            # Refresh the UI
                            await main_window.show_graph()
                        else:
                            # Just refresh
                            await main_window.show_graph()
                    else:
                        QtWidgets.QMessageBox.warning(main_window, "Warning", "No node selected.")
            else:
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Error getting nodes: {error or 'Unknown error'}")
                logging.error(f"Error getting nodes: {error or 'Unknown error'}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error editing node: {e}")
            logging.error(f"Error editing node: {e}", exc_info=True)
    
    # Start the async task
    asyncio.create_task(get_nodes_and_show_dialog())

def edit_edge(main_window):
    """Edit an existing edge using the ticket system."""
    async def get_graph_and_show_dialog():
        try:
            # Get the current graph and node information
            graph = await main_window.get_graph()
            if not graph:
                QtWidgets.QMessageBox.critical(main_window, "Error", "Failed to get graph data")
                return
                
            # Get node labels using ticket system
            success, content, error = await main_window.communication.request_and_get_response(
                operation="get_nodes",
                params={},
                sender="Frontend"
            )
            
            if success and content.get("result"):
                nodes_data = content.get("result", {}).get("nodes", [])
                node_labels = {uuid.UUID(node["id"]): node["label"] for node in nodes_data}
                
                # Extract edge information
                edge_labels = []
                edge_map = {}  # Store a mapping from edge label to (node1_uuid, node2_uuid)
                
                # Iterate through the edges and get the UUIDs directly
                for node1, node2, data in graph.edges(data=True):
                    node1_label = node_labels.get(node1, str(node1))
                    node2_label = node_labels.get(node2, str(node2))
                    edge_label = f"({node1_label}, {node2_label})"
                    edge_labels.append(edge_label)
                    edge_map[edge_label] = (node1, node2, data)  # Store the UUIDs and data
                
                if not edge_labels:
                    QtWidgets.QMessageBox.information(main_window, "Info", "No edges available to edit.")
                    return
                
                first_edge_label = edge_labels[0] if edge_labels else None
                dialog = EditEdgeDialog(main_window, edge_labels, node_labels=node_labels, current_edge_label=first_edge_label)
                if dialog.exec():
                    selected_edge_label, new_node1_label, new_node2_label, weight, edge_type, color = dialog.get_values()
                    
                    # Find the UUIDs corresponding to the selected edge label
                    if selected_edge_label in edge_map:
                        old_node1_uuid, old_node2_uuid, old_data = edge_map[selected_edge_label]
                        
                        # Find the UUIDs corresponding to the new node labels
                        new_node1_uuid = None
                        new_node2_uuid = None
                        for node_uuid, label in node_labels.items():
                            if label == new_node1_label:
                                new_node1_uuid = node_uuid
                            if label == new_node2_label:
                                new_node2_uuid = node_uuid
                        
                        if new_node1_uuid and new_node2_uuid:
                            # Use edit_edge operation
                            await edit_edge_async(main_window, 
                                str(old_node1_uuid), str(old_node2_uuid),
                                str(new_node1_uuid), str(new_node2_uuid),
                                weight, edge_type, color)
                        else:
                            QtWidgets.QMessageBox.warning(main_window, "Warning", "Invalid nodes selected for new edge.")
                    else:
                        QtWidgets.QMessageBox.warning(main_window, "Warning", "Invalid edge selected.")
            else:
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Error getting nodes: {error or 'Unknown error'}")
                logging.error(f"Error getting nodes: {error or 'Unknown error'}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error editing edge: {e}")
            logging.error(f"Error editing edge: {e}")
    
    # Start the async task
    asyncio.create_task(get_graph_and_show_dialog())

async def edit_edge_async(main_window, old_source_id, old_target_id, new_source_id, new_target_id, weight, edge_type, color):
    """Asynchronously edit an edge using the ticket system."""
    try:
        # Since there's no direct "edit_edge" operation, we'll need to:
        # 1. Delete the existing edge
        # 2. Create a new edge with the updated attributes
        
        # First delete the old edge
        success1, content1, error1 = await main_window.communication.request_and_get_response(
            operation="delete_edge",
            params={
                "source_id": old_source_id,
                "target_id": old_target_id,
                "update_page": False  # Don't update page yet
            },
            sender="Frontend"
        )
        
        if success1 and content1.get("result"):
            # Now add the new edge
            success2, content2, error2 = await main_window.communication.request_and_get_response(
                operation="add_edge",
                params={
                    "source_id": new_source_id,
                    "target_id": new_target_id,
                    "weight": weight,
                    "edge_type": edge_type,
                    "update_page": True
                },
                sender="Frontend"
            )
            
            if success2 and content2.get("result"):
                logging.info(f"Edge edited: ({old_source_id}, {old_target_id}) -> ({new_source_id}, {new_target_id}), Weight={weight}, Type={edge_type}")
                await main_window.show_graph()
            else:
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Error adding new edge: {error2 or 'Unknown error'}")
                logging.error(f"Error adding new edge: {error2 or 'Unknown error'}")
        else:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error removing old edge: {error1 or 'Unknown error'}")
            logging.error(f"Error removing old edge: {error1 or 'Unknown error'}")
    except Exception as e:
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error editing edge: {e}")
        logging.error(f"Error editing edge: {e}")

def save_plot_as_image(main_window):
    """Save the graph plot as an image."""
    logging.info("Saving plot as image...")
    try:
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            main_window,
            "Save Plot as Image",
            "",
            "PNG (*.png);;JPG (*.jpg *.jpeg);;All Files (*)"
        )

        if file_path:
            main_window.canvas.figure.savefig(file_path)
            logging.info(f"Plot saved as image to {file_path}")
        else:
            logging.info("Save plot as image cancelled.")

    except Exception as e:
        logging.error(f"Error saving plot as image: {e}")
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error saving plot as image: {e}")

