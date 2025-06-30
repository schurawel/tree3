import os
import logging
import asyncio
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, pyqtSignal
from ResearchGuidePackage.FrontendModule.client import APIClient

logger = logging.getLogger('ImportExportPage')

class ImportExportPage(QtWidgets.QWidget):
    """Widget for managing import and export operations"""
    
    refresh_completed = pyqtSignal()
    
    def __init__(self, main_window):
        """Initialize the import/export page."""
        super().__init__()
        self.main_window = main_window
        self.communication = APIClient()
        
        # Setup UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header label
        header_label = QtWidgets.QLabel("Import & Export")
        header_font = header_label.font()
        header_font.setBold(True)
        header_font.setPointSize(14)
        header_label.setFont(header_font)
        layout.addWidget(header_label)
        
        # Description label
        desc_label = QtWidgets.QLabel("Import from various sources and export your research data to different formats.")
        layout.addWidget(desc_label)
        layout.addSpacing(20)
        
        # Import section
        import_group = QtWidgets.QGroupBox("Import Options")
        import_layout = QtWidgets.QVBoxLayout(import_group)
        
        # Import Markdown Folder button
        import_md_button = QtWidgets.QPushButton("Import Markdown Folder Structure")
        import_md_button.setIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogNewFolder))
        import_md_button.clicked.connect(self.import_markdown_folder)
        import_layout.addWidget(import_md_button)
        
        # Import GML File button
        import_gml_button = QtWidgets.QPushButton("Import GML File")
        import_gml_button.setIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon))
        import_gml_button.clicked.connect(self.import_gml_file)
        import_layout.addWidget(import_gml_button)
        
        layout.addWidget(import_group)
        layout.addSpacing(20)
        
        # Export section
        export_group = QtWidgets.QGroupBox("Export Options")
        export_layout = QtWidgets.QVBoxLayout(export_group)
        
        # Export as GML button
        export_gml_button = QtWidgets.QPushButton("Export as GML")
        export_gml_button.setIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileLinkIcon))
        export_gml_button.clicked.connect(self.export_as_gml)
        export_layout.addWidget(export_gml_button)
        
        # Export as CSV button
        export_csv_button = QtWidgets.QPushButton("Export as CSV")
        export_csv_button.setIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon))
        export_csv_button.clicked.connect(self.export_as_csv)
        export_layout.addWidget(export_csv_button)
        
        layout.addWidget(export_group)
        
        # Status label
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # Add spacer at bottom
        layout.addStretch(1)
    
    def import_markdown_folder(self):
        """Import a markdown folder structure."""
        # Show a folder dialog
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Markdown Folder to Import",
            os.path.expanduser("~/Documents")
        )
        
        if not folder_path:
            return  # User cancelled
        
        # Get destination database file path
        db_file_path = self.database_save_as_dialog()
        if not db_file_path:
            return  # User cancelled the save dialog
        
        # Start import task
        self.status_label.setText(f"Importing markdown folder: {folder_path}...")
        asyncio.create_task(self.async_import_markdown_folder(folder_path, db_file_path))
    
    async def async_import_markdown_folder(self, folder_path, db_file_path):
        """Asynchronously import a markdown folder structure."""
        try:
            # Use ticket system to import markdown folder
            success, content, error = await self.communication.request_and_get_response(
                operation="import_markdown_folder",
                params={"folder_path": folder_path, "db_file_path": db_file_path},
                sender="ImportExportPage"
            )
            
            if success and content.get("result"):
                # Load the created database
                success, content, error = await self.communication.request_and_get_response(
                    operation="load_graph",
                    params={"file_path": db_file_path},
                    sender="ImportExportPage"
                )
                
                if success:
                    # Update the UI
                    self.status_label.setText(f"Successfully imported markdown folder to {os.path.basename(db_file_path)}")
                    
                    # Set the last saved file path
                    await self.communication.request_and_get_response(
                        operation="set_last_saved_file_path",
                        params={"file_path": db_file_path},
                        sender="ImportExportPage"
                    )
                    
                    # Update main window with the new graph directly
                    await self.main_window.show_graph(None)
                    await self.main_window.async_update_window_title()
                    
                    # Optional: show success dialog
                    QtWidgets.QMessageBox.information(
                        self, 
                        "Import Successful",
                        f"Successfully imported markdown folder to {os.path.basename(db_file_path)}"
                    )
                else:
                    self.status_label.setText(f"Error loading imported database: {error}")
                    QtWidgets.QMessageBox.critical(
                        self, 
                        "Import Error", 
                        f"Error loading imported database: {error or 'Unknown error'}"
                    )
            else:
                self.status_label.setText(f"Error importing markdown folder: {error}")
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Import Error", 
                    f"Error importing markdown folder: {error or 'Unknown error'}"
                )
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, 
                "Import Error", 
                f"Error importing markdown folder: {str(e)}"
            )
            logger.error(f"Error importing markdown folder: {e}", exc_info=True)
    
    def import_gml_file(self):
        """Import a GML file."""
        # Show file dialog
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select GML File to Import",
            os.path.expanduser("~/Documents"),
            "GML Files (*.gml);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        # Start import task
        self.status_label.setText(f"Importing GML file: {file_path}...")
        asyncio.create_task(self.async_import_gml_file(file_path))
    
    async def async_import_gml_file(self, file_path):
        """Asynchronously import a GML file."""
        try:
            # Use ticket system to import GML file
            success, content, error = await self.communication.request_and_get_response(
                operation="load_graph_from_gml",
                params={"file_path": file_path},
                sender="ImportExportPage"
            )
            
            if success:
                self.status_label.setText(f"Successfully imported GML file: {os.path.basename(file_path)}")
                
                # Update main window with the new graph directly
                await self.main_window.show_graph(None)
                
                # Optional: show success dialog
                QtWidgets.QMessageBox.information(
                    self, 
                    "Import Successful",
                    f"Successfully imported GML file: {os.path.basename(file_path)}"
                )
            else:
                self.status_label.setText(f"Error importing GML file: {error}")
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Import Error", 
                    f"Error importing GML file: {error or 'Unknown error'}"
                )
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, 
                "Import Error", 
                f"Error importing GML file: {str(e)}"
            )
            logger.error(f"Error importing GML file: {e}", exc_info=True)
    
    def export_as_gml(self):
        """Export the current graph as a GML file."""
        # Show save dialog
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export as GML",
            os.path.expanduser("~/Documents"),
            "GML Files (*.gml)"
        )
        
        if not file_path:
            return  # User cancelled
        
        # Ensure .gml extension
        if not file_path.endswith(".gml"):
            file_path += ".gml"
        
        # Start export task
        self.status_label.setText(f"Exporting to GML file: {file_path}...")
        asyncio.create_task(self.async_export_as_gml(file_path))
    
    async def async_export_as_gml(self, file_path):
        """Asynchronously export the graph as a GML file."""
        try:
            # Use ticket system to export GML file
            success, content, error = await self.communication.request_and_get_response(
                operation="save_graph_as_gml",
                params={"file_path": file_path},
                sender="ImportExportPage"
            )
            
            if success and content.get("result"):
                self.status_label.setText(f"Successfully exported to GML file: {os.path.basename(file_path)}")
                
                # Optional: show success dialog
                QtWidgets.QMessageBox.information(
                    self, 
                    "Export Successful",
                    f"Successfully exported to GML file: {os.path.basename(file_path)}"
                )
            else:
                self.status_label.setText(f"Error exporting to GML: {error}")
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Export Error", 
                    f"Error exporting to GML: {error or 'Unknown error'}"
                )
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, 
                "Export Error", 
                f"Error exporting to GML: {str(e)}"
            )
            logger.error(f"Error exporting to GML: {e}", exc_info=True)
    
    def export_as_csv(self):
        """Export the current graph nodes and edges as CSV files."""
        # Show save dialog for nodes file
        nodes_file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Nodes as CSV",
            os.path.expanduser("~/Documents"),
            "CSV Files (*.csv)"
        )
        
        if not nodes_file_path:
            return  # User cancelled
        
        # Ensure .csv extension
        if not nodes_file_path.endswith(".csv"):
            nodes_file_path += ".csv"
        
        # Get base path for edges file
        base_path = os.path.splitext(nodes_file_path)[0]
        edges_file_path = f"{base_path}_edges.csv"
        
        # Start export task
        self.status_label.setText(f"Exporting to CSV files...")
        asyncio.create_task(self.async_export_as_csv(nodes_file_path, edges_file_path))
    
    async def async_export_as_csv(self, nodes_file_path, edges_file_path):
        """Asynchronously export the graph as CSV files."""
        try:
            # Use ticket system to export CSV files
            success, content, error = await self.communication.request_and_get_response(
                operation="export_graph_as_csv",
                params={
                    "nodes_file_path": nodes_file_path,
                    "edges_file_path": edges_file_path
                },
                sender="ImportExportPage"
            )
            
            if success and content.get("result"):
                self.status_label.setText(f"Successfully exported to CSV files")
                
                # Optional: show success dialog
                QtWidgets.QMessageBox.information(
                    self, 
                    "Export Successful",
                    f"Successfully exported to CSV files:\n"
                    f"Nodes: {os.path.basename(nodes_file_path)}\n"
                    f"Edges: {os.path.basename(edges_file_path)}"
                )
            else:
                self.status_label.setText(f"Error exporting to CSV: {error}")
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Export Error", 
                    f"Error exporting to CSV: {error or 'Unknown error'}"
                )
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, 
                "Export Error", 
                f"Error exporting to CSV: {str(e)}"
            )
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
    
    def database_save_as_dialog(self):
        """Show dialog to save a database file."""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Database As",
            os.path.expanduser("~/Documents"),
            "Graph Database (*.db)"
        )
        
        if file_path and not file_path.endswith(".db"):
            file_path += ".db"
            
        return file_path
    
    def get_tab_title(self):
        """Return the title for this tab."""
        return "Import/Export"
    
    def refresh(self):
        """Refresh the page. Required for tab interface compatibility."""
        # Currently nothing to refresh
        self.refresh_completed.emit()
