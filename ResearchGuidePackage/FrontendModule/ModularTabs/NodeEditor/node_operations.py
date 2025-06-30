import logging
import uuid
import os
import asyncio
import base64
import pickle
from PyQt6 import QtWidgets
from ResearchGuidePackage.FrontendModule.client import APIClient
from PyQt6 import QtCore

logger = logging.getLogger(__name__)

async def create_node_in_backend(name, color, size, attribute_updates=None, file_updates=None):
    """
    Create a new node in the backend.
    
    Returns:
        dict: Result with keys:
            - graph: NetworkX graph object if operation was successful, None otherwise
            - error: Error message if an error occurred
    """
    result = {"graph": None, "error": None}
    try:
        # Create API client instance
        comm = APIClient()
        
        params = {
            "name": name,
            "color": color,
            "size": size,
            "update_page": True
        }
        
        # Add any additional attributes
        if attribute_updates:
            # Remove already handled attributes
            for key in ['name', 'color', 'size']:
                if key in attribute_updates:
                    attribute_updates.pop(key, None)  # Use pop with default to avoid KeyError
            params.update(attribute_updates)
        
        logger.info(f"Creating node with params: {params}")
        
        # Create the node
        success, content, error = await comm.request_and_get_response(
            operation="create_node",
            params=params,
            sender="Frontend",
            timeout=30
        )
        
        if success and content and content.get("result"):
            # Get the created node ID
            node_id = content.get("result", {}).get('node_id')
            logger.info(f"Node created: ID={node_id}, Name={name}, Color={color}, Size={size}")
            
            # Note: File uploads are now handled directly by the form manager
            # when the user presses the upload button, so we don't need to handle them here
            
            # Get fresh graph data
            success, graph_content, graph_error = await comm.request_and_get_response(
                operation="get_graph",
                params={},
                sender="Frontend"
            )
            
            if success and "graph_data" in graph_content:
                graph_data = base64.b64decode(graph_content["graph_data"])
                graph = pickle.loads(graph_data)
                result["graph"] = graph
                return result
            else:
                result["error"] = graph_error or "Failed to get updated graph"
                return result
        else:
            parent = QtWidgets.QApplication.activeWindow()
            error_msg = error or "Unknown error"
            QtWidgets.QMessageBox.critical(parent, "Error", f"Error creating node: {error_msg}")
            logger.error(f"Error creating node: {error_msg}")
            result["error"] = error_msg
            return result
    except Exception as e:
        parent = QtWidgets.QApplication.activeWindow()
        QtWidgets.QMessageBox.critical(parent, "Error", f"Error creating node: {e}")
        logger.error(f"Error creating node: {e}", exc_info=True)
        result["error"] = str(e)
        return result

