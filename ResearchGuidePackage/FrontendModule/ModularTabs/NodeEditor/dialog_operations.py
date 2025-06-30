import logging
import uuid
import asyncio
from PyQt6 import QtWidgets

from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_operations import (
    create_node_in_backend, edit_node_in_backend, handle_file_download
)
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_types_manager import NodeTypesManager
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_dialog import create_async_dialog

logger = logging.getLogger(__name__)

# Ensure form values are correctly passed to the backend when creating a new node

async def show_node_dialog(parent, mode="add", node_id=None):
    """
    Show a node editor dialog or tab for creating or editing a node.
    
    Args:
        parent: Parent window
        mode: Either "add" or "edit"
        node_id: For edit mode, the ID of the node to edit
        
    Returns:
        Result dictionary or None if dialog was cancelled
    """
    try:
        # Get main window reference
        main_window = parent if hasattr(parent, 'content_tabs') else parent.window()
        
        # First check if we want to use tabs or dialogs
        use_tabs = hasattr(main_window, 'content_tabs')
        
        if use_tabs:
            # Use the tab-based approach
            return await _show_node_editor_tab(main_window, mode, node_id)
        else:
            # Use the original dialog-based approach for backward compatibility
            return await _show_original_dialog(parent, mode, node_id)
            
    except Exception as e:
        logger.error(f"Error in show_node_dialog: {e}", exc_info=True)
        QtWidgets.QMessageBox.critical(
            parent, 
            "Error", 
            f"Error showing node editor: {e}"
        )
        return {"error": str(e)}

async def _show_node_editor_tab(main_window, mode, node_id):
    """Show a node editor tab instead of a dialog."""
    try:
        from ResearchGuidePackage.FrontendModule.ModularTabs.node_editor_tab import NodeEditorTab
        
        # Check if there's already an editor tab for this node we can reuse
        existing_tab = None
        if hasattr(main_window.content_tabs, 'content_tabs'):
            for tab in main_window.content_tabs.content_tabs:
                if isinstance(tab, NodeEditorTab) and tab.mode == mode:
                    if mode == "edit" and tab.node_id == node_id:
                        # Found matching edit tab
                        existing_tab = tab
                        break
                    elif mode == "add":
                        # Found matching add tab
                        existing_tab = tab
                        break
        
        if existing_tab:
            # Focus on existing tab
            if hasattr(main_window.content_tabs, 'active_tab'):
                main_window.content_tabs.active_tab = existing_tab
            
            # Find tab index and select it
            if hasattr(main_window.content_tabs, 'tab_widget'):
                idx = main_window.content_tabs.tab_widget.indexOf(existing_tab)
                if idx >= 0:
                    main_window.content_tabs.tab_widget.setCurrentIndex(idx)
            
            # Return a future for existing tab
            future = asyncio.Future()
            existing_tab.operation_completed.connect(
                lambda result: future.set_result(result) if not future.done() else None
            )
            return await future
        
        # Create new node editor tab
        editor_tab = NodeEditorTab(main_window, mode, node_id)
        
        # Add the tab
        if hasattr(main_window.content_tabs, 'add_custom_tab'):
            main_window.content_tabs.add_custom_tab(editor_tab, editor_tab.get_tab_title())
        else:
            # Fallback to manual tab addition
            if hasattr(main_window.content_tabs, 'tab_widget'):
                idx = main_window.content_tabs.tab_widget.addTab(editor_tab, editor_tab.get_tab_title())
                main_window.content_tabs.tab_widget.setCurrentIndex(idx)
                
                # Update content_tabs list
                if hasattr(main_window.content_tabs, 'content_tabs'):
                    main_window.content_tabs.content_tabs.append(editor_tab)
                    
                # Update active tab
                if hasattr(main_window.content_tabs, 'active_tab'):
                    main_window.content_tabs.active_tab = editor_tab
        
        # Create a future to wait for operation completion
        future = asyncio.Future()
        
        # Connect to operation_completed signal
        editor_tab.operation_completed.connect(
            lambda result: future.set_result(result) if not future.done() else None
        )
        
        # Return the future - will be resolved when the editor completes
        return await future
        
    except Exception as e:
        logger.error(f"Error in _show_node_editor_tab: {e}", exc_info=True)
        return {"error": str(e)}

