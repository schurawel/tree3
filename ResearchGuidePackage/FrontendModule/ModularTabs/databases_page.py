import os
import logging
import asyncio
import datetime
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, pyqtSignal
from ResearchGuidePackage.FrontendModule.client import APIClient

logger = logging.getLogger('DatabasesPage')

class DatabasesPage(QtWidgets.QWidget):
    """Widget for managing database connections"""
    
    refresh_completed = pyqtSignal()
    
    def __init__(self, main_window):
        """Initialize the databases page."""
        super().__init__()
        self.main_window = main_window
        self.communication = APIClient()
        self.db_file_dir = os.path.expanduser("~/Documents")  # Default directory for database files
        self.current_db_path = None  # Track currently loaded database path
        
        self.init_ui()
        asyncio.create_task(self.load_available_databases())
        
        # Initialize current database info
        asyncio.create_task(self._init_current_database_info())
    
    async def _init_current_database_info(self):
        """Initialize current database info at startup."""
        # Get current database path from backend
        success, content, error = await self.communication.request_and_get_response(
            operation="get_last_saved_file_path",
            params={},
            sender="DatabasesPage"
        )
        
        if success and content:
            db_path = None
            
            # Check for file_path field first
            if "file_path" in content and isinstance(content["file_path"], (str, bytes, os.PathLike)):
                db_path = content["file_path"]
            # Fall back to result field
            elif "result" in content and isinstance(content["result"], (str, bytes, os.PathLike)):
                db_path = content["result"]
                
            if db_path and os.path.exists(db_path):
                self.current_db_path = db_path
                self.update_current_database_info(db_path)
                self.update_db_list_highlight()

    def init_ui(self):
        """Initialize the user interface components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header label
        header_label = QtWidgets.QLabel("Database Management")
        header_font = header_label.font()
        header_font.setBold(True)
        header_font.setPointSize(14)
        header_label.setFont(header_font)
        layout.addWidget(header_label)
        
        # Description label
        desc_label = QtWidgets.QLabel("Manage your research database connections. Add, remove, open, and save databases.")
        layout.addWidget(desc_label)
        layout.addSpacing(10)
        
        # Current database indicator in a frame for better visibility
        current_db_frame = QtWidgets.QFrame()
        current_db_frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        current_db_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        current_db_layout = QtWidgets.QVBoxLayout(current_db_frame)
        
        current_db_header = QtWidgets.QLabel("Current Database")
        current_db_header.setStyleSheet("font-weight: bold;")
        current_db_layout.addWidget(current_db_header)
        
        # Two separate rows for name and status
        self.current_db_label = QtWidgets.QLabel("None")
        self.current_db_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        current_db_layout.addWidget(self.current_db_label)
        
        # Add creation date and last modified date
        dates_layout = QtWidgets.QGridLayout()
        dates_layout.addWidget(QtWidgets.QLabel("Created:"), 0, 0)
        self.created_date_label = QtWidgets.QLabel("N/A")
        dates_layout.addWidget(self.created_date_label, 0, 1)
        
        dates_layout.addWidget(QtWidgets.QLabel("Last modified:"), 1, 0)
        self.modified_date_label = QtWidgets.QLabel("N/A")
        dates_layout.addWidget(self.modified_date_label, 1, 1)
        
        # Add database statistics section
        dates_layout.addWidget(QtWidgets.QLabel("Nodes:"), 2, 0)
        self.nodes_count_label = QtWidgets.QLabel("N/A")
        dates_layout.addWidget(self.nodes_count_label, 2, 1)
        
        dates_layout.addWidget(QtWidgets.QLabel("Edges:"), 3, 0)
        self.edges_count_label = QtWidgets.QLabel("N/A")
        dates_layout.addWidget(self.edges_count_label, 3, 1)
        
        current_db_layout.addLayout(dates_layout)
        
        # Modified indicator
        modified_layout = QtWidgets.QHBoxLayout()
        modified_layout.addWidget(QtWidgets.QLabel("Status:"))
        self.modified_label = QtWidgets.QLabel("No changes")
        self.modified_label.setStyleSheet("color: gray;")
        modified_layout.addWidget(self.modified_label)
        modified_layout.addStretch(1)
        current_db_layout.addLayout(modified_layout)
        
        layout.addWidget(current_db_frame)

        # Save operations in separate section
        save_group = QtWidgets.QGroupBox("Save Operations")
        save_layout = QtWidgets.QHBoxLayout(save_group)
        
        # Save database button
        save_button = QtWidgets.QPushButton("Save")
        save_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        save_button.setToolTip("Save current database")
        save_button.clicked.connect(self.save_database)
        save_layout.addWidget(save_button)
        
        # Save As button
        save_as_button = QtWidgets.QPushButton("Save As...")
        save_as_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton))
        save_as_button.setToolTip("Save current database to a new file")
        save_as_button.clicked.connect(self.save_as_database)
        save_layout.addWidget(save_as_button)
        
        layout.addWidget(save_group)

        save_layout.addStretch(1)
        layout.addSpacing(20)
        
        # Available databases list
        list_label = QtWidgets.QLabel("Available Databases:")
        list_font = list_label.font()
        list_font.setBold(True)
        list_label.setFont(list_font)
        layout.addWidget(list_label)
        
        self.db_list = QtWidgets.QListWidget()
        self.db_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.db_list.setAlternatingRowColors(True)
        self.db_list.itemDoubleClicked.connect(self.on_db_double_clicked)
        layout.addWidget(self.db_list)
        
        # Main buttons layout (Add, Open, New, Remove)
        buttons_layout = QtWidgets.QHBoxLayout()
        
        # Add database button
        add_button = QtWidgets.QPushButton("Add Database")
        add_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogNewFolder))
        add_button.setToolTip("Add a database file to the list")
        add_button.clicked.connect(self.add_database)
        buttons_layout.addWidget(add_button)
        
        # Open database button - now positioned next to Add Database
        open_button = QtWidgets.QPushButton("Open")
        open_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton))
        open_button.setToolTip("Open selected database")
        open_button.clicked.connect(self.open_selected_database)
        buttons_layout.addWidget(open_button)
        
        # New database button - moved to main buttons
        new_button = QtWidgets.QPushButton("New Database")
        new_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon))
        new_button.setToolTip("Create a new empty database")
        new_button.clicked.connect(self.new_database)
        buttons_layout.addWidget(new_button)
        
        # Remove database button
        remove_button = QtWidgets.QPushButton("Remove")
        remove_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TrashIcon))
        remove_button.setToolTip("Remove selected database from list")
        remove_button.clicked.connect(self.remove_database)
        buttons_layout.addWidget(remove_button)
        
        buttons_layout.addStretch(1)
        layout.addLayout(buttons_layout)
        layout.addSpacing(20)
        
        # Status label at the bottom
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # Update current database info
        self.update_current_database_info()

    def update_current_database_info(self, specific_file_path=None): # Modified
        """Update the current database information display."""
        asyncio.create_task(self._async_update_database_info(specific_file_path=specific_file_path)) # Modified
    
    async def _async_update_database_info(self, specific_file_path=None): 
        """Asynchronously update database info."""
        try:
            path_to_display = None

            if specific_file_path and isinstance(specific_file_path, (str, bytes, os.PathLike)) and os.path.exists(specific_file_path):
                path_to_display = specific_file_path
                # Update our tracked current path
                self.current_db_path = specific_file_path
                logger.info(f"Updating DB info using provided path: {path_to_display}")
            else:
                # Get last saved file path from backend
                success, content, error = await self.communication.request_and_get_response(
                    operation="get_last_saved_file_path",
                    params={},
                    sender="DatabasesPage"
                )
                
                if success and content:
                    # Check for file_path field first (correct field)
                    if "file_path" in content and content["file_path"] and isinstance(content["file_path"], str):
                        backend_path = content["file_path"]
                        logger.info(f"Using file_path from backend response: {backend_path}")
                        
                        if os.path.exists(backend_path):
                            path_to_display = backend_path
                            # Update our tracked current path
                            self.current_db_path = backend_path
                            logger.info(f"Updating DB info using backend path: {path_to_display}")
                        else:
                            logger.warning(f"Backend path '{backend_path}' does not exist")
                    else:
                        # Log this scenario - this is what's causing our warning
                        if "file_path" in content:
                            logger.warning(f"Backend returned null or invalid file_path: {content['file_path']}")
                        else:
                            logger.warning("Backend response did not contain a file_path field")
                elif error:
                    logger.warning(f"Failed to get last saved file path from backend: {error}")

            if path_to_display:
                self.current_db_label.setText(os.path.basename(path_to_display))
                self.current_db_label.setToolTip(path_to_display)
                
                # Update creation and modification dates
                try:
                    creation_timestamp = os.path.getctime(path_to_display)
                    creation_date = datetime.datetime.fromtimestamp(creation_timestamp)
                    self.created_date_label.setText(creation_date.strftime("%Y-%m-%d %H:%M"))
                except Exception as e:
                    logger.warning(f"Error getting creation date for {path_to_display}: {e}")
                    self.created_date_label.setText("Unknown")
                    
                try:
                    modified_timestamp = os.path.getmtime(path_to_display)
                    modified_date = datetime.datetime.fromtimestamp(modified_timestamp)
                    self.modified_date_label.setText(modified_date.strftime("%Y-%m-%d %H:%M"))
                except Exception as e:
                    logger.warning(f"Error getting modification date for {path_to_display}: {e}")
                    self.modified_date_label.setText("Unknown")
                    
                # Get database statistics (nodes, edges)
                await self.update_database_statistics()
            else:
                # No valid path to display, reset labels
                logger.info("No valid path to display, resetting DB info labels to None/N/A.")
                self.current_db_label.setText("None")
                self.current_db_label.setToolTip("")
                self.created_date_label.setText("N/A")
                self.modified_date_label.setText("N/A")
                self.nodes_count_label.setText("N/A")
                self.edges_count_label.setText("N/A")
            
            # Get modified status of the in-memory graph
            success_mod, content_mod, error_mod = await self.communication.request_and_get_response(
                operation="get_graph_modified_status",
                params={},
                sender="DatabasesPage"
            )
            
            if success_mod:
                is_modified = content_mod.get("result", False)
                if is_modified:
                    self.modified_label.setText("Modified")
                    self.modified_label.setStyleSheet("color: red; font-weight: bold;")
                else:
                    self.modified_label.setText("No changes")
                    self.modified_label.setStyleSheet("color: gray;")
            elif error_mod:
                logger.warning(f"Failed to get graph modified status: {error_mod}")
            
            # Update the highlight in the database list
            self.update_db_list_highlight()
            
        except Exception as e:
            logger.error(f"Error updating database info: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
    
    async def update_database_statistics(self):
        """Fetch and update database statistics (number of nodes, edges)."""
        try:
            await self._fallback_get_statistics()
                
        except Exception as e:
            logger.warning(f"Error getting database statistics: {e}")
            await self._fallback_get_statistics()
            
    async def _fallback_get_statistics(self):
        """Fallback method to get graph statistics if main method fails."""
        try:
            # Get the graph directly
            success, content, error = await self.communication.request_and_get_response(
                operation="get_graph",
                params={},
                sender="DatabasesPage"
            )
            
            if success and "graph_data" in content:
                # Parse pickle and extract stats
                import pickle
                import base64
                
                graph_data = base64.b64decode(content["graph_data"])
                graph = pickle.loads(graph_data)
                
                # Update statistics from graph
                self.nodes_count_label.setText(str(len(graph.nodes)))
                self.edges_count_label.setText(str(len(graph.edges)))
            else:
                self.nodes_count_label.setText("N/A")
                self.edges_count_label.setText("N/A")
                
        except Exception as e:
            logger.error(f"Error in fallback statistics retrieval: {e}")
            self.nodes_count_label.setText("N/A")
            self.edges_count_label.setText("N/A")

    async def load_available_databases(self):
        """Load the list of available databases from backend API."""
        self.db_list.clear()
        databases = []
        
        try:
            self.status_label.setText("Loading available databases...")
            
            success, content, error = await self.communication.request_and_get_response(
                operation="list_available_databases",
                params={},
                sender="DatabasesPage"
            )
            
            if success and content.get("result") and "databases" in content:
                databases = content["databases"]
                
                for path in databases:
                    if os.path.exists(path):
                        item = QtWidgets.QListWidgetItem(os.path.basename(path))
                        item.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DriveHDIcon))
                        item.setToolTip(path)
                        item.setData(Qt.ItemDataRole.UserRole, path)
                        self.db_list.addItem(item)
            
            self.status_label.setText(f"Loaded {self.db_list.count()} database(s)")
            
            # Update highlighting of current database
            self.update_db_list_highlight()
            
            return databases
            
        except Exception as e:
            logger.error(f"Error loading available databases: {e}")
            self.status_label.setText(f"Error loading databases: {str(e)}")
            return []
    
    async def save_available_databases(self, databases=None):
        """
        This method is no longer necessary as database list is managed by backend.
        It's kept as a stub for compatibility.
        """
        logger.info("Database list is now managed by backend API")
        return True
    
    def add_database(self):
        """Add a new database file to the list."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Add Database", self.db_file_dir,
            "Graph Database (*.db);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Update last used directory
        self.db_file_dir = os.path.dirname(file_path)
        
        # Check if this db is already in the list
        for i in range(self.db_list.count()):
            item = self.db_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                self.db_list.setCurrentItem(item)
                self.status_label.setText("Database already in list")
                return
        
        # Add to backend registry
        asyncio.create_task(self._async_add_database(file_path))
    
    async def _async_add_database(self, file_path):
        """Asynchronously add database to registry."""
        try:
            success, content, error = await self.communication.request_and_get_response(
                operation="add_database_to_list",
                params={"file_path": file_path},
                sender="DatabasesPage"
            )
            
            if success:
                # Refresh the database list
                await self.load_available_databases()
                self.status_label.setText(f"Added database: {os.path.basename(file_path)}")
            else:
                self.status_label.setText(f"Error adding database: {error}")
                
        except Exception as e:
            logger.error(f"Error adding database: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    def remove_database(self):
        """Remove selected database from the list."""
        selected_items = self.db_list.selectedItems()
        if not selected_items:
            self.status_label.setText("No database selected")
            return
        
        selected_item = selected_items[0]
        db_name = selected_item.text()
        db_path = selected_item.data(Qt.ItemDataRole.UserRole)
        
        # Remove "● " prefix if present for display
        if db_name.startswith("● "):
            db_name = db_name[2:]
        
        # Confirm deletion
        confirm = QtWidgets.QMessageBox.question(
            self, 
            "Confirm Removal",
            f"Remove {db_name} from the database list?\n\nNote: This will only remove it from the list, not delete the file.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
            # Check if we're removing the currently active database
            is_current_database = (self.current_db_path == db_path)
            
            # Remove from backend registry
            asyncio.create_task(self._async_remove_database(db_path, is_current_database))

    async def _async_remove_database(self, db_path, is_current_database):
        """Asynchronously remove database from registry."""
        try:
            success, content, error = await self.communication.request_and_get_response(
                operation="remove_database_from_list",
                params={"file_path": db_path},
                sender="DatabasesPage"
            )
            
            if success:
                # Refresh the database list
                await self.load_available_databases()
                
                # If we removed the current database, reset the current database view
                if is_current_database:
                    logger.info("Removed the currently active database, resetting current database view")
                    self.current_db_path = None
                    self.update_current_database_info(None)
                    # Update window title
                    asyncio.create_task(self.main_window.async_update_window_title())
                
                self.status_label.setText(f"Removed database: {os.path.basename(db_path)}")
            else:
                self.status_label.setText(f"Error removing database: {error}")
                
        except Exception as e:
            logger.error(f"Error removing database: {e}")
            self.status_label.setText(f"Error: {str(e)}")

    def on_db_double_clicked(self, item):
        """Handle double-click on a database in the list."""
        self.open_selected_database()
    
    def open_selected_database(self):
        """Open the currently selected database."""
        selected_items = self.db_list.selectedItems()
        if not selected_items:
            self.status_label.setText("No database selected")
            return
        
        file_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
        self._open_database_file(file_path)
    
    def _open_database_file(self, file_path):
        """Open a database file using the backend."""
        if not os.path.exists(file_path):
            QtWidgets.QMessageBox.critical(
                self, 
                "Error",
                f"Database file not found:\n{file_path}"
            )
            return
        
        # Check if there are unsaved changes in current database
        asyncio.create_task(self._async_open_database(file_path))
    
    async def _async_open_database(self, file_path):
        """Asynchronously open a database file."""
        try:
            self.status_label.setText(f"Opening database: {os.path.basename(file_path)}...")
            
            # Check for modifications first
            success_mod_check, content_mod_check, error_mod_check = await self.communication.request_and_get_response(
                operation="get_graph_modified_status",
                params={},
                sender="DatabasesPage"
            )
            
            if success_mod_check and content_mod_check.get("result", False):
                # Database is modified, ask to save before closing
                confirm = QtWidgets.QMessageBox.question(
                    self, 
                    "Save Changes?",
                    f"Current database has unsaved changes. Save before closing and opening {os.path.basename(file_path)}?",
                    QtWidgets.QMessageBox.StandardButton.Yes | 
                    QtWidgets.QMessageBox.StandardButton.No |
                    QtWidgets.QMessageBox.StandardButton.Cancel
                )
                
                if confirm == QtWidgets.QMessageBox.StandardButton.Cancel:
                    self.status_label.setText("Database opening canceled")
                    return
                
                if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
                    # Save current database first
                    logger.info(f"Saving current database before closing it")
                    save_success, _, save_error = await self.communication.request_and_get_response(
                        operation="save_graph",
                        params={}, # Save to its current path if known, or prompt if not
                        sender="DatabasesPage"
                    )
                    
                    if not save_success:
                        QtWidgets.QMessageBox.critical(
                            self, 
                            "Error",
                            f"Failed to save current database: {save_error or 'Unknown error'}"
                        )
                        self.status_label.setText("Error saving current database")
                        return
            
            # Log that we're closing the current database
            if self.current_db_path:
                logger.info(f"Closing current database: {self.current_db_path}")
            
            # First store the original path in case we need to rollback
            original_db_path = self.current_db_path
            
            # Clear the current database path before loading new one
            self.current_db_path = None
            self.update_current_database_info(None)
            
            # Now load the new database with explicit timeout
            logger.info(f"Opening new database: {file_path}")
            
            # First, forcefully create a new empty graph to clear all existing state
            clear_success, _, clear_error = await self.communication.request_and_get_response(
                operation="create_new_graph",
                params={},
                sender="DatabasesPage",
            )
            
            if not clear_success:
                logger.warning(f"Failed to clear graph state before loading: {clear_error}")
                # Continue anyway, but log the warning
            
            # Now load the new database
            load_success, load_content, load_error = await self.communication.request_and_get_response(
                operation="load_graph",
                params={"file_path": file_path},
                sender="DatabasesPage",
            )
            
            if load_success and load_content.get("result"):
                # Successfully loaded the database
                logger.info(f"Database loaded successfully: {file_path}")
                self.status_label.setText(f"Database loaded: {os.path.basename(file_path)}")
                
                # Update our tracked current path
                self.current_db_path = file_path

                set_path_success, set_path_content, set_path_error = await self.communication.request_and_get_response(
                    operation="set_last_saved_file_path",
                    params={"file_path": file_path},
                    sender="DatabasesPage",
                    timeout=30
                )
                
                verify_success, verify_content, verify_error = await self.communication.request_and_get_response(
                    operation="get_last_saved_file_path",
                    params={},
                    sender="DatabasesPage",
                )
                
                # Continue with UI updates
                await self.main_window.async_update_window_title()
                self.log_last_file_path(file_path)
                self.update_current_database_info(specific_file_path=file_path)
                self.update_db_list_highlight()
                
                # Refresh main window and dependent components
                if hasattr(self.main_window, 'show_graph'):
                    # Use show_graph with None to force a fresh fetch from backend
                    await self.main_window.show_graph(None)
                elif hasattr(self.main_window, 'refresh_graph'):
                    await self.main_window.refresh_graph()
                
                # Refresh content tabs if they exist
                if hasattr(self.main_window, 'content_tabs') and hasattr(self.main_window.content_tabs, 'refresh_all'):
                    self.main_window.content_tabs.refresh_all()
                
                return True
            else:
                # Loading failed
                error_msg = load_error or "Unknown error"
                logger.error(f"Failed to load database: {error_msg}")
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Failed to load database: {error_msg}"
                )
                self.status_label.setText("Error loading database")
                
                # Restore original database state if there was one
                if original_db_path:
                    logger.info(f"Restoring original database state: {original_db_path}")
                    self.current_db_path = original_db_path
                    self.update_current_database_info(specific_file_path=original_db_path)
                    self.update_db_list_highlight()
                
                return False
        
        except Exception as e:
            logger.error(f"Error opening database: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Error opening database: {str(e)}")
            return False

    def new_database(self):
        """Create a new empty database."""
        # Check if there are unsaved changes in current database
        asyncio.create_task(self._async_new_database())
    
    async def _async_new_database(self):
        """Asynchronously create a new database."""
        try:
            # Check for modifications first
            success, content, error = await self.communication.request_and_get_response(
                operation="get_graph_modified_status",
                params={},
                sender="DatabasesPage"
            )
            
            if success and content.get("result", False):
                # Database is modified, ask to save
                confirm = QtWidgets.QMessageBox.question(
                    self, 
                    "Save Changes?",
                    "Current database has unsaved changes. Save before creating a new database?",
                    QtWidgets.QMessageBox.StandardButton.Yes | 
                    QtWidgets.QMessageBox.StandardButton.No |
                    QtWidgets.QMessageBox.StandardButton.Cancel
                )
                
                if confirm == QtWidgets.QMessageBox.StandardButton.Cancel:
                    self.status_label.setText("New database creation canceled")
                    return
                
                if confirm == QtWidgets.QMessageBox.StandardButton.Yes:
                    # Save current database first
                    save_success, save_content, save_error = await self.communication.request_and_get_response(
                        operation="save_graph",
                        params={},
                        sender="DatabasesPage"
                    )
                    
                    if not save_success:
                        QtWidgets.QMessageBox.critical(
                            self, 
                            "Error",
                            f"Failed to save current database: {save_error or 'Unknown error'}"
                        )
                        self.status_label.setText("Error saving current database")
                        return
            
            # Create new database
            new_success, new_content, new_error = await self.communication.request_and_get_response(
                operation="create_new_graph",
                params={},
                sender="DatabasesPage"
            )
            
            if new_success:
                # Successfully created new database
                self.status_label.setText("New database created")
                
                # Clear tracked current path since this is a new unsaved database
                self.current_db_path = None
                
                # Update window title
                await self.main_window.async_update_window_title()
                
                # Update database info
                self.update_current_database_info()
                
                # Update the list highlighting
                self.update_db_list_highlight()
                
                # Refresh any graph views
                if hasattr(self.main_window, 'content_tabs') and hasattr(self.main_window.content_tabs, 'refresh_all'):
                    self.main_window.content_tabs.refresh_all()
            else:
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Failed to create new database: {new_error or 'Unknown error'}"
                )
                self.status_label.setText("Error creating new database")
        
        except Exception as e:
            logger.error(f"Error creating new database: {e}")
            self.status_label.setText(f"Error: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Error creating new database: {str(e)}")
    
    def save_database(self):
        """Save the current database."""
        asyncio.create_task(self._async_save_database())
    
    async def _async_save_database(self):
        """Asynchronously save the current database."""
        try:
            # Get current file path
            path_success, path_content, path_error = await self.communication.request_and_get_response(
                operation="get_last_saved_file_path",
                params={},
                sender="DatabasesPage"
            )
            
            if path_success and path_content:
                # First try to get the file_path field which is the correct one
                if "file_path" in path_content and isinstance(path_content["file_path"], (str, bytes, os.PathLike)):
                    current_file_path = path_content["file_path"]
                    logger.info(f"Using file_path from response: {current_file_path}")
                # Fall back to result field for backwards compatibility
                elif "result" in path_content and isinstance(path_content["result"], (str, bytes, os.PathLike)):
                    current_file_path = path_content["result"]
                    logger.info(f"Using result field as file path: {current_file_path}")
                else:
                    # If result is a boolean or other non-path value, we don't have a valid path
                    if "result" in path_content:
                        logger.warning(f"Invalid file path type from get_last_saved_file_path: {type(path_content['result']).__name__}")
                    current_file_path = None
                
                # We have a valid path string, save to it
                if current_file_path and os.path.exists(current_file_path):
                    save_success, save_content, save_error = await self.communication.request_and_get_response(
                        operation="save_graph",
                        params={"file_path": current_file_path},
                        sender="DatabasesPage"
                    )
                    
                    if save_success:
                        # Update our tracked current path
                        self.current_db_path = current_file_path
                        
                        # Update UI and log file
                        self.status_label.setText(f"Database saved: {os.path.basename(current_file_path)}")
                        self.update_current_database_info(specific_file_path=current_file_path)
                        self.log_last_file_path(current_file_path)
                        self.update_db_list_highlight()
                    else:
                        QtWidgets.QMessageBox.critical(
                            self, 
                            "Error", 
                            f"Failed to save database: {save_error or 'Unknown error'}"
                        )
                        self.status_label.setText("Error saving database")
                else:
                    # No valid path, do a save as
                    logger.info("No valid save path available - using Save As...")
                    self.save_as_database()
            else:
                # No path information from backend, do a save as
                logger.info("No path information from backend - using Save As...")
                self.save_as_database()
        
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            self.status_label.setText(f"Error: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Error saving database: {str(e)}")
    
    def save_as_database(self):
        """Save the current database to a new file."""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Database As", self.db_file_dir,
            "Graph Database (*.db)"
        )
        
        if not file_path:
            return
            
        # Ensure .db extension
        if not file_path.endswith(".db"):
            file_path += ".db"
        
        # Update last used directory
        self.db_file_dir = os.path.dirname(file_path)
        
        # Save the database
        asyncio.create_task(self._async_save_as_database(file_path))
    
    async def _async_save_as_database(self, file_path):
        """Asynchronously save the current database to a new file."""
        try:
            save_success, save_content, save_error = await self.communication.request_and_get_response(
                operation="save_graph",
                params={"file_path": file_path},
                sender="DatabasesPage"
            )
            
            if save_success:
                # Update our tracked current path
                self.current_db_path = file_path
                
                self.status_label.setText(f"Database saved as: {os.path.basename(file_path)}")
                
                # Add to list if not already there
                found = False
                for i in range(self.db_list.count()):
                    item = self.db_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == file_path:
                        self.db_list.setCurrentItem(item)
                        found = True
                        break
                
                if not found:
                    item = QtWidgets.QListWidgetItem(os.path.basename(file_path))
                    item.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DriveHDIcon))
                    item.setToolTip(file_path)
                    item.setData(Qt.ItemDataRole.UserRole, file_path)
                    self.db_list.addItem(item)
                    self.db_list.setCurrentItem(item)
                    self.save_available_databases()
                
                # Update window title
                await self.main_window.async_update_window_title()
                # After saving to a new path, update info using that new path
                self.update_current_database_info(specific_file_path=file_path)
                
                # Update log file
                self.log_last_file_path(file_path)
                
                # Update list highlighting
                self.update_db_list_highlight()
            else:
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Failed to save database: {save_error or 'Unknown error'}"
                )
                self.status_label.setText("Error saving database")
        
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            self.status_label.setText(f"Error: {str(e)}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Error saving database: {str(e)}")

    def get_tab_title(self):
        """Return the title for this tab."""
        return "Databases"
    
    def log_last_file_path(self, file_path):
        """Update the last accessed database in the backend."""
        asyncio.create_task(self._async_log_last_file_path(file_path))
    
    async def _async_log_last_file_path(self, file_path):
        """Asynchronously update the database registry with the last accessed file."""
        try:
            # Add the file to the database list (which will move it to the beginning)
            success, content, error = await self.communication.request_and_get_response(
                operation="add_database_to_list",
                params={"file_path": file_path},
                sender="DatabasesPage"
            )
            
            if success:
                # Refresh list in the UI
                await self.load_available_databases()
                logger.info(f"Updated last accessed database: {file_path}")
            else:
                logger.warning(f"Failed to update last accessed database: {error}")
                
        except Exception as e:
            logger.error(f"Error updating last accessed database: {e}", exc_info=True)

    def refresh(self):
        """Refresh all database information and UI elements."""
        # Reload database list
        asyncio.create_task(self.load_available_databases())
        
        # Update current database info
        self.update_current_database_info()
        
        # Update highlighting
        self.update_db_list_highlight()
        
        logger.info("Database manager refreshed")
    
    # Add this method if it's missing or not being recognized
    def update_db_list_highlight(self):
        """Update the visual highlighting for the currently active database in the list."""
        try:
            logger.debug(f"Updating database list highlighting, current_db_path: {self.current_db_path}")
            # Loop through all items in the list
            for i in range(self.db_list.count()):
                item = self.db_list.item(i)
                db_path = item.data(Qt.ItemDataRole.UserRole)
                font = item.font()
                
                # Check if this item is the current database
                if db_path == self.current_db_path:
                    # Make the text bold
                    font.setBold(True)
                else:
                    # Reset to normal text
                    font.setBold(False)
                
                # Apply the font to the item
                item.setFont(font)
                
            logger.debug("Database list highlighting update complete")
        except Exception as e:
            logger.error(f"Error in update_db_list_highlight: {e}", exc_info=True)
