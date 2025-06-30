import logging
import uuid
import asyncio
import webbrowser
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.dialog_operations import edit_node_by_uuid

logger = logging.getLogger(__name__)

OPEN_FILE_ACTION = "open_file"  # Action for opening a file

def handle_link_click(main_window, url):
    """Handle link click event."""
    logger.info(f"Link clicked: {url}")
    
    # Check if it's a special action link
    if url == OPEN_FILE_ACTION:
        from ResearchGuidePackage.FrontendModule.file_handler import open_file_dialog
        open_file_dialog(main_window)
        return
    
    # Check if it's a UUID (node link)
    try:
        node_uuid = uuid.UUID(url)
        # Use the edit_node_by_uuid function from dialog_operations
        asyncio.create_task(edit_node_by_uuid(main_window, url))
        return
    except ValueError:
        # Not a UUID, proceed with regular URL handling
        pass
    
    # Handle as external URL
    if url.startswith(("http://", "https://", "ftp://")):
        webbrowser.open(url)
    else:
        logger.warning(f"Unsupported link format: {url}")

def show_node_info(main_window, node_uuid):
    """Synchronous wrapper for opening NodeDialog - used by mpl_canvas."""
    try:
        # Just create async task to edit the node by UUID string
        # No need to check for communication attribute
        asyncio.create_task(edit_node_by_uuid(main_window, str(node_uuid)))
    except Exception as e:
        logger.error(f"Error in show_node_info: {e}")
        # Try to show error dialog if possible
        try:
            QtWidgets.QMessageBox.warning(
                main_window, "Error", f"Cannot show node info: {e}")
        except:
            # If we can't show dialog, just log the error
            logger.error("Could not show error dialog")

# Use edit_node_by_uuid from dialog_operations
async def show_node_edit_dialog(main_window, node_uuid):
    """Open the NodeDialog in edit mode for a specific node."""
    await edit_node_by_uuid(main_window, node_uuid)