async def _show_original_dialog(parent, mode, node_id):
    """Show the original node dialog for backward compatibility."""
    # Import this here to avoid circular imports
    from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_dialog import create_async_dialog
    
    # Create communication instance locally if needed
    if not hasattr(parent, 'communication'):
        from ResearchGuidePackage.FrontendModule.client import APIClient
        communication = APIClient()
    else:
        communication = parent.communication
    
    # For edit mode, we need to fetch the node labels
    node_labels = {}
    node_attributes = {}
    
    if mode == "edit":
        if node_id:
            # First try to get data from the get_nodes operation
            success, content, error = await communication.request_and_get_response(
                operation="get_nodes",  # This operation exists in backend_operations.py
                params={},
                sender="Frontend"
            )
            
            if success and content and "result" in content and "nodes" in content["result"]:
                nodes = content["result"]["nodes"]
                
                # Find the specific node we want
                target_node_id = str(node_id)
                node_data = None
                for node in nodes:
                    if str(node.get("id")) == target_node_id:
                        # Make a clean copy and filter out system attributes
                        node_data = {}
                        excluded_fields = ['id', '_id', 'node_id', 'pos', 'position', 'index', 'status']
                        for k, v in node.items():
                            if k not in excluded_fields:
                                node_data[k] = v
                        break
                
                if node_data:
                    label = node_data.get("label", node_data.get("name", str(node_id)))
                    node_labels = {str(node_id): label}
                    node_attributes = {str(node_id): node_data}
                    logger.info(f"Using node data from API for node {node_id}")
                else:
                    # Fallback to using graph data
                    if hasattr(parent, 'graph') and parent.graph is not None:
                        try:
                            node_uuid = uuid.UUID(node_id)
                            if node_uuid in parent.graph.nodes:
                                node_data = parent.graph.nodes[node_uuid].copy()
                                # Extract label from node data
                                label = node_data.get("label", node_data.get("name", str(node_id)))
                                node_labels = {str(node_id): label}
                                node_attributes = {str(node_id): node_data}
                                logger.info(f"Using node data from graph for node {node_id}")
                            else:
                                QtWidgets.QMessageBox.critical(
                                    parent, "Error", f"Node {node_id} not found in graph"
                                )
                                return {"error": f"Node {node_id} not found in graph"}
                        except (ValueError, KeyError) as e:
                            QtWidgets.QMessageBox.critical(
                                parent, "Error", f"Error processing node: {e}"
                            )
                            return {"error": f"Error processing node: {e}"}
            else:
                QtWidgets.QMessageBox.critical(
                    parent, "Error", f"Error fetching nodes: {error or 'Unknown error'}"
                )
                return {"error": error or "Unknown error fetching nodes"}
        else:
            # Show all nodes to let user select which to edit
            success, content, error = await communication.request_and_get_response(
                operation="get_nodes",
                params={},
                sender="Frontend"
            )
            
            if not (success and content.get("result")):
                QtWidgets.QMessageBox.critical(
                    parent, "Error", f"Error fetching nodes: {error or 'Unknown error'}"
                )
                return {"error": error or "Unknown error fetching nodes"}
            
            # Get nodes data
            nodes_data = content.get("result", {}).get("nodes", [])
            if not nodes_data:
                QtWidgets.QMessageBox.information(parent, "Information", "No nodes to edit.")
                return None
            
            # Create node labels mapping for all nodes
            node_labels = {node["id"]: node.get("label", node.get("name", node["id"])) for node in nodes_data}
    
    try:
        # Use the async dialog function instead of creating a modal dialog
        await asyncio.sleep(0.1)  # Small delay to allow UI to settle
        
        # Show dialog and get result
        values = await create_async_dialog(
            parent, 
            mode=mode,
            node_labels=node_labels,
            node_attributes=node_attributes,
            selected_node_id=node_id if mode == "edit" else None
        )
        
        # If dialog was cancelled (values is None), return None
        if values is None:
            return None
        
        # Extract common parameters
        node_type = values.pop("node_type", "document")
        
        # Remove file_updates from values - file operations are already handled directly
        if "file_updates" in values:
            values.pop("file_updates", None)
        
        # Process based on mode
        if mode == "add":
            from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_operations import create_node_in_backend
            from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_types_manager import NodeTypesManager
            
            # Get name from values
            name = None
            for key, value in list(values.items()):
                if key.lower() == "name":
                    name = value
                    break
            
            if not name:
                # Use default name if not provided
                name = f"New {node_type.capitalize()} Node"
            
            # Get color based on node type
            type_manager = NodeTypesManager(parent)
            color = await type_manager.get_default_color(node_type)
            
            # If no color from backend, use a default
            if not color:
                color = "skyblue"
            
            # Create node in backend
            try:
                logger.info(f"Creating node: name={name}, type={node_type}, color={color}")
                result = await create_node_in_backend(
                    name=name,
                    color=color,
                    size=10,
                    attribute_updates=values
                )
                logger.info(f"Node creation result: {result}")
                return result
            except Exception as e:
                logger.error(f"Error creating node: {e}")
                return {"error": str(e)}
        else:  # mode == "edit"
            from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.node_operations import edit_node_in_backend
            
            # Get the selected node ID for editing
            selected_node_id = None
            
            if node_id:
                # We already know which node to edit
                selected_node_id = str(node_id)
            else:
                # Get the selected node ID from the values dictionary
                selected_node_id = values.get("node_id")
            
            if not selected_node_id:
                QtWidgets.QMessageBox.critical(parent, "Error", "No node selected.")
                return {"error": "No node selected"}
            
            # Make sure node_id is a string
            if isinstance(selected_node_id, uuid.UUID):
                selected_node_id = str(selected_node_id)
            
            logger.info(f"Editing node: ID={selected_node_id}")
            
            # Remove node_type from values
            if "node_type" in values:
                values.pop("node_type")
            
            # Update node in backend
            try:
                result = await edit_node_in_backend(
                    node_id=selected_node_id,
                    attribute_updates=values
                )
                logger.info(f"Node edit result: {result}")
                return result
            except Exception as e:
                logger.error(f"Error editing node: {e}")
                return {"error": str(e)}
    except Exception as e:
        logger.error(f"Error in show_node_dialog: {e}", exc_info=True)
        QtWidgets.QMessageBox.critical(
            parent, 
            "Error", 
            f"Error showing node dialog: {e}"
        )
        return {"error": str(e)}

