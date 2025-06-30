from PyQt6 import QtWidgets
import logging
import uuid
# Import NodeDialog from its new location (instead of EditNodeDialog)

# AddNodeDialog has been removed as it's been replaced by NodeDialog's "create" mode

class AddEdgeDialog(QtWidgets.QDialog):
    """Dialog for adding a new edge."""
    def __init__(self, parent=None, node_labels=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Edge")
        self.node_labels = node_labels or {}  # Use node labels

        # Create widgets
        self.node1_label = QtWidgets.QLabel("Node 1:")
        self.node1_combo = QtWidgets.QComboBox()
        self.node1_combo.addItems(list(self.node_labels.values()))  # Use labels

        self.node2_label = QtWidgets.QLabel("Node 2:")
        self.node2_combo = QtWidgets.QComboBox()
        self.node2_combo.addItems(list(self.node_labels.values()))  # Use labels

        self.weight_label = QtWidgets.QLabel("Weight:")
        self.weight_spinbox = QtWidgets.QDoubleSpinBox()
        self.weight_spinbox.setRange(0.0, 1.0)
        self.weight_spinbox.setSingleStep(0.1)
        self.weight_spinbox.setValue(1.0)  # Set default value to 1

        self.type_label = QtWidgets.QLabel("Type:")
        self.type_edit = QtWidgets.QLineEdit()

        self.color_label = QtWidgets.QLabel("Color:")
        self.color_edit = QtWidgets.QLineEdit()

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Create layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.node1_label)
        layout.addWidget(self.node1_combo)
        layout.addWidget(self.node2_label)
        layout.addWidget(self.node2_combo)
        layout.addWidget(self.weight_label)
        layout.addWidget(self.weight_spinbox)
        layout.addWidget(self.type_label)
        layout.addWidget(self.type_edit)
        layout.addWidget(self.color_label)
        layout.addWidget(self.color_edit)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def get_values(self):
        """Get values from the dialog."""
        node1 = self.node1_combo.currentText()  # Get label
        node2 = self.node2_combo.currentText()  # Get label
        weight = self.weight_spinbox.value()
        edge_type = self.type_edit.text()
        color = self.color_edit.text()
        return node1, node2, weight, edge_type, color

class DeleteNodeDialog(QtWidgets.QDialog):
    """Dialog for deleting a node."""
    def __init__(self, parent=None, node_labels=None):
        super().__init__(parent)
        self.setWindowTitle("Delete Node")
        self.node_labels = node_labels or {}

        # Create widgets
        self.node_label = QtWidgets.QLabel("Node to delete:")
        self.node_combo = QtWidgets.QComboBox()
        self.node_combo.addItems(list(self.node_labels.values()))

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Create layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.node_label)
        layout.addWidget(self.node_combo)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def get_selected_node(self):
        """Get the selected node label."""
        return self.node_combo.currentText()

class DeleteEdgeDialog(QtWidgets.QDialog):
    """Dialog for deleting an edge."""
    def __init__(self, parent=None, edge_labels=None):
        super().__init__(parent)
        self.setWindowTitle("Delete Edge")
        self.edge_labels = edge_labels or []

        # Create widgets
        self.edge_label = QtWidgets.QLabel("Edge to delete:")
        self.edge_combo = QtWidgets.QComboBox()
        self.edge_combo.addItems(self.edge_labels)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Create layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.edge_label)
        layout.addWidget(self.edge_combo)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def get_selected_edge(self):
        """Get the selected edge label."""
        return self.edge_combo.currentText()

