import logging
from PyQt6 import QtWidgets
import os
import asyncio

def open_file_dialog(main_window):
    """Open database dialog and trigger graph loading using ticket system."""
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        main_window, "Open Laboratory Database", "",
        "Graph Database (*.db);;All Files (*)"
    )
    if file_path:
        asyncio.create_task(load_graph_from_file(main_window, file_path))

async def load_graph_from_file(main_window, file_path):
    """Load graph from file using ticket system."""
    try:
        logging.info(f"Loading graph from {file_path} using ticket system")
        success, graph, loaded_file_path, error = await main_window._request_graph_operation(
            operation="load_graph",
            params={"file_path": file_path}
        )
        
        if success and graph:
            logging.info(f"Successfully loaded graph from {file_path}")
            # Set the last saved file path using ticket system
            await main_window.set_last_saved_file_path(file_path)
            await main_window.show_graph(graph)
        else:
            error_msg = error or "Failed to load graph"
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error opening database: {error_msg}")
            logging.error(f"Error opening database: {error_msg}")
    except Exception as e:
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error opening database: {e}")
        logging.error(f"Error opening database: {e}")

def save_file_dialog(main_window):
    """Handle save database action using ticket system."""
    asyncio.create_task(save_graph(main_window))

async def save_graph(main_window):
    """Save graph using ticket system."""
    # First check if the graph is modified
    success, content, error = await main_window.communication.request_and_get_response(
        operation="get_graph_modified_status",
        params={},
        sender="Frontend"
    )
    
    if success and content.get("result", False):
        # Get the last saved file path using ticket system
        file_path = await main_window.get_last_saved_file_path()
        
        if file_path:
            return await main_window.save_graph_to_file(file_path)
        else:
            return await main_window.save_graph_as()
    else:
        QtWidgets.QMessageBox.information(main_window, "Info", "No changes to save.")
        return False

def save_as_file_dialog(main_window):
    """Handle save as database action using ticket system."""
    # First check if the graph is modified
    asyncio.create_task(check_and_save_as_graph(main_window))

async def check_and_save_as_graph(main_window):
    """Check if graph is modified and save as using ticket system."""
    success, content, error = await main_window.communication.request_and_get_response(
        operation="get_graph_modified_status",
        params={},
        sender="Frontend"
    )
    
    if success:
        if content.get("result", False):
            show_save_as_dialog(main_window)
        else:
            QtWidgets.QMessageBox.information(main_window, "Info", "No changes to save.")
    else:
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error checking graph status: {error or 'Unknown error'}")

def show_save_as_dialog(main_window):
    """Show save as dialog and save the file."""
    caption = "Save Laboratory As"
    directory = ""
    filter = "Graph Database (*.db)"
    file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
        main_window, caption, directory, filter
    )
    if file_path and not file_path.endswith(".db"):
        file_path += ".db"

    if file_path:
        asyncio.create_task(save_graph_to_file(main_window, file_path))

async def save_graph_to_file(main_window, file_path):
    """Save graph to the specified file using ticket system."""
    try:
        success, content, error = await main_window.communication.request_and_get_response(
            operation="save_graph",
            params={"file_path": file_path},
            sender="Frontend"
        )
        
        if success and content.get("result"):
            # Set the last saved file path using ticket system
            await main_window.set_last_saved_file_path(file_path)
            # Update window title
            await main_window.async_update_window_title()
            return True
        else:
            error_msg = error or "Failed to save graph"
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error saving graph: {error_msg}")
            logging.error(f"Error saving graph: {error_msg}")
            return False
    except Exception as e:
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error saving graph: {e}")
        logging.error(f"Error saving graph: {e}")
        return False