# These remain simple wrappers
async def show_dialog_for_create(parent):
    """Show dialog/tab for creating a new node."""
    return await show_node_dialog(parent, mode="add")

async def show_dialog_for_edit(parent):
    """Show dialog/tab for editing a node (lets user select which node)."""
    return await show_node_dialog(parent, mode="edit", node_id=None)

async def edit_node_by_uuid(main_window, node_uuid_str):
    """Edit a specific node by its UUID."""
    try:
        # Get the actual main window instance if we were passed a widget
        if not hasattr(main_window, 'show_graph'):
            # Try to get the main window from the widget
            actual_main_window = main_window.window()  # window() returns top-level window
        else:
            actual_main_window = main_window
            
        # Convert string to UUID object if needed
        if isinstance(node_uuid_str, str):
            try:
                node_uuid = uuid.UUID(node_uuid_str)
                node_id = str(node_uuid)
            except ValueError:
                logger.error(f"Invalid UUID format: {node_uuid_str}")
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Invalid node ID: {node_uuid_str}")
                return {"error": f"Invalid UUID format: {node_uuid_str}"}
        else:
            node_uuid = node_uuid_str
            node_id = str(node_uuid)
        
        logger.info(f"Editing node with UUID: {node_id}")
        
        # Create a variable to hold the resulting future for better task management
        dialog_result = None
        
        try:
            # Show dialog specifically for this node
            dialog_result = await show_node_dialog(main_window, mode="edit", node_id=node_id)
            
            # If dialog was cancelled or no result, return early
            if dialog_result is None or not dialog_result:
                logger.info(f"Node edit cancelled for {node_id}")
                return None
                
            # Handle both result formats - new tab format and old dialog format
            if "action" in dialog_result and dialog_result.get("action") == "cancel":
                logger.info(f"Node edit cancelled for {node_id}")
                return None
                
            if "action" in dialog_result and dialog_result.get("action") in ("create", "update"):
                # Get the actual backend result
                node_result = dialog_result.get("result", {})
                
                # Process the backend result like before
                if node_result.get("graph"):
                    await actual_main_window.show_graph(node_result["graph"])
                    logger.info(f"Node {node_id} edited successfully, graph updated")
                elif node_result.get("error"):
                    error_msg = node_result["error"]
                    logger.error(f"Error editing node {node_id}: {error_msg}")
                    QtWidgets.QMessageBox.critical(main_window, "Error", f"Failed to edit node: {error_msg}")
                    await actual_main_window.show_graph()
                else:
                    logger.info(f"Node edit operation completed for {node_id}, refreshing UI")
                    await actual_main_window.show_graph()
                
                return node_result
            
            # Process legacy format directly
            if dialog_result.get("graph"):
                # Update the UI with the edited graph
                await actual_main_window.show_graph(dialog_result["graph"])
                logger.info(f"Node {node_id} edited successfully, graph updated")
            elif dialog_result.get("error"):
                # Show error message
                error_msg = dialog_result["error"]
                logger.error(f"Error editing node {node_id}: {error_msg}")
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Failed to edit node: {error_msg}")
                # Refresh graph anyway
                await actual_main_window.show_graph()
            elif dialog_result.get("download_info"):
                # Handle file download if requested
                await handle_file_download(main_window, dialog_result["download_info"])
                await actual_main_window.show_graph()
            else:
                # If we get here, something succeeded but we don't have a graph
                # Try to refresh the UI anyway
                logger.info(f"Node edit operation completed for {node_id}, refreshing UI")
                await actual_main_window.show_graph()
            
            return dialog_result
            
        except Exception as inner_e:
            logger.error(f"Error processing dialog result: {inner_e}", exc_info=True)
            # Try to refresh the graph even after an error
            await actual_main_window.show_graph()
            return {"error": str(inner_e)}
        
    except Exception as e:
        logger.error(f"Error in edit_node_by_uuid: {e}", exc_info=True)
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error editing node: {e}")
        # Try to refresh the graph even after an error
        try:
            # Try to get actual_main_window again in case the error happened earlier
            if 'actual_main_window' in locals():
                await actual_main_window.show_graph()
            elif hasattr(main_window, 'window') and hasattr(main_window.window(), 'show_graph'):
                await main_window.window().show_graph()
        except Exception as refresh_error:
            logger.error(f"Error refreshing graph after failed edit: {refresh_error}")
        return {"error": str(e)}
