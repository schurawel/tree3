from PyQt6 import QtWidgets
from PyQt6.QtCore import QUrl, Qt, QEvent, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor, QDesktopServices, QIcon, QScreen
import networkx as nx
import logging
import uuid
import os
import sys
import asyncio
import qasync
import signal
import pickle
import base64
from qasync import QEventLoop, QApplication
import functools
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ResearchGuidePackage.FrontendModule import menu_bar, import_graph, toolbar, tools
from ResearchGuidePackage.FrontendModule.mpl_canvas import MplCanvas
from ResearchGuidePackage.FrontendModule.ModularTabs.abstract_tabs import ContentTabWidget
from ResearchGuidePackage.FrontendModule.ModularTabs.page_editor import PageEditor  # Add this import
from ResearchGuidePackage.FrontendModule.client import APIClient
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.dialog_operations import edit_node_by_uuid

# Configure logging


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""
    calculation_done = pyqtSignal(str)  # Add new signal

    def __init__(self, *args, **kwargs):
        """Initialize MainWindow."""
        super().__init__(*args, **kwargs)
        logging.info("Initializing MainWindow...")
        try:
            self.graph = None  # No graph loaded initially
            self.selected_node = None # Currently selected node
            self.startup_complete = False  # Flag to track if startup has completed

            # Initialize canvas as None - it will be set by GraphTab
            self.canvas = None
            logging.info("Canvas reference initialized.")

            # Create a widget to hold the toolbar buttons
            self.toolbar_widget = QtWidgets.QWidget(self)
            self.toolbar_layout = QtWidgets.QHBoxLayout(self.toolbar_widget)
            self.toolbar_widget.setLayout(self.toolbar_layout)
            logging.info("Toolbar widget created.")

            # Don't create toolbar here - will be done by GraphTab

            # Initialize communication
            self.communication = APIClient()
            
            self.initialize_ui()
            
            # Load last graph ONLY on startup, then mark startup as complete
            asyncio.create_task(self.startup_load_graph())

            # Start the window maximized (full window size but not full screen)
            self.showMaximized()
            
            logging.info("MainWindow initialized and shown maximized.")

            # Add calculator window attribute
            self.calculator_window = None

        except Exception as e:
            logging.error(f"Error during MainWindow initialization: {e}")

    def get_event_loop(self):
        """Get the current event loop."""
        return asyncio.get_event_loop()
    
    def read_version_info(self):
        """Read application version information from version.txt."""
        version_info = {
            'APP_NAME': 'ResearchGuide',  # Default values
            'VERSION': '1.0.0'
        }
        
        try:
            # Find version.txt in project root directory
            version_file_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), '..', '..', 'version.txt'
            ))
            
            if os.path.exists(version_file_path):
                with open(version_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line:
                            key, value = line.split('=', 1)
                            version_info[key] = value
                logging.info(f"Version info loaded from {version_file_path}")
            else:
                logging.warning(f"Version file not found at {version_file_path}")
        except Exception as e:
            logging.error(f"Error reading version info: {e}")
            
        return version_info
    
    def initialize_ui(self):
        """Initialize user interface elements."""
        # Read version info for window title
        version_info = self.read_version_info()
        app_name = version_info.get('APP_NAME', 'ResearchGuideUnearth')
        version = version_info.get('VERSION', '1.0.0')
        
        self.setWindowTitle(f"{app_name} {version}")

        # Set the application icon
        app_icon = QIcon(os.path.abspath(os.path.join(os.path.dirname(__file__), 'resources', 'Icons', 'icons8-library-96.png')))
        self.setWindowIcon(app_icon)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout()
        logging.info("Main layout created.")
        
        # Create the multi-tab content widget - now it's the only main component
        self.content_tabs = ContentTabWidget(self)
        main_layout.addWidget(self.content_tabs)
        
        # Store a reference to current tab for backward compatibility
        self.page_editor = self.content_tabs.get_current_tab()
        
        logging.info("Content tabs created as central component.")
        
        # Set central widget
        self.set_central_widget(main_layout)
        logging.info("UI elements initialized.")
        
    def set_central_widget(self, main_layout):
        """Set central widget."""
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        logging.info("Central widget set.")

    def closeEvent(self, event: QEvent):
        """Handle close event using ticket system."""
        # Create async task to check if graph is modified and handle saving
        loop = asyncio.get_running_loop()
        future = asyncio.run_coroutine_threadsafe(self._async_close_event(event), loop)
        
        # This is a synchronous event handler that creates an async task
        # Do not make this method itself async
        
    async def _async_close_event(self, event):
        """Async implementation of closeEvent logic."""
        try:
            # Check if graph is modified using ticket system
            success, content, error = await self.communication.request_and_get_response(
                operation="get_graph_modified_status",
                params={},
                sender="Frontend"
            )
            
            is_modified = success and content.get("result", False)
            
            if is_modified:
                reply = QtWidgets.QMessageBox.question(
                    self, "Confirm Close",
                    "The graph has been modified. Do you want to save changes?",
                    QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Discard | QtWidgets.QMessageBox.StandardButton.Cancel
                )

                if reply == QtWidgets.QMessageBox.StandardButton.Save:
                    # Get last saved file path using ticket system
                    last_file = await self.get_last_saved_file_path()
                    if last_file:
                        # Save to existing file
                        await self.save_graph_to_file(last_file)
                    else:
                        # Save as new file
                        await self.save_graph_as()
                    event.accept()
                elif reply == QtWidgets.QMessageBox.StandardButton.Discard:
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
        except Exception as e:
            logging.error(f"Error in async close event: {e}")
            event.accept()  # Accept the close event even on error

    async def get_last_saved_file_path(self):
        """Get the last saved file path using the ticket system."""
        try:
            success, content, error = await self.communication.request_and_get_response(
                operation="get_last_saved_file_path",
                params={},
                sender="Frontend"
            )
            
            if success:
                return content.get("file_path")
            return None
        except Exception as e:
            logging.error(f"Error getting last saved file path: {e}")
            return None
            
    async def set_last_saved_file_path(self, file_path):
        """Set the last saved file path using the ticket system."""
        try:
            await self.communication.request_and_get_response(
                operation="set_last_saved_file_path",
                params={"file_path": file_path},
                sender="Frontend"
            )
            return True
        except Exception as e:
            logging.error(f"Error setting last saved file path: {e}")
            return False

    async def save_graph_to_file(self, file_path):
        """Save graph to the specified file using ticket system."""
        try:
            success, content, error = await self.communication.request_and_get_response(
                operation="save_graph",
                params={"file_path": file_path},
                sender="Frontend"
            )
            
            if success and content.get("result"):
                # Update last saved file path
                await self.set_last_saved_file_path(file_path)
                # Update window title
                await self.async_update_window_title()
                return True
            else:
                error_msg = error or "Failed to save graph"
                QtWidgets.QMessageBox.critical(self, "Error", f"Error saving graph: {error_msg}")
                logging.error(f"Error saving graph: {error_msg}")
                return False
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error saving graph: {e}")
            logging.error(f"Error saving graph: {e}")
            return False
            
    async def save_graph_as(self):
        """Show save as dialog and save the graph using ticket system."""
        caption = "Save Laboratory As"
        directory = ""
        filter = "Graph Database (*.db)"
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, caption, directory, filter
        )
        if file_path and not file_path.endswith(".db"):
            file_path += ".db"

        if file_path:
            return await self.save_graph_to_file(file_path)
        return False

    async def async_update_window_title(self):
        """Asynchronously update window title using ticket system."""
        # Read version info
        version_info = self.read_version_info()
        app_name = version_info.get('APP_NAME', 'ResearchGuideUnearth')
        version = version_info.get('VERSION', '1.0.0')
        base_title = f"{app_name} {version}"
        
        try:
            # Get the current graph
            graph = await self.get_graph()
            
            if not graph or not graph.nodes:
                self.setWindowTitle(f"{base_title} - [Empty]")
                return
                
            # Get modified status using ticket system
            success_mod, content_mod, error_mod = await self.communication.request_and_get_response(
                operation="get_graph_modified_status",
                params={},
                sender="Frontend"
            )
            
            is_modified = False
            if success_mod and "result" in content_mod:
                is_modified = bool(content_mod["result"])
            elif error_mod:
                logging.warning(f"Error getting graph modified status: {error_mod}")
            
            # Direct call to API for file path - don't use self.get_last_saved_file_path()
            success_path, content_path, error_path = await self.communication.request_and_get_response(
                operation="get_last_saved_file_path",
                params={},
                sender="Frontend"
            )
            
            # Get file path directly from API response
            file_path = None
            if success_path and "file_path" in content_path:
                file_path = content_path["file_path"]
            elif error_path:
                logging.warning(f"Error getting last saved file path: {error_path}")
            
            # Update window title based on available info
            if file_path:
                file_name = os.path.basename(file_path)
                if is_modified:
                    self.setWindowTitle(f"{base_title} - {file_name} [not saved]")
                else:
                    self.setWindowTitle(f"{base_title} - {file_name}")
                logging.debug(f"Updated window title with file: {file_name}")
            else:
                if is_modified:
                    self.setWindowTitle(f"{base_title} - [not saved]")
                else:
                    self.setWindowTitle(f"{base_title}")
                logging.debug("Updated window title without file path")
                
        except Exception as e:
            logging.error(f"Error updating window title: {e}", exc_info=True)
            self.setWindowTitle(f"{base_title}")

    def save_plot_as_image(self):
        """Delegate save plot as image to canvas."""
        if self.canvas:
            self.canvas.save_plot_as_image()
    
    async def _request_graph_operation(self, operation, params=None):
        """
        Generic method to request graph operations from backend and process responses.
        
        Args:
            operation: String name of the operation
            params: Dictionary of parameters (default: empty dict)
            
        Returns:
            tuple: (success, graph, file_path, error)
                - success: Boolean indicating if operation succeeded
                - graph: Deserialized graph object (or None)
                - file_path: File path if returned (or None)
                - error: Error message if any (or None)
        """
        try:
            if params is None:
                params = {}
                
            success, content, error = await self.communication.request_and_get_response(
                operation=operation,
                params=params,
                sender="Frontend",
            )
            
            if success and content:
                # Extract graph data if present
                graph = None
                if content.get("graph_data"):
                    try:
                        graph_data = base64.b64decode(content["graph_data"])
                        graph = pickle.loads(graph_data)
                        # Verify we actually got a valid graph object
                        if not isinstance(graph, nx.Graph):
                            logging.error(f"Deserialized object is not a graph: {type(graph)}")
                            return False, None, None, f"Deserialized object is not a graph: {type(graph)}"
                        logging.info(f"Successfully deserialized graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
                    except Exception as e:
                        logging.error(f"Failed to deserialize graph: {e}")
                        return False, None, None, f"Failed to deserialize graph: {e}"
                
                # Get result information
                result = content.get("result")
                file_path = content.get("file_path")
                
                # Be more explicit about the success/failure of graph operations
                if operation in ["load_last_graph", "load_graph", "create_new_graph"] and graph is None:
                    logging.warning(f"{operation} returned success=True but no valid graph was deserialized")
                    # Override success to False if we expected a graph but didn't get one
                    if result is True:
                        return False, None, file_path, "No valid graph returned despite success status"
                
                return True, graph, file_path, None
            else:
                return False, None, None, error or "Operation failed"
        except Exception as e:
            logging.error(f"Error in {operation}: {e}")
            return False, None, None, str(e)
    
    async def get_graph(self):
        """Fetch the graph from the backend."""
        success, graph, _, error = await self._request_graph_operation("get_graph")
        
        if not success:
            logging.error(f"Error getting graph: {error}")
        
        return graph
        
    async def startup_load_graph(self):
        """Initial graph loading on startup - tries to load last graph or creates a new one."""
        try:
            # Try to load the last graph
            success, graph, file_path, error = await self._request_graph_operation("load_last_graph")
            
            if success and graph:
                logging.info(f"Successfully loaded last graph from {file_path if file_path else 'unknown location'}")
                if file_path:
                    # Use the ticket system to set the last saved file path
                    await self.set_last_saved_file_path(file_path)
                await self.show_graph(graph)
            else:
                # If loading last graph fails, create a new one
                if error:
                    logging.warning(f"Error loading last graph: {error}")
                logging.info("Creating new graph")
                
                success, graph, _, error = await self._request_graph_operation("create_new_graph")
                if success and graph:
                    logging.info("Created new empty graph")
                    await self.show_graph(graph)
                else:
                    logging.error(f"Error creating new graph: {error}")
            
            # Mark startup as complete
            self.startup_complete = True
            
        except Exception as e:
            logging.error(f"Error during startup graph loading: {e}")
            self.startup_complete = True  # Set flag even on error

    async def show_graph(self, new_graph=None):
        """
        Central function to update GUI elements based on a given graph.
        Does NOT try to load last graph - that should only happen on startup.
        """
        try:
            # If no graph provided, fetch latest from backend
            if new_graph is None:
                success, graph, _, error = await self._request_graph_operation("get_graph")
                if success and graph:
                    new_graph = graph
                else:
                    logging.error(f"Failed to fetch latest graph: {error}")
                    return False
            
            # Store the current graph
            self.graph = new_graph
            
            # Update the graph visualization through the graph_tab
            if hasattr(self, 'tab_widget') and hasattr(self.tab_widget, 'graph_tab'):
                self.tab_widget.graph_tab.update_graph(new_graph)
            
            # Update other UI elements
            if hasattr(self, 'nodes_display'):
                self.nodes_display.render_nodes()
            
            if hasattr(self, 'zettelkasten_widget') and self.zettelkasten_widget:
                self.zettelkasten_widget.update_tree(new_graph)
            
            # Update namespaces view - directly access it in tab_widget
            if hasattr(self, 'tab_widget') and hasattr(self.tab_widget, 'namespaces_view'):
                logging.info("Refreshing namespaces view")
                self.tab_widget.namespaces_view.refresh_async()
            
            # Update page editor tabs AFTER graph is updated
            if hasattr(self, 'content_tabs'):
                logging.info("Refreshing page editors with updated graph")
                self.content_tabs.refresh_all()
            
            # Update window title
            await self.async_update_window_title()
            logging.info("GUI elements updated based on graph.")
            return True            
        except Exception as e:
            logging.error(f"Error in show_graph: {e}")
            return False

    # Deprecated - should not be called outside of startup
    async def load_last_graph(self):
        """
        DEPRECATED: This method should only be used during startup.
        Use startup_load_graph() for initialization or create_new_graph() for runtime.
        """
        logging.warning("load_last_graph() called outside of startup - this method is only intended for startup use")
        if not self.startup_complete:
            # Only allow during startup
            success, graph, file_path, _ = await self._request_graph_operation("load_last_graph")
            if success and graph:
                await self.show_graph(graph)
                if file_path:
                    # Use ticket system instead of direct graph_manager access
                    await self.set_last_saved_file_path(file_path)
                return True
        return False

    async def create_new_graph(self):
        """Create a new graph and show it."""
        success, graph, _, _ = await self._request_graph_operation("create_new_graph")
        if success:
            return await self.show_graph(graph)
        return False

    def open_node_in_page_editor(self, node_id):
        """
        Open a node in a page editor tab.
        - If there are no page editors open, opens in a new tab
        - If there are page editors open, uses the last focused one
        """
        try:
            # Try to convert string to UUID if needed
            if isinstance(node_id, str):
                try:
                    node_id = uuid.UUID(node_id)
                except ValueError:
                    logging.warning(f"Invalid node ID format: {node_id}")
                    return False
            
            # Check if node exists in graph
            if not self.graph or node_id not in self.graph:
                logging.warning(f"Cannot open node {node_id}: Node not found in graph")
                return False
            
            # Use the content_tabs' system to handle page opening
            if hasattr(self, 'content_tabs'):
                logging.info(f"Opening node {node_id} in page editor")
                
                # First, check if there's an existing page editor tab we can reuse
                existing_page_tab = self._find_last_focused_page_editor()
                
                if existing_page_tab:
                    # Use existing page editor tab - focus it and set the node
                    logging.info(f"Reusing existing page editor tab for node {node_id}")
                    
                    # Make sure this tab is focused
                    self.content_tabs.active_tab = existing_page_tab
                    
                    # Set the node in the dropdown - find its index
                    for i in range(existing_page_tab.node_dropdown.count()):
                        if existing_page_tab.node_dropdown.itemData(i) == str(node_id):
                            existing_page_tab.node_dropdown.setCurrentIndex(i)
                            existing_page_tab.setFocus()
                            return True
                    
                    # If we didn't find the node, the dropdown might need refreshing
                    existing_page_tab.refresh()
                    
                    # Try again
                    for i in range(existing_page_tab.node_dropdown.count()):
                        if existing_page_tab.node_dropdown.itemData(i) == str(node_id):
                            existing_page_tab.node_dropdown.setCurrentIndex(i)
                            existing_page_tab.setFocus()
                            return True
                
                # If no existing page editor or node not found in dropdown, create new tab
                page_editor = self.content_tabs.open_page(str(node_id))
                
                if page_editor:
                    page_editor.setFocus()
                    return True
                else:
                    logging.warning("Failed to open page editor tab")
            else:
                logging.warning("Content tabs not available")
            
            return False
        except Exception as e:
            logging.error(f"Error opening node {node_id}: {e}")
            return False
    
    def _find_last_focused_page_editor(self):
        """Find the most recently focused page editor tab, if any."""
        if not hasattr(self, 'content_tabs') or not self.content_tabs:
            return None
        
        # First check if the currently active tab is a page editor
        current_tab = self.content_tabs.get_current_tab()
        if current_tab and isinstance(current_tab, PageEditor):
            return current_tab
        
        # If not, look through all tabs for the first page editor we find
        # In a future enhancement, we could track the order of focus for all page editors
        for tab in self.content_tabs.content_tabs:
            if isinstance(tab, PageEditor):
                return tab
        
        # No page editor tabs found
        return None

    def switch_to_graph_tab_and_highlight_node(self, node_id):
        """Switch to graph tab and highlight the specified node."""
        # Open a discover tab
        discover_tab = self.content_tabs.open_discover()
        
        # Highlight the node if discover tab was opened successfully
        if discover_tab and hasattr(discover_tab, 'select_focus_node') and node_id:
            # Let the discover tab handle highlighting the node
            discover_tab.select_focus_node(node_id)
            
        # Return success if the node was highlighted
        return discover_tab is not None

    def open_by_id(self, node_id):
        """
        Universal method to open a node in the appropriate viewer based on its type.
        Handles pages, PDF files, and can be extended for other node types.
        
        Args:
            node_id: UUID or string ID of the node to open
            
        Returns:
            bool: True if node was successfully opened, False otherwise
        """
        try:
            # Standardize the node_id to UUID
            if isinstance(node_id, str):
                try:
                    node_id = uuid.UUID(node_id)
                except ValueError:
                    logging.warning(f"Invalid node ID format: {node_id}")
                    return False
            
            # Check if the node exists in the graph
            if not self.graph or node_id not in self.graph:
                logging.warning(f"Cannot open node {node_id}: Node not found in graph")
                return False
            
            # Get node data
            node_data = self.graph.nodes[node_id]
            node_type = node_data.get('node_type', '')
            file_path = node_data.get('file_path', '')
            
            # Add explicit logging to diagnose PDF detection issues
            logging.info(f"Opening node {node_id} with type='{node_type}', file_path='{file_path}'")
            
            # Check for PDF files FIRST, before checking node types
            if file_path and file_path.lower().endswith('.pdf'):
                # PDF FILES: ALWAYS use PDF viewer for any .pdf files, no matter what node type
                logging.info(f"PDF FILE DETECTED - Opening in PDF viewer: {file_path}")
                return self.open_node_in_pdf_viewer(node_id)
                
            # Non-PDF handling below:
            if node_type == 'page':
                # Pages always open in page editor
                logging.info(f"Opening page node {node_id} in page editor")
                return self.open_node_in_page_editor(node_id)
            elif node_type == 'file':
                # Non-PDF files - use node editor
                logging.info(f"Non-PDF file node: {node_id}")
                asyncio.create_task(edit_node_by_uuid(self, node_id))
                return True
            else:
                # For all other node types, use the node editor
                logging.info(f"Opening node {node_id} of type '{node_type}' in node editor")
                asyncio.create_task(edit_node_by_uuid(self, node_id))
                return True
        except Exception as e:
            logging.error(f"Error in open_by_id for node {node_id}: {e}")
            return False

    def open_node_in_pdf_viewer(self, node_id):
        """
        Open a file node in the PDF viewer tab.
        Similar to open_node_in_page_editor but for PDF files.
        """
        try:
            # Try to convert string to UUID if needed
            if isinstance(node_id, str):
                try:
                    node_id = uuid.UUID(node_id)
                except ValueError:
                    logging.warning(f"Invalid node ID format: {node_id}")
                    return False
            
            # Check if node exists in graph
            if not self.graph or node_id not in self.graph:
                logging.warning(f"Cannot open node {node_id}: Node not found in graph")
                return False
                
            # Check if this is a file node
            node_data = self.graph.nodes[node_id]
            file_path = node_data.get('file_path')
            
            if not file_path:
                logging.warning(f"Node {node_id} has no file_path")
                return False
            
            # Use the content_tabs system to open PDF viewer
            if hasattr(self, 'content_tabs'):
                logging.info(f"Opening PDF file node {node_id} in PDF viewer")
                
                # Create PDF viewer data
                pdf_data = {
                    "file_path": file_path,
                    "node_id": str(node_id)
                }
                
                # Open a new tab with PDF viewer
                pdf_viewer = self.content_tabs.open_pdf_viewer(pdf_data)
                if pdf_viewer:
                    return True
                    
            return False
        except Exception as e:
            logging.error(f"Error opening node {node_id} in PDF viewer: {e}")
            return False
   

class App:
    def __init__(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        # Setup qasync event loop
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        self.window = None

    def show_window(self):
        if self.window is None:
            self.window = MainWindow()
            self.window.show()
    
    def get_loop(self):
        return self.loop

    def get_main_window(self):
        return self.window

    async def run(self):
        self.show_window()
        await self.loop.run_forever()

def setup_gui():
    app = App()
    return app

def run_app():
    """Run the ResearchGuide application with async support."""
    try:
        app = App()
        app.show_window()
        
        # Handle ctrl+c gracefully
        for sig in (signal.SIGINT, signal.SIGTERM):
            app.loop.add_signal_handler(sig, lambda: app.loop.stop())
        
        # Run the event loop
        app.loop.run_forever()
    except Exception as e:
        logging.error(f"Error in run_app: {e}")
    finally:
        app.loop.close()