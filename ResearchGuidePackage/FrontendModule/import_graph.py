from PyQt6 import QtWidgets, QtCore
from ResearchGuidePackage.BackendModule.import_markdown_folder import import_markdown_folder_structure
from ResearchGuidePackage.FrontendModule.file_handler import *
import logging
import os
import uuid
import asyncio

logger = logging.getLogger(__name__)

def import_file(main_window):
    """Import graph from file."""
    dialog = ImportDialog(main_window)
    if dialog.exec():
        if dialog.import_type_dropdown.currentText() == "Import Markdown Folder Structure":
            asyncio.create_task(dialog.async_import_markdown_folder(main_window, dialog.path_edit.text()))
        elif dialog.import_type_dropdown.currentText() == "Import GML File":
            asyncio.create_task(dialog.async_import_gml_file(main_window, dialog.path_edit.text()))
        else:
            pass
            # Implement other import types here

class ImportDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Graph")
        self.setGeometry(100, 100, 400, 200)
        self.center_on_parent()

        layout = QtWidgets.QVBoxLayout()

        # Dropdown for import type
        self.import_type_label = QtWidgets.QLabel("Select Import Type:")
        self.import_type_dropdown = QtWidgets.QComboBox()
        self.import_type_dropdown.addItems(["Import GML File", "Import Markdown Folder Structure"])

        # Line edit and button to select file path
        self.path_label = QtWidgets.QLabel("Select File Path:")
        self.path_edit = QtWidgets.QLineEdit()
        self.path_button = QtWidgets.QPushButton("Choose File or Folder")
        self.path_button.clicked.connect(self.choose_file)
        self.import_type_dropdown.currentIndexChanged.connect(self.update_button_text)
        self.update_button_text() # Call it initially to set the correct text

        # OK and Cancel buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.import_type_label)
        layout.addWidget(self.import_type_dropdown)
        layout.addWidget(self.path_label)
        layout.addWidget(self.path_edit)
        layout.addWidget(self.path_button)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def update_button_text(self):
        """Update the button text based on the selected import type."""
        if self.import_type_dropdown.currentText() == "Import Markdown Folder Structure":
            self.path_button.setText("Choose Folder")
        elif self.import_type_dropdown.currentText() == "Import GML File":
            self.path_button.setText("Choose GML File")
        else:
            self.path_button.setText("Choose File or Folder")

    def choose_file(self):
        file_dialog = QtWidgets.QFileDialog(self)
        if self.import_type_dropdown.currentText() == "Import Markdown Folder Structure":
            file_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)
        elif self.import_type_dropdown.currentText() == "Import GML File":
             file_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
             file_dialog.setNameFilter("GML files (*.gml)")
        else:
            file_dialog.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)
        file_dialog.setOption(QtWidgets.QFileDialog.Option.ShowDirsOnly, False)
        file_dialog.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        if file_dialog.exec():
            file_name = file_dialog.selectedFiles()[0]
            self.path_edit.setText(file_name)

    def center_on_parent(self):
        """Center the dialog on its parent."""
        parent_geometry = self.parent().geometry()
        self_geometry = self.geometry()
        x = parent_geometry.x() + (parent_geometry.width() - self_geometry.width()) // 2
        y = parent_geometry.y() + (parent_geometry.height() - self_geometry.height()) // 2
        self.move(x, y)

    async def async_import_markdown_folder(self, main_window, folder_path):
        """Imports a markdown folder using the ticket system."""
        try:
            db_file_path = self.database_save_as_dialog()
            if not db_file_path:
                return  # User cancelled the save dialog

            # Use ticket system to import markdown folder
            success, content, error = await main_window.communication.request_and_get_response(
                operation="import_markdown_folder",
                params={"folder_path": folder_path, "db_file_path": db_file_path},
                sender="Frontend"
            )
            
            if success and content.get("result"):
                # Load the created database using the ticket system
                success, graph, file_path, error = await main_window._request_graph_operation(
                    operation="load_graph",
                    params={"file_path": db_file_path}
                )
                
                if success and graph:
                    # Set the last saved file path using ticket system
                    await main_window.set_last_saved_file_path(db_file_path)
                    await main_window.show_graph(graph)
                    logging.info(f"Imported markdown folder: {folder_path}")
                else:
                    QtWidgets.QMessageBox.critical(main_window, "Error", f"Error loading imported markdown database: {error or 'Unknown error'}")
            else:
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Error importing markdown folder: {error or 'Unknown error'}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error importing markdown folder: {e}")
            logging.error(f"Error importing markdown folder: {e}")

    def database_save_as_dialog(self):
        """Handle save as file action, enforcing .db extension."""
        caption = "Save Graph Database As"
        directory = ""  # You might want to set a default directory here
        filter = "Graph Database (*.db)"
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, caption, directory, filter
        )
        if file_path and not file_path.endswith(".db"):
            file_path += ".db"
        return file_path

    async def async_import_gml_file(self, main_window, file_path):
        """Imports a graph from a GML file using the ticket system."""
        try:
            # Use _request_graph_operation to handle graph deserialization
            success, graph, _, error = await main_window._request_graph_operation(
                operation="load_graph_from_gml",
                params={"file_path": file_path}
            )
            
            if success and graph:
                # Show the graph and set the path
                await main_window.show_graph(graph)
                # Set the file path for later use
                await main_window.set_last_saved_file_path(file_path)
                logging.info(f"Imported GML file: {file_path}")
            else:
                QtWidgets.QMessageBox.critical(main_window, "Error", f"Error importing GML file: {error or 'Unknown error'}")
                logging.error(f"Error importing GML file: {error or 'Unknown error'}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(main_window, "Error", f"Error importing GML file: {e}")
            logging.error(f"Error importing GML file: {e}")