class EditEdgeDialog(QtWidgets.QDialog):
    """Dialog for editing an existing edge."""
    def __init__(self, parent=None, edge_labels=None, current_weight=None, current_type=None, node_labels=None, current_edge_label=None, current_color=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Edge")
        self.edge_labels = edge_labels or []
        self.node_labels = node_labels or {}  # Store node labels
        self.current_edge_label = current_edge_label
        self.current_node1_label = None
        self.current_node2_label = None
        self.current_color = current_color

        if current_edge_label:
            node1_label, node2_label = current_edge_label[1:-1].split(", ")
            self.current_node1_label = node1_label
            self.current_node2_label = node2_label

        # Create widgets
        self.edge_label = QtWidgets.QLabel("Edge to edit:")
        self.edge_combo = QtWidgets.QComboBox()
        self.edge_combo.addItems(self.edge_labels)
        if current_edge_label:
            self.edge_combo.setCurrentText(current_edge_label)
        self.edge_combo.currentIndexChanged.connect(self.update_node_selection)

        self.node1_label = QtWidgets.QLabel("New Node 1:")
        self.node1_combo = QtWidgets.QComboBox()
        self.node1_combo.addItems(list(self.node_labels.values()))  # Use labels
        if self.current_node1_label:
            self.node1_combo.setCurrentText(self.current_node1_label)

        self.node2_label = QtWidgets.QLabel("New Node 2:")
        self.node2_combo = QtWidgets.QComboBox()
        self.node2_combo.addItems(list(self.node_labels.values()))  # Use labels
        if self.current_node2_label:
            self.node2_combo.setCurrentText(self.current_node2_label)

        self.weight_label = QtWidgets.QLabel("Weight:")
        self.weight_spinbox = QtWidgets.QDoubleSpinBox()
        self.weight_spinbox.setRange(0.0, 1.0)
        self.weight_spinbox.setSingleStep(0.1)
        self.weight_spinbox.setValue(current_weight or 1.0)

        self.type_label = QtWidgets.QLabel("Type:")
        self.type_edit = QtWidgets.QLineEdit(current_type or "")

        self.color_label = QtWidgets.QLabel("Color:")
        self.color_edit = QtWidgets.QLineEdit(self.current_color or "")

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Create layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.edge_label)
        layout.addWidget(self.edge_combo)
        layout.addWidget(self.node1_label)
        layout.addWidget(self.node1_combo)
        layout.addWidget(self.node2_label)
        layout.addWidget(self.node2_combo)
        layout.addWidget(self.weight_label)
        layout.addWidget(self.weight_spinbox)
        layout.addWidget(self.type_label)
        layout.addWidget(self.type_edit)
        layout.addWidget(self.color_label)
        layout.addWidget(self.color_edit)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def get_values(self):
        """Get values from the dialog."""
        selected_edge_label = self.edge_combo.currentText()
        node1 = self.node1_combo.currentText()  # Get label for new node 1
        node2 = self.node2_combo.currentText()  # Get label for new node 2
        weight = self.weight_spinbox.value()
        edge_type = self.type_edit.text()
        color = self.color_edit.text()
        return selected_edge_label, node1, node2, weight, edge_type, color

    def update_node_selection(self, index):
        """Update node selection based on selected edge."""
        selected_edge_label = self.edge_combo.itemText(index)
        if selected_edge_label:
            node1_label, node2_label = selected_edge_label[1:-1].split(", ")
            self.node1_combo.setCurrentText(node1_label)
            self.node2_combo.setCurrentText(node2_label)

class SelectNodeDialog(QtWidgets.QDialog):
    """Dialog for selecting a node from a dropdown."""
    
    def __init__(self, parent=None, node_labels=None, title="Select Node"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(300, 150)
        
        self.node_labels = node_labels or {}
        
        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Node selection dropdown
        layout.addWidget(QtWidgets.QLabel("Select a node:"))
        self.node_dropdown = QtWidgets.QComboBox(self)
        
        # Add node labels to dropdown
        for node_id, label in self.node_labels.items():
            self.node_dropdown.addItem(label, node_id)
            
        layout.addWidget(self.node_dropdown)
        
        # Add buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Disable OK button if no nodes are available
        if self.node_dropdown.count() == 0:
            button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            layout.addWidget(QtWidgets.QLabel("No nodes available."))
    
    def get_selected_node_id(self):
        """Get the ID of the selected node."""
        return self.node_dropdown.currentData()
    
    def get_selected_node_label(self):
        """Get the label of the selected node."""
        return self.node_dropdown.currentText()
