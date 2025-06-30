from PyQt6 import QtWidgets, QtCore
import logging
import networkx as nx
import asyncio

class ExportDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Graph")
        self.setGeometry(100, 100, 400, 200)
        self.center_on_parent()

        layout = QtWidgets.QVBoxLayout()

        # Dropdown for export type
        self.export_type_label = QtWidgets.QLabel("Select Export Type:")
        self.export_type_dropdown = QtWidgets.QComboBox()
        self.export_type_dropdown.addItems(["GML"])

        # Line edit and button to select file path
        self.path_label = QtWidgets.QLabel("Select File Path:")
        self.path_edit = QtWidgets.QLineEdit()
        self.path_button = QtWidgets.QPushButton("Choose File or Folder")
        self.path_button.clicked.connect(self.choose_file)

        # OK and Cancel buttons
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.export_type_label)
        layout.addWidget(self.export_type_dropdown)
        layout.addWidget(self.path_label)
        layout.addWidget(self.path_edit)
        layout.addWidget(self.path_button)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def choose_file(self):
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setNameFilter("GML Files (*.gml)")
        if file_dialog.exec():
            file_name = file_dialog.selectedFiles()[0]
            if not file_name.endswith(".gml"):
                file_name += ".gml"
            self.path_edit.setText(file_name)

    def center_on_parent(self):
        """Center the dialog on its parent."""
        parent_geometry = self.parent().geometry()
        self_geometry = self.geometry()
        x = parent_geometry.x() + (parent_geometry.width() - self_geometry.width()) // 2
        y = parent_geometry.y() + (parent_geometry.height() - self_geometry.height()) // 2
        self.move(x, y)

def export_file(main_window):
    """Export graph to file."""
    dialog = ExportDialog(main_window)
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        export_type = dialog.export_type_dropdown.currentText()
        file_path = dialog.path_edit.text()

        if export_type == "GML":
            asyncio.create_task(export_graph_to_gml(main_window, file_path))

async def export_graph_to_gml(main_window, file_path):
    """Export the graph to a GML file using the ticket system."""
    try:
        # Get the current graph from the main window
        graph = await main_window.get_graph()
        
        if not graph:
            QtWidgets.QMessageBox.critical(main_window, "Export Failed", "No graph available to export")
            return
            
        # Use ticket system to export the graph
        success, content, error = await main_window.communication.request_and_get_response(
            operation="export_graph_to_gml",
            params={"file_path": file_path},
            sender="Frontend"
        )
        
        if success and content.get("result"):
            logging.info(f"Graph exported to GML file: {file_path}")
            QtWidgets.QMessageBox.information(main_window, "Export Successful", f"Graph exported to GML file: {file_path}")
        else:
            logging.error(f"Error exporting graph to GML file: {error or 'Unknown error'}")
            QtWidgets.QMessageBox.critical(main_window, "Export Failed", f"Error exporting graph to GML file: {error or 'Unknown error'}")
    except Exception as e:
        logging.error(f"Error exporting graph to GML file: {e}")
        QtWidgets.QMessageBox.critical(main_window, "Export Failed", f"Error exporting graph to GML file: {e}")
