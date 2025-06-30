from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QAbstractItemModel, QModelIndex
import qasync
import sys
import os
import asyncio
import json
import pickle
import base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ResearchGuidePackage.FrontendModule.client import APIClient
import functools
import logging

communication = APIClient()

logger = logging.getLogger(__name__)

class JsonModel(QAbstractItemModel):
    """Model to display JSON data in a QTreeView."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.json_data = {}

    def setJsonData(self, data):
        self.beginResetModel()
        self.json_data = data
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self.json_data)
        return 0

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            key = list(self.json_data.keys())[index.row()]
            if index.column() == 0:
                return key
            elif index.column() == 1:
                return str(self.json_data[key])
        return None

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def headerData(self, section, orientation, role):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return "Parameter" if section == 0 else "Value"
        return None

class ConsoleWindow(QtWidgets.QWidget):
    """Separate console window for sending arbitrary tickets."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.operations = {}  # Store available operations
        self.setup_ui()
        asyncio.create_task(self.list_available_operations())  # Load operations on startup

    def setup_ui(self):
        self.setWindowTitle("Console")
        main_layout = QtWidgets.QHBoxLayout()  # Change to horizontal layout
        
        # Left side layout (operation controls)
        left_layout = QtWidgets.QVBoxLayout()
        
        self.operation_combo = QtWidgets.QComboBox()
        self.operation_combo.addItem("Select Operation")
        self.operation_combo.currentIndexChanged.connect(self.operation_selected)

        self.params_table = QtWidgets.QTableWidget()
        self.params_table.setColumnCount(2)
        header = self.params_table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.params_table.setHorizontalHeaderLabels(["Parameter", "Value"])

        self.send_button = QtWidgets.QPushButton("Send Ticket")
        
        self.json_tree = QtWidgets.QTreeView()
        self.json_model = JsonModel()
        self.json_tree.setModel(self.json_model)
        self.json_tree.setHeaderHidden(False)

        left_layout.addWidget(self.operation_combo)
        left_layout.addWidget(self.params_table)
        left_layout.addWidget(self.send_button)
        left_layout.addWidget(self.json_tree)

        # Right side layout (response display)
        right_layout = QtWidgets.QVBoxLayout()
        
        # Add status labels at the top of right side
        status_layout = QtWidgets.QVBoxLayout()
        self.sent_label = QtWidgets.QLabel("Ticket Sent: -")
        self.received_label = QtWidgets.QLabel("Ticket Received: -")
        status_layout.addWidget(self.sent_label)
        status_layout.addWidget(self.received_label)
        
        self.response_label = QtWidgets.QLabel("Response:")
        self.response_text = QtWidgets.QTextEdit()
        self.response_text.setReadOnly(True)
        self.additional_json_tree = QtWidgets.QTreeView()
        self.additional_json_model = JsonModel()
        self.additional_json_tree.setModel(self.additional_json_model)
        self.additional_json_tree.setHeaderHidden(False)

        right_layout.addLayout(status_layout)
        right_layout.addWidget(self.response_label)
        right_layout.addWidget(self.response_text)
        right_layout.addWidget(self.additional_json_tree)

        # Add left and right layouts to main layout
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_layout)
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_layout)

        # Set a minimum width for both sides
        left_widget.setMinimumWidth(300)
        right_widget.setMinimumWidth(300)

        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)

        self.setLayout(main_layout)
        self.send_button.clicked.connect(lambda: asyncio.create_task(self.send_ticket()))
        
        # Set a reasonable initial size for the window
        self.resize(800, 600)

    def operation_selected(self, index):
        """Populates the parameter table when an operation is selected."""
        if index == 0:  # "Select Operation" is selected
            self.params_table.setRowCount(0)
            self.json_model.setJsonData({})
            self.json_tree.expandAll()
            return

        operation_name = self.operation_combo.currentText()
        operation_data = self.operations.get(operation_name, {})
        
        # Debug print
        print(f"Operation data for {operation_name}:", operation_data)
        
        # Get all available parameter names and types from operation data
        if operation_data:
            param_names = operation_data.get("params", [])
            param_types = operation_data.get("types", [])
        else:
            param_names = []
            param_types = []
        
        # Debug print
        print(f"Parameters: {param_names}")
        print(f"Types: {param_types}")

        if param_names and param_types:
            self.params_table.setRowCount(len(param_names))
            for row, (param, typ) in enumerate(zip(param_names, param_types)):
                # Set parameter name
                param_item = QtWidgets.QTableWidgetItem(param)
                param_item.setFlags(param_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.params_table.setItem(row, 0, param_item)

                # Create editable value cell with type info
                value_item = QtWidgets.QTableWidgetItem("")
                value_item.setData(QtCore.Qt.ItemDataRole.UserRole, typ)
                self.params_table.setItem(row, 1, value_item)

            # Debug print
            print(f"Table rows set: {self.params_table.rowCount()}")
        else:
            self.params_table.setRowCount(0)

        # Show JSON data for the selected operation
        self.json_model.setJsonData(operation_data)
        self.json_tree.expandAll()

    async def list_available_operations(self):
        """Lists available operations and populates the dropdown."""
        try:
            success, response_content, error = await communication.request_and_get_response(
                operation="list_operations",
                params={},
                sender="FrontendConsole"
            )
            
            if success and response_content:
                logger.debug(f"Response content: {response_content}")  # Log the response content
                self.operations = {}
                for op_name, op_data in response_content.get("result", {}).items():
                    self.operations[op_data["operation"]] = op_data  # Store by operation name
                self.json_model.setJsonData(self.operations)  # Display operations in JSON viewer
                self.json_tree.expandAll()
                if self.operations:
                    self.operation_combo.clear()
                    self.operation_combo.addItem("Select Operation")
                    for op_name in self.operations.keys():
                        self.operation_combo.addItem(op_name)
                else:
                    self.operation_combo.addItem("No operations found")
            else:
                self.operation_combo.addItem("No response received")

        except Exception as e:
            logger.error(f"Error listing operations: {e}", exc_info=True)
            self.operation_combo.addItem(f"Error: {e}")

    async def send_ticket(self):
        """Sends a ticket to the backend with the specified operation and parameters."""
        operation = self.operation_combo.currentText()
        if operation == "Select Operation":
            self.response_label.setText("Please select a valid operation")
            return

        # Get parameters from the table
        params = {}
        operation_data = self.operations.get(operation, {})
        param_names = operation_data.get("params", [])

        for row, param_name in enumerate(param_names):
            value_item = self.params_table.item(row, 1)
            if value_item:
                param_value = value_item.text()
                param_type = operation_data["types"][row]

                try:
                    if param_value:  # Only attempt conversion if a value is entered
                        if param_type == "str":
                            param_value = str(param_value)
                        elif param_type == "int":
                            param_value = int(param_value)
                        elif param_type == "float":
                            param_value = float(param_value)
                        elif param_type == "bool":
                            if param_value.lower() == "true":
                                param_value = True
                            elif param_value.lower() == "false":
                                param_value = False
                            else:
                                raise ValueError("Invalid boolean value. Must be 'true' or 'false'.")
                        else:
                            raise ValueError(f"Unsupported type: {param_type}")
                        params[param_name] = param_value
                except ValueError as ve:
                    self.response_label.setText(f"Invalid value for parameter {param_name}. Expected type: {param_type}. Error: {ve}")
                    return

        try:
            success, content, error = await communication.request_and_get_response(
                operation=operation,
                params=params,
                sender="FrontendConsole"
            )
            
            if success:
                self.received_label.setText(f"Ticket Received: Success")
                self.additional_json_model.setJsonData(content)
                self.additional_json_tree.expandAll()
                self.response_text.setPlainText(json.dumps(content, indent=4))

                # Check if we need to update the graph
                if content.get("update_page", False):
                    await self.main_window.show_graph()
            else:
                self.received_label.setText(f"Ticket Received: Error - {error}")
                self.additional_json_model.setJsonData({"error": error})
                self.additional_json_tree.expandAll()
                self.response_text.setPlainText(f"Error: {error}")

        except Exception as e:
            logger.error(f"Error sending ticket: {e}", exc_info=True)
            self.sent_label.setText("Ticket Sent: Error")
            self.received_label.setText("Ticket Received: Error")
            self.additional_json_model.setJsonData({"error": str(e)})
            self.additional_json_tree.expandAll()
            self.response_text.setPlainText(f"Error: {e}")

class Tools:
    def __init__(self, main_window):
        self.main_window = main_window
        self.console = None

    def show_console(self):
        """Show console window."""
        if not self.console:
            self.console = ConsoleWindow(self.main_window)
        # Center the console window on screen
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        console_geometry = self.console.geometry()
        x = (screen.width() - console_geometry.width()) // 2
        y = (screen.height() - console_geometry.height()) // 2
        self.console.move(x, y)
        self.console.show()