async def edit_node_in_backend(node_id, attribute_updates, file_updates=None):
    """
    Edit an existing node in the backend.
    
    Returns:
        dict: Result with keys:
            - graph: NetworkX graph object if operation was successful, None otherwise
            - error: Error message if an error occurred
    """
    result = {"graph": None, "error": None}
    try:
        # Create API client instance
        comm = APIClient()
        
        # Log the operation
        logger.info(f"Editing node: ID={node_id} with attributes: {attribute_updates}")
        
        # Check if node_id is valid
        if not isinstance(node_id, str) or not node_id.strip():
            parent = QtWidgets.QApplication.activeWindow()
            QtWidgets.QMessageBox.critical(parent, "Error", f"Invalid node ID: {node_id}")
            result["error"] = f"Invalid node ID: {node_id}"
            return result
        
        # Note: File operations are now handled directly by the form manager
        # when the user presses the upload/download/replace buttons
        
        # Normalize attribute keys to lowercase to match backend expectations
        normalized_attributes = {}
        for key, value in attribute_updates.items():
            # Don't modify keys - preserve them as-is
            normalized_key = key
            
            # Don't include placeholder file values
            if normalized_key.lower() in ['file', 'file_path'] and value == "Select File":
                continue
                
            # Handle empty strings - don't send them as they cause fields to be deleted
            if value != "":
                normalized_attributes[normalized_key] = value
            else:
                logger.debug(f"Skipping empty attribute: {normalized_key}")
        
        logger.info(f"Submitting normalized attributes: {normalized_attributes}")
            
        # Send edit request with normalized attributes
        success, content, error = await comm.request_and_get_response(
            operation="edit_node",
            params={
                "node_id": node_id,
                "attributes": normalized_attributes,
                "update_page": True
            },
            sender="Frontend",
            timeout=15  # Increase timeout for editing operations
        )

        
        if success and content.get("result") is True:
            logger.info(f"Node {node_id} edited successfully")

            active_window = QtWidgets.QApplication.activeWindow()
            if hasattr(active_window, 'show_graph') and callable(active_window.show_graph):
                asyncio.create_task(active_window.show_graph())
        
            
            # Get the updated graph data
            success, graph_content, graph_error = await comm.request_and_get_response(
                operation="get_graph",
                params={},
                sender="Frontend"
            )
            
            if success and "graph_data" in graph_content:
                # Decode graph data
                graph_data = base64.b64decode(graph_content["graph_data"])
                try:
                    graph = pickle.loads(graph_data)
                    result["graph"] = graph
                    logger.info("Successfully loaded updated graph")
                except Exception as e:
                    logger.error(f"Error deserializing graph: {e}")
                    result["error"] = f"Error deserializing graph: {e}"
            else:
                logger.warning(f"Error getting updated graph: {graph_error}")
                # Even if we can't get the updated graph, the edit was successful
                result["result"] = True
                
            return result
        else:
            parent = QtWidgets.QApplication.activeWindow()
            error_msg = error or "Unknown error editing node"
            QtWidgets.QMessageBox.critical(parent, "Error", error_msg)
            logger.error(f"Error editing node: {error_msg}")
            result["error"] = error_msg
            return result
            
    except Exception as e:
        parent = QtWidgets.QApplication.activeWindow()
        QtWidgets.QMessageBox.critical(parent, "Error", f"Error editing node: {e}")
        logger.error(f"Exception in edit_node_in_backend: {e}", exc_info=True)
        result["error"] = str(e)
        return result

# Keep this function for direct file downloads not tied to the form
async def handle_file_download(parent, download_info):
    """Handle downloading a file for a node."""
    if 'node_id' in download_info and 'save_path' in download_info:
        await export_node_file(parent, download_info['node_id'], download_info['save_path'])

async def export_node_file(parent, node_id, save_path):
    """Export a node's file content to the specified path."""
    try:
        logger.info(f"Starting download for node {node_id} to {save_path}")
        
        # Create API client instance
        comm = APIClient()
        
        # Request the file with longer timeout
        success, content, error = await comm.request_and_get_response(
            operation="get_node_file",
            params={"node_id": str(node_id)},
            sender="Frontend",
            timeout=30
        )
        
        # Handle response
        if success and content and "file_content" in content:
            file_content = content["file_content"]
            
            if not file_content:
                logger.error("File content is empty")
                QtWidgets.QMessageBox.critical(parent, "Error", "File content is empty")
                return
                
            # Write file to disk
            with open(save_path, 'wb') as f:
                f.write(file_content)
                
            # Show success message
            QtWidgets.QMessageBox.information(
                parent, 
                "Download Complete", 
                f"File saved to {save_path}"
            )
            logger.info(f"File saved to {save_path}")
        else:
            error_msg = error or "Failed to get file"
            logger.error(f"Error downloading file: {error_msg}")
            QtWidgets.QMessageBox.critical(parent, "Error", f"Error downloading file: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        QtWidgets.QMessageBox.critical(parent, "Error", f"Error saving file: {e}")

async def edit_node_by_id(parent, node_uuid, graph=None):
    """Edit a specific node by its ID."""
    from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.dialog_operations import show_node_dialog

    
    try:
        # Get graph if not provided
        if graph is None:
            if hasattr(parent, 'graph'):
                graph = parent.graph
            else:
                return {"error": "No graph available"}
        
        # Verify node exists
        if node_uuid not in graph.nodes:
            return {"error": f"Node {node_uuid} does not exist in the graph"}
        
        # Convert node_uuid to string if it's a UUID object
        node_id = str(node_uuid) if isinstance(node_uuid, uuid.UUID) else node_uuid
        
        # Use the unified dialog function with the node_id
        return await show_node_dialog(parent, mode="edit", node_id=node_id)
        
    except Exception as e:
        logger.error(f"Error in edit_node_by_id: {e}", exc_info=True)
        return {"error": str(e)}
