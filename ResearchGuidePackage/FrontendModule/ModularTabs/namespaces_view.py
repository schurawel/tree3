import logging
import asyncio
import os
from typing import Dict, List, Set
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, pyqtSignal
from collections import defaultdict
from ResearchGuidePackage.FrontendModule.client import APIClient
from ResearchGuidePackage.FrontendModule.link_handler import show_node_info
from ResearchGuidePackage.FrontendModule.ModularTabs.NodeEditor.dialog_operations import edit_node_by_uuid
from ResearchGuidePackage.FrontendModule.zettelkasten_index_calculator import ZettelkastenIndexCalculator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('NamespacesView')

class NamespaceTreeNode:
    """Represents a node in the namespace tree structure."""
    def __init__(self, name):
        self.name = name
        self.children = {}  # Map of name -> NamespaceTreeNode
        self.node_ids = []  # List of node IDs associated with this namespace
        self.representative_node = None  # Node ID that represents this folder (when name matches namespace)

class CheckableComboBox(QtWidgets.QComboBox):
    """Simple combo box with checkable items."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setView(QtWidgets.QListView())
        self.view().pressed.connect(self._handle_item_pressed)
        self.setModel(QtGui.QStandardItemModel())
        self.model().itemChanged.connect(self._update_text)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Select node types...")
        
    def _handle_item_pressed(self, index):
        """Toggle item check state when an item is clicked."""
        item = self.model().itemFromIndex(index)
        if item.isCheckable():
            item.setCheckState(
                Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
            )
    
    def add_item(self, text, checked=False):
        """Add a checkable item to the combo box."""
        item = QtGui.QStandardItem(text)
        item.setCheckable(True)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.model().appendRow(item)
        self._update_text()
    
    def get_checked_items(self):
        """Get list of checked item texts."""
        checked = []
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(item.text())
        return checked
    
    def set_check_state(self, text, checked):
        """Set check state for an item with the given text."""
        for i in range(self.model().rowCount()):
            item = self.model().item(i)
            if item.text() == text:
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                break
    
    def _update_text(self):
        """Update combo box display text to show checked items."""
        checked = self.get_checked_items()
        if not checked:
            self.lineEdit().setText("No types selected")
        elif len(checked) <= 2:
            self.lineEdit().setText(", ".join(checked))
        else:
            self.lineEdit().setText(f"{len(checked)} types selected")

class NamespacesView(QtWidgets.QWidget):
    """Widget that displays all namespaces found in the graph."""
    
    refresh_completed = pyqtSignal()
    
    def __init__(self, main_window):
        """Initialize the namespaces view widget."""
        super().__init__()
        self.main_window = main_window
        self.namespace_tree = NamespaceTreeNode("root")  # Root of the namespace tree
        self.communication = APIClient()
        
        # Add a flag and timer to properly handle single and double clicks
        self.is_double_click = False
        self.click_timer = QtCore.QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.process_single_click)
        self.clicked_item = None
        self.clicked_column = None
        
        self.init_ui()
        
        # Initial refresh
        self.refresh_async()
        
    def init_ui(self):
        """Initialize the user interface components."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Top controls - filter, navigation, and node type filter combined in one row
        top_layout = QtWidgets.QHBoxLayout()
        
        # Left side: Refresh button and namespace filter
        filter_layout = QtWidgets.QHBoxLayout()
        
        # Add refresh button - now styled green with black refresh arrow
        refresh_button = QtWidgets.QPushButton("↻")  # Black cycle arrow character ↻
        refresh_button.setToolTip("Refresh namespaces")
        refresh_button.clicked.connect(self.refresh_async)
        refresh_button.setFixedWidth(30)
        refresh_button.setFixedHeight(30)  # Make it square
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;  /* Green */
                color: white;  /* Black arrow */
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #45a049;  /* Darker green on hover */
            }
            QPushButton:pressed {
                background-color: #3d8b40;  /* Even darker when pressed */
            }
        """)
        filter_layout.addWidget(refresh_button)
        
        # Filter field - limit width
        self.namespace_filter = QtWidgets.QLineEdit()
        self.namespace_filter.setPlaceholderText("Filter namespaces...")
        self.namespace_filter.textChanged.connect(self.filter_namespaces)
        self.namespace_filter.setFixedWidth(200)  # Limit width of search bar
        filter_layout.addWidget(self.namespace_filter)
        
        # Add expand/collapse buttons
        expand_button = QtWidgets.QPushButton("Expand All")
        expand_button.clicked.connect(self.expand_all)
        expand_button.setToolTip("Expand all namespace folders")
        
        collapse_button = QtWidgets.QPushButton("Collapse All")
        collapse_button.clicked.connect(self.collapse_all)
        collapse_button.setToolTip("Collapse all namespace folders")
        
        filter_layout.addWidget(expand_button)
        filter_layout.addWidget(collapse_button)
        
        # Add the filter layout to the top layout - no stretch factor to keep left-bound
        top_layout.addLayout(filter_layout)
        
        # Add spacing between sections
        top_layout.addSpacing(10)  # Reduced spacing
        
        # Right side: node type filtering
        type_filter_layout = QtWidgets.QHBoxLayout()
        type_filter_layout.addWidget(QtWidgets.QLabel("Types:"))  # Shorter label
        
        # Create a checkable dropdown for node types
        self.type_dropdown = CheckableComboBox(self)
        self.type_dropdown.setFixedWidth(150)  # Limit width
        self.node_types = ['document', 'person', 'concept', 'task', 'page', 'file', 'text_block']
        
        # Populate the dropdown with checkable items
        for node_type in self.node_types:
            self.type_dropdown.add_item(node_type.capitalize(), checked=True)
        
        type_filter_layout.addWidget(self.type_dropdown)
        
        # Add select all / none buttons
        select_all_button = QtWidgets.QPushButton("All")
        select_all_button.clicked.connect(self.select_all_types)
        select_all_button.setToolTip("Select all node types")
        
        select_none_button = QtWidgets.QPushButton("None")
        select_none_button.clicked.connect(self.select_no_types)
        select_none_button.setToolTip("Deselect all node types")
        
        # Add a button to apply the filter
        apply_filter_button = QtWidgets.QPushButton("Apply")
        apply_filter_button.clicked.connect(self.filter_by_types)
        apply_filter_button.setToolTip("Apply type filter")
        
        type_filter_layout.addWidget(select_all_button)
        type_filter_layout.addWidget(select_none_button)
        type_filter_layout.addWidget(apply_filter_button)
        
        # Add the type filter layout to the top layout - no stretch factor
        top_layout.addLayout(type_filter_layout)
        
        # Add stretch at the end to push everything to the left
        top_layout.addStretch(1)
        
        layout.addLayout(top_layout)

        # Create a more compact view mode selection
        view_mode_layout = QtWidgets.QHBoxLayout()
        view_mode_layout.setContentsMargins(4, 4, 4, 4)
        view_mode_layout.setSpacing(8)
        
        # Create view mode label and dropdown
        view_mode_layout.addWidget(QtWidgets.QLabel("View:"), 0)
        
        self.view_mode_combo = QtWidgets.QComboBox()
        self.view_mode_combo.addItem("Standard Namespaces")
        self.view_mode_combo.addItem("Zettelkasten Index")
        self.view_mode_combo.setCurrentIndex(0)  # Default to standard namespaces
        self.view_mode_combo.currentIndexChanged.connect(self.on_view_mode_combo_changed)
        self.view_mode_combo.setToolTip("Switch between namespace styles")
        self.view_mode_combo.setFixedWidth(150)  # Limit width
        view_mode_layout.addWidget(self.view_mode_combo, 0)  # No stretch
        
        # Add jitter control for Zettelkasten mode - more compact
        jitter_container = QtWidgets.QWidget()
        jitter_layout = QtWidgets.QHBoxLayout(jitter_container)
        jitter_layout.setContentsMargins(0, 0, 0, 0)
        jitter_layout.setSpacing(4)
        
        self.jitter_label = QtWidgets.QLabel("Randomness:")
        jitter_layout.addWidget(self.jitter_label)
        
        self.jitter_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.jitter_slider.setMinimum(0)
        self.jitter_slider.setMaximum(100)
        self.jitter_slider.setValue(30)  # Default 0.3
        self.jitter_slider.setToolTip("Adjust randomness of Zettelkasten structure")
        self.jitter_slider.valueChanged.connect(self.on_jitter_changed)
        self.jitter_slider.setFixedWidth(80)  # Make slider smaller
        jitter_layout.addWidget(self.jitter_slider)
        
        self.jitter_value_label = QtWidgets.QLabel("0.30")
        self.jitter_value_label.setFixedWidth(30)
        jitter_layout.addWidget(self.jitter_value_label)
        
        view_mode_layout.addWidget(jitter_container, 0)  # No stretch
        
        # Add stretch to push everything to the left
        view_mode_layout.addStretch(1)
        
        # Initially disable jitter controls
        jitter_container.setEnabled(False)
        self.jitter_container = jitter_container  # Store reference for enabling/disabling
        
        # Add the view mode layout to the main layout
        layout.addLayout(view_mode_layout)
        
        # Namespace focus controls - modified for left alignment
        focus_group = QtWidgets.QGroupBox("Namespace Focus")
        focus_layout = QtWidgets.QHBoxLayout(focus_group)
        focus_layout.setContentsMargins(10, 10, 10, 10)  # Add some padding
        focus_layout.setSpacing(10)  # Consistent spacing
        
        # Left side: dropdown and add button
        self.focus_combo = QtWidgets.QComboBox()
        self.focus_combo.setPlaceholderText("Select namespace")
        self.focus_combo.setMinimumWidth(150)  # Ensure minimum width
        self.focus_combo.setMaximumWidth(200)  # Limit maximum width
        focus_layout.addWidget(self.focus_combo, 0)  # No stretch factor to keep natural width
        
        # Add button to add selected namespace to multi-select
        add_to_focus_button = QtWidgets.QPushButton("Add")
        add_to_focus_button.setToolTip("Add selected namespace to focus")
        add_to_focus_button.clicked.connect(self.add_selected_to_focus)
        focus_layout.addWidget(add_to_focus_button, 0)  # No stretch
        
        # Multi-select line edit for multiple namespaces
        self.focus_multi_edit = QtWidgets.QLineEdit()
        self.focus_multi_edit.setPlaceholderText("Multiple namespaces (comma-separated)")
        self.focus_multi_edit.setMinimumWidth(200)
        self.focus_multi_edit.setMaximumWidth(400)  # Limit maximum width
        focus_layout.addWidget(self.focus_multi_edit, 0)  # No stretch - changed from 1 to keep fixed width
        
        # Action buttons
        self.apply_focus_button = QtWidgets.QPushButton("Apply Focus")
        self.apply_focus_button.clicked.connect(self.apply_focus)
        focus_layout.addWidget(self.apply_focus_button, 0)  # No stretch
        
        self.clear_focus_button = QtWidgets.QPushButton("Clear Focus")
        self.clear_focus_button.clicked.connect(self.clear_focus)
        focus_layout.addWidget(self.clear_focus_button, 0)  # No stretch
        
        # Add stretch to push everything to the left
        focus_layout.addStretch(1)
        
        layout.addWidget(focus_group)
        
        # Namespaces tree widget - with single column
        self.tree_widget = QtWidgets.QTreeWidget()
        self.tree_widget.setHeaderLabels(["Namespace"])  # Single column header
        self.tree_widget.setColumnWidth(0, 380)  # Make column wider to accommodate counts in text
        self.tree_widget.setAlternatingRowColors(True)
        layout.addWidget(self.tree_widget, 1)  # 1 = stretch factor for tree
        
        # Set up context menu
        self.tree_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        # Set up click handling with a different approach
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Add Transfer Namespaces section
        self.setup_transfer_namespaces_section(layout)
        
        # Status bar with Zettelkasten notation info
        self.status_container = QtWidgets.QWidget()
        status_layout = QtWidgets.QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 4, 0, 0)
        
        self.status_label = QtWidgets.QLabel("Ready")
        status_layout.addWidget(self.status_label, 1)  # stretch
        
        # Add a notation indicator that's visible only in Zettelkasten mode
        self.notation_indicator = QtWidgets.QLabel("Index format: Number.Subnumber (e.g., 1.2.3)")
        self.notation_indicator.setStyleSheet("color: #666; font-style: italic;")
        self.notation_indicator.setVisible(False)  # Initially hidden
        status_layout.addWidget(self.notation_indicator, 0)  # no stretch
        
        layout.addWidget(self.status_container)
        
        # Initialize member variables for filtering
        self.focused_namespaces = set()
        self.current_filter_text = ""
        self.current_view_mode = "namespaces"  # Default to standard namespaces
        self.jitter_value = 0.3  # Default jitter value
        self.zettelkasten_indexer = ZettelkastenIndexCalculator(randomness_factor=self.jitter_value)
        
        # Set icons and other properties (existing code)
        self.folder_icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirClosedIcon)
        self.file_icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
        
        # Node type specific icons
        self.node_type_icons = {
            'document': self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon),
            'person': self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon),
            'concept': self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation),
            'task': self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_BrowserReload),
            'page': self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView),
            'file': self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileLinkIcon),
            'text_block': self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView)
        }
        
        # Default icon for unknown types
        self.default_icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
        
        self.refresh_completed.connect(self.update_status_label)
        
    def setup_transfer_namespaces_section(self, layout):
        """Set up the Transfer Namespaces section with two list panels."""
        # Create a group box for transfer section
        transfer_group = QtWidgets.QGroupBox("Transfer Namespaces")
        transfer_layout = QtWidgets.QHBoxLayout(transfer_group)
        
        # Create two sides: source and target
        self.source_panel = self.create_namespace_panel("Source Namespace:")
        self.target_panel = self.create_namespace_panel("Target Namespace:")
        
        # Add transfer button between panels
        transfer_buttons_layout = QtWidgets.QVBoxLayout()
        
        transfer_right_button = QtWidgets.QPushButton("→")
        transfer_right_button.setToolTip("Transfer selected nodes to target namespace")
        transfer_right_button.clicked.connect(self.transfer_nodes_to_target)
        transfer_right_button.setFixedWidth(40)
        
        transfer_left_button = QtWidgets.QPushButton("←")
        transfer_left_button.setToolTip("Transfer selected nodes to source namespace")
        transfer_left_button.clicked.connect(self.transfer_nodes_to_source)
        transfer_left_button.setFixedWidth(40)
        
        transfer_buttons_layout.addStretch(1)
        transfer_buttons_layout.addWidget(transfer_right_button)
        transfer_buttons_layout.addWidget(transfer_left_button)
        transfer_buttons_layout.addStretch(1)
        
        # Add panels and buttons to layout
        transfer_layout.addWidget(self.source_panel, 1)
        transfer_layout.addLayout(transfer_buttons_layout)
        transfer_layout.addWidget(self.target_panel, 1)
        
        # Add to main layout with small stretch factor
        layout.addWidget(transfer_group, 0)

    def create_namespace_panel(self, title):
        """Create a panel with namespace input and node list."""
        panel = QtWidgets.QWidget()
        panel_layout = QtWidgets.QVBoxLayout(panel)
        
        # Add label and line edit for namespace input
        panel_layout.addWidget(QtWidgets.QLabel(title))
        namespace_input = QtWidgets.QLineEdit()
        namespace_input.setPlaceholderText("Type namespace...")
        panel_layout.addWidget(namespace_input)
        
        # Add list widget for showing nodes
        node_list = QtWidgets.QListWidget()
        node_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        node_list.setMinimumHeight(150)  # Set minimum height for the list
        panel_layout.addWidget(node_list)
        
        # Node ID input section
        node_id_layout = QtWidgets.QHBoxLayout()
        node_id_input = QtWidgets.QLineEdit()
        node_id_input.setPlaceholderText("Paste node ID(s)...")
        node_id_layout.addWidget(node_id_input)
        
        add_id_button = QtWidgets.QPushButton("Add ID")
        add_id_button.setToolTip("Add node by ID")
        add_id_button.clicked.connect(lambda: self.add_node_by_id(panel))
        node_id_layout.addWidget(add_id_button)
        
        panel_layout.addLayout(node_id_layout)
        
        # Add buttons for operations
        buttons_layout = QtWidgets.QHBoxLayout()
        
        transfer_all_button = QtWidgets.QPushButton("Transfer All")
        transfer_all_button.setToolTip("Transfer all nodes (not just selected)")
        transfer_all_button.clicked.connect(lambda: self.transfer_all_nodes(panel))
        buttons_layout.addWidget(transfer_all_button)
        
        remove_button = QtWidgets.QPushButton("Remove")
        remove_button.setToolTip("Remove selected nodes from list")
        remove_button.clicked.connect(lambda: self.remove_selected_nodes(panel))
        buttons_layout.addWidget(remove_button)
        
        panel_layout.addLayout(buttons_layout)
        
        # Add node count label
        node_count_label = QtWidgets.QLabel("0 nodes")
        panel_layout.addWidget(node_count_label)
        
        # Store the widgets as properties of the panel for easy access
        panel.namespace_input = namespace_input
        panel.node_list = node_list
        panel.node_count_label = node_count_label
        panel.node_id_input = node_id_input
        
        # Connect the input signal to update the list
        namespace_input.textChanged.connect(lambda text, p=panel: self.update_namespace_node_list(text, p))
        
        return panel

    def add_node_by_id(self, panel):
        """Add node(s) to the panel by ID and update its namespaces attribute."""
        try:
            # Get the input text and split by commas, spaces, or newlines
            input_text = panel.node_id_input.text().strip()
            if not input_text:
                return
            
            # Get the panel's namespace
            panel_namespace = panel.namespace_input.text().strip()
            if not panel_namespace:
                self.status_label.setText("Please specify a namespace for this panel first")
                return
            
            # Split by common separators
            import re
            node_ids = re.split(r'[,\s\n]+', input_text)
            node_ids = [id.strip() for id in node_ids if id.strip()]
            
            if not node_ids:
                return
            
            # Add each valid node ID to the list
            added_count = 0
            for node_id in node_ids:
                try:
                    # Validate UUID format
                    import uuid
                    uuid_obj = uuid.UUID(node_id)
                    node_id = str(uuid_obj)  # Normalize format
                    
                    # Check if node already exists in list
                    existing = False
                    for i in range(panel.node_list.count()):
                        item = panel.node_list.item(i)
                        if item.data(Qt.ItemDataRole.UserRole) == node_id:
                            existing = True
                            break
                        
                    if existing:
                        continue
                    
                    # Get node data
                    node_data = self.get_node_data(node_id)
                    node_name = node_data.get('name') or node_data.get('title', '')
                    node_type = node_data.get('node_type', '')
                    
                    # Create list item
                    item = QtWidgets.QListWidgetItem()
                    display_text = f"{node_name} ({node_id})" if node_name else node_id
                    item.setText(display_text)
                    
                    # Set icon based on node type
                    if node_type and node_type in self.node_type_icons:
                        item.setIcon(self.node_type_icons[node_type])
                    else:
                        item.setIcon(self.default_icon)
                        
                    # Store node ID in item data
                    item.setData(Qt.ItemDataRole.UserRole, node_id)
                    
                    # Add to list
                    panel.node_list.addItem(item)
                    added_count += 1
                    
                    # Update the node's namespaces attribute in the backend
                    asyncio.create_task(self._update_node_namespace(node_id, panel_namespace, add=True))
                    
                except ValueError:
                    self.status_label.setText(f"Invalid node ID format: {node_id}")
                except Exception as e:
                    logger.error(f"Error adding node by ID: {e}")
        
        except Exception as e:
            logger.error(f"Error in add_node_by_id: {e}")
            self.status_label.setText(f"Error adding node by ID: {str(e)}")

    def transfer_all_nodes(self, source_panel):
        """Transfer all nodes in the panel, not just selected ones."""
        try:
            # Determine if this is the source or target panel
            if source_panel == self.source_panel:
                target_panel = self.target_panel
            else:
                target_panel = self.source_panel
                
            # Get namespaces
            source_namespace = source_panel.namespace_input.text().strip()
            target_namespace = target_panel.namespace_input.text().strip()
            
            if not target_namespace:
                self.status_label.setText("Target namespace is empty")
                return
                
            # Collect all node IDs from the list
            node_ids = []
            for i in range(source_panel.node_list.count()):
                item = source_panel.node_list.item(i)
                node_id = item.data(Qt.ItemDataRole.UserRole)
                if node_id:
                    node_ids.append(node_id)
            
            if not node_ids:
                self.status_label.setText("No nodes in list to transfer")
                return
                
            # Transfer all nodes
            asyncio.create_task(self._async_transfer_nodes(node_ids, source_namespace, target_namespace))
            
        except Exception as e:
            logger.error(f"Error in transfer_all_nodes: {e}")
            self.status_label.setText(f"Error transferring all nodes: {str(e)}")

    def remove_selected_nodes(self, panel):
        """Remove selected nodes from the list and update their namespaces attribute."""
        try:
            # Get selected items
            selected_items = panel.node_list.selectedItems()
            if not selected_items:
                return
            
            # Get panel namespace
            panel_namespace = panel.namespace_input.text().strip()
            if not panel_namespace:
                self.status_label.setText("No namespace specified for this panel")
                return
            
            # Remove items in reverse order to avoid index problems
            removed_count = 0
            for item in reversed(selected_items):
                node_id = item.data(Qt.ItemDataRole.UserRole)
                row = panel.node_list.row(item)
                panel.node_list.takeItem(row)
                removed_count += 1
                
                # Update the node's namespaces attribute in the backend - remove this namespace
                if node_id:
                    asyncio.create_task(self._update_node_namespace(node_id, panel_namespace, add=False))
            
            # Update count label
            panel.node_count_label.setText(f"{panel.node_list.count()} nodes")
            
            if removed_count > 0:
                self.status_label.setText(f"Removed {removed_count} nodes from list and updated namespaces")
                
        except Exception as e:
            logger.error(f"Error removing nodes: {e}")
            self.status_label.setText(f"Error removing nodes: {str(e)}")

    async def _update_node_namespace(self, node_id, namespace, add=True):
        """Update a node's namespaces attribute in the backend."""
        try:
            # First, get the current node data including namespaces
            get_success, get_content, get_error = await self.communication.request_and_get_response(
                operation="get_node",
                params={"node_id": node_id},
                sender="NamespacesView"
            )
            
            if get_success and get_content and "result" in get_content:
                # Extract node data from the result field
                node_data = get_content["result"]
                
                # Parse existing namespaces
                current_namespaces = []
                if "namespaces" in node_data:
                    if isinstance(node_data["namespaces"], str):
                        current_namespaces = [ns.strip() for ns in node_data["namespaces"].split(',') if ns.strip()]
                    elif isinstance(node_data["namespaces"], (list, tuple)):
                        current_namespaces = [str(ns).strip() for ns in node_data["namespaces"] if str(ns).strip()]
                
                # Modify namespaces based on 'add' parameter
                if add and namespace not in current_namespaces:
                    current_namespaces.append(namespace)
                elif not add and namespace in current_namespaces:
                    current_namespaces.remove(namespace)
                else:
                    # No change needed
                    return
                
                # Format as comma-separated string
                new_namespaces = ", ".join(current_namespaces)
                
                # Update the node with modified namespaces
                edit_success, edit_content, edit_error = await self.communication.request_and_get_response(
                    operation="edit_node",
                    params={
                        "node_id": node_id,
                        "attributes": {
                            "namespaces": new_namespaces
                        }
                    },
                    sender="NamespacesView"
                )
                
                if not edit_success:
                    logger.error(f"Error updating namespaces for node {node_id}: {edit_error or 'Unknown error'}")
            else:
                logger.error(f"Error retrieving node {node_id}: {get_error or 'Unknown error'}")
    
        except Exception as e:
            logger.error(f"Error in _update_node_namespace: {e}")
            self.status_label.setText(f"Error updating node namespace: {str(e)}")

    def expand_all(self):
        """Expand all items in the tree."""
        self.tree_widget.expandAll()
        
    def collapse_all(self):
        """Collapse all items in the tree."""
        self.tree_widget.collapseAll()

    def select_all_types(self):
        """Select all node type checkboxes."""
        for node_type in self.node_types:
            self.type_dropdown.set_check_state(node_type.capitalize(), True)
        self.filter_by_types()
        
    def select_no_types(self):
        """Deselect all node type checkboxes."""
        for node_type in self.node_types:
            self.type_dropdown.set_check_state(node_type.capitalize(), False)
        self.filter_by_types()

    def filter_by_types(self):
        """Apply filtering based on selected node types."""
        # Get the selected node types from dropdown
        selected_types = [type_name.lower() for type_name in self.type_dropdown.get_checked_items()]
        
        # Apply filtering by hiding/showing appropriate items
        for i in range(self.tree_widget.topLevelItemCount()):
            self._filter_by_types_recursive(self.tree_widget.topLevelItem(i), selected_types)
        
        # Update status label
        if not selected_types:
            self.status_label.setText("No node types selected for filtering")
        elif len(selected_types) == len(self.node_types):
            self.status_label.setText("Showing all node types")
        else:
            types_str = ", ".join(t.capitalize() for t in selected_types)
            self.status_label.setText(f"Filtered by types: {types_str}")

    def _filter_by_types_recursive(self, item, selected_types):
        """Recursively apply type filtering to all child nodes."""
        visible_children = 0
        
        # Process all folder children first (non-leaf nodes)
        for i in range(item.childCount()):
            child = item.child(i)
            node_id = child.data(0, Qt.ItemDataRole.UserRole)
            
            # If this is a namespace folder (no node_id), recurse into it
            if not node_id:
                if self._filter_by_types_recursive(child, selected_types):
                    visible_children += 1
            else:
                # This is a leaf node, check its type
                node_type = self.get_node_type(node_id)
                
                # Show/hide based on type
                is_visible = node_type in selected_types
                child.setHidden(not is_visible)
                
                if is_visible:
                    visible_children += 1
        
        # A folder should be visible if it has visible children
        should_show = visible_children > 0
        item.setHidden(not should_show)
        
        return should_show

    def update_focus(self, text):
        """Update focus when the text changes (for auto-completion)."""
        # Just update the text, don't apply filtering yet
        pass

    def add_selected_to_focus(self):
        """Add selected namespace from dropdown to the multi-select focus input."""
        selected_namespace = self.focus_combo.currentText()
        if not selected_namespace:
            return
            
        # Get current focus text
        current_focus = self.focus_multi_edit.text().strip()
        
        # Parse existing namespaces
        namespaces = set()
        if current_focus:
            namespaces = set(ns.strip() for ns in current_focus.split(',') if ns.strip())
        
        # Add the selected namespace
        namespaces.add(selected_namespace)
        
        # Update the multi-select input with sorted namespaces
        sorted_namespaces = sorted(namespaces)
        self.focus_multi_edit.setText(', '.join(sorted_namespaces))
        
        # Update status
        self.status_label.setText(f"Added {selected_namespace} to focus")

    def apply_focus(self):
        """Apply focus to specific namespaces, restructuring the tree."""
        focus_text = self.focus_multi_edit.text().strip()
        
        if not focus_text:
            self.clear_focus()
            return
        
        # Set focused namespaces from the multi-select input
        raw_namespaces = [ns.strip() for ns in focus_text.split(',')]
        
        # Filter for valid namespaces
        valid_namespaces = set()
        all_namespaces = self._collect_all_namespaces(self.namespace_tree)
        
        # Process each namespace
        for ns in raw_namespaces:
            if ns in all_namespaces:
                # Check if this namespace is a child of another namespace in the set
                is_child = False
                for other_ns in valid_namespaces.copy():  # Use copy to allow modification during iteration
                    if ns != other_ns and (ns.startswith(other_ns + '.') or other_ns.startswith(ns + '.')):
                        # If this is a more specific (longer) path, replace the parent
                        if len(ns) > len(other_ns) and ns.startswith(other_ns + '.'):
                            # Keep both - we want to show the entire hierarchy
                            is_child = False
                        # If this is a parent of an already included namespace, skip it
                        elif len(ns) < len(other_ns) and other_ns.startswith(ns + '.'):
                            is_child = True
                            break
                
                if not is_child:
                    valid_namespaces.add(ns)
        
        # Store the validated namespaces
        self.focused_namespaces = valid_namespaces
        
        if not self.focused_namespaces:
            self.clear_focus()
            return
        
        logger.info(f"Focusing on namespaces: {self.focused_namespaces}")
        
        # Update the multi-select input with only valid namespaces
        self.focus_multi_edit.setText(', '.join(sorted(self.focused_namespaces)))
        
        # Restructure the tree with focused namespaces at top
        self.restructure_tree_for_focus(self.focused_namespaces)
        
        self.status_label.setText(f"Focused on: {', '.join(self.focused_namespaces)}")

    def clear_focus(self):
        """Clear namespace focus and restore original tree structure."""
        if not self.focused_namespaces:
            return
            
        self.focused_namespaces = set()
        self.focus_multi_edit.clear()
        
        # Restore original tree structure
        self.update_tree_widget()
        
        # Re-apply filtering
        self.filter_by_types()
        if self.current_filter_text:
            self.filter_namespaces()
        
        self.status_label.setText("Focus cleared")

    def filter_namespaces(self):
        """Filter the namespaces tree based on user input and focus."""
        # Store current filter text
        self.current_filter_text = self.namespace_filter.text().lower()
        
        # Apply filter recursively to all items
        for i in range(self.tree_widget.topLevelItemCount()):
            self._filter_item_recursive(self.tree_widget.topLevelItem(i), self.current_filter_text)

    def _filter_item_recursive(self, item, filter_text):
        """Recursively filter an item and its children."""
        # Count visible children
        visible_children = 0
        
        # Get the full namespace path for this item
        namespace_path = self._get_item_namespace_path(item)
        
        # Process all children first
        for i in range(item.childCount()):
            child = item.child(i)
            if self._filter_item_recursive(child, filter_text):
                visible_children += 1
        
        # Check if this item matches text filter
        item_text = item.text(0).lower()
        matches_text = not filter_text or filter_text in item_text
        
        # Check if this item or any parent matches focus filter (if active)
        matches_focus = not self.focused_namespaces or namespace_path in self.focused_namespaces
        
        # Node ID means this is a leaf node (actual graph node)
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Special case: If this is a leaf node, also check for type filtering
        if node_id:
            node_type = self.get_node_type(node_id)
            matches_type = node_type in [t.lower() for t in self.type_dropdown.get_checked_items()]
        else:
            matches_type = True  # Folders are always visible if they have visible children
        
        # Item is visible if:
        # 1. It matches the text filter (or no text filter), AND
        # 2. It matches the focus filter (or no focus filter), AND 
        # 3. Either:
        #    a. It's a leaf node that matches type filter, OR
        #    b. It's a folder that has visible children
        should_show = (matches_text and matches_focus and 
                      ((node_id and matches_type) or (not node_id and visible_children > 0)))
        
        item.setHidden(not should_show)
        
        # If filter is active and this item matches, expand it and its parents
        if filter_text and (matches_text or visible_children > 0):
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()
            if not node_id:  # Only expand folders, not leaf nodes
                item.setExpanded(True)
        
        return should_show

    def _get_item_namespace_path(self, item):
        """Get the full namespace path for an item by traversing up the tree."""
        if not item:
            return ""
        
        path_parts = []
        current = item
        
        # Only include folder items (actual namespaces), not leaf nodes
        if not item.data(0, Qt.ItemDataRole.UserRole):
            path_parts.append(item.text(0))
        
        # Traverse up the tree
        parent = item.parent()
        while parent:
            # Only include if it's a namespace folder (no node_id)
            if not parent.data(0, Qt.ItemDataRole.UserRole):
                path_parts.append(parent.text(0))
            parent = parent.parent()
        
        # Join path parts in reverse order (root to leaf)
        return '.'.join(reversed(path_parts))

    def show_context_menu(self, position):
        """Show context menu for namespace items."""
        item = self.tree_widget.itemAt(position)
        if not item:
            return
        
        # Create context menu
        menu = QtWidgets.QMenu(self)
        
        # Node ID indicates this is a leaf node (actual graph node)
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not node_id:
            # This is a namespace folder
            namespace_path = self._get_item_namespace_path(item)
            
            focus_action = menu.addAction(f"Focus on '{namespace_path}'")
            focus_action.triggered.connect(lambda: self._focus_on_namespace(namespace_path))
            
            expand_action = menu.addAction("Expand All Children")
            expand_action.triggered.connect(lambda: self._expand_item_children(item))
            
            collapse_action = menu.addAction("Collapse All Children")
            collapse_action.triggered.connect(lambda: self._collapse_item_children(item))
        else:
            # This is a node
            open_action = menu.addAction("Edit Node")
            open_action.triggered.connect(lambda: self._open_node_editor(node_id))
        
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def _focus_on_namespace(self, namespace):
        """Focus on a specific namespace."""
        # Add this namespace to the multi-select focus input
        current_focus = self.focus_multi_edit.text().strip()
        namespaces = set()
        if current_focus:
            namespaces = set(ns.strip() for ns in current_focus.split(','))
        namespaces.add(namespace)
        
        # Update the multi-select input
        self.focus_multi_edit.setText(', '.join(sorted(namespaces)))
        
        # Apply the focus
        self.apply_focus()

    def _expand_item_children(self, item):
        """Expand an item and all its children."""
        item.setExpanded(True)
        for i in range(item.childCount()):
            child = item.child(i)
            if not child.data(0, Qt.ItemDataRole.UserRole):  # Only expand folders
                self._expand_item_children(child)

    def _collapse_item_children(self, item):
        """Collapse an item and all its children."""
        for i in range(item.childCount()):
            child = item.child(i)
            if not child.data(0, Qt.ItemDataRole.UserRole):  # Only folders have children
                self._collapse_item_children(child)
        item.setExpanded(False)

    def _open_node_editor(self, node_id):
        """Open the node editor for a specific node."""
        try:
            import uuid
            if isinstance(node_id, str):
                node_id = uuid.UUID(node_id)
            
            # Use the same logic as double-click
            asyncio.create_task(edit_node_by_uuid(self.main_window, node_id))
        except Exception as e:
            logger.exception(f"Error opening node editor: {e}")

    def refresh_async(self):
        """Asynchronously refresh the namespaces list."""
        self.status_label.setText("Refreshing namespaces...")
        
        # Remember focus state before refresh
        focused_namespaces = self.focused_namespaces.copy() if self.focused_namespaces else set()
        filter_text = self.current_filter_text
        
        # Refresh the data
        task = asyncio.create_task(self.fetch_namespaces())
        
        # After refresh, restore focus and filters
        def restore_state(_):
            if focused_namespaces:
                self.focused_namespaces = focused_namespaces
                self.focus_multi_edit.setText(', '.join(sorted(focused_namespaces)))
                # Apply focus (this will restructure the tree)
                self.apply_focus()
                
            if filter_text:
                self.namespace_filter.setText(filter_text)
                
            # Re-apply type filtering
            self.filter_by_types()
        
        task.add_done_callback(restore_state)
        
    async def fetch_namespaces(self):
        """Fetch the graph and extract namespace hierarchy."""
        try:
            # Get the graph from the main window
            graph = self.main_window.graph
            if not graph:
                self.status_label.setText("No graph available")
                return
            
            # Clear existing namespace tree
            self.namespace_tree = NamespaceTreeNode("root")
            
            if self.current_view_mode == "namespaces":
                # Extract and organize standard namespaces
                self.extract_namespaces_to_tree(graph)
                self.status_label.setText("Using standard namespace organization")
            else:
                # Use Zettelkasten indexer with current jitter setting
                self.status_label.setText(f"Calculating Zettelkasten index (randomness: {self.jitter_value:.2f})...")
                self.zettelkasten_indexer = ZettelkastenIndexCalculator(randomness_factor=self.jitter_value)
                indexed_nodes = self.zettelkasten_indexer.calculate_indices(graph)
                
                # Convert Zettelkasten index format to our namespace tree format
                self.convert_zettelkasten_to_tree(indexed_nodes, graph)
                self.status_label.setText(f"Using Zettelkasten index (randomness: {self.jitter_value:.2f})")
            
            # Update the UI
            self.update_tree_widget()
            
            # Signal completion
            self.refresh_completed.emit()
            
        except Exception as e:
            logger.exception(f"Error fetching namespaces: {e}")
            self.status_label.setText(f"Error: {str(e)}")
    
    def extract_namespaces_to_tree(self, graph):
        """Extract namespaces from graph and organize in tree structure."""
        # Process explicit namespaces
        for node_id, node_data in graph.nodes(data=True):
            # Extract explicit namespaces
            if 'namespaces' in node_data:
                namespaces = node_data['namespaces']
                node_id_str = str(node_id)
                node_name = node_data.get('name') or node_data.get('title', '')
                
                # Handle different formats (string, list, etc.)
                if isinstance(namespaces, str):
                    # Split by commas
                    for ns in namespaces.split(','):
                        if ns := ns.strip():
                            self.add_namespace_to_tree(ns, node_id_str, "explicit", node_name)
                elif isinstance(namespaces, (list, tuple, set)):
                    for ns in namespaces:
                        if ns := str(ns).strip():
                            self.add_namespace_to_tree(ns, node_id_str, "explicit", node_name)
            
            # Extract namespaces from file paths
            if 'file_path' in node_data:
                file_path = node_data['file_path']
                node_id_str = str(node_id)
                
                if file_path and isinstance(file_path, str):
                    # Extract directory structure
                    path = os.path.dirname(file_path)
                    if path:
                        # Convert path separators to dots but ensure no empty components
                        # Normalize path first to handle different separators
                        norm_path = os.path.normpath(path)
                        # Split by separators and filter out empty parts
                        parts = [p for p in norm_path.replace('\\', '/').split('/') if p]
                        # Join with dots to create the namespace
                        if parts:
                            path_namespace = '.'.join(parts)
                            self.add_namespace_to_tree(path_namespace, node_id_str, "path")

        # Pass 2: Identify page nodes and mark their corresponding NamespaceTreeNodes as representative
        for node_id, node_data in graph.nodes(data=True):
            if node_data.get('node_type') == 'page':
                page_id_str = str(node_id)
                page_name = node_data.get('name') or node_data.get('title', '')
                
                # A page's content (like text blocks) often has a namespace like "ParentNS.PageName"
                # The page itself might have "ParentNS" as its namespace.
                # We want the "ParentNS.PageName" NamespaceTreeNode to be represented by this page_id_str.
                
                page_declared_namespaces = node_data.get('namespaces', [])
                if isinstance(page_declared_namespaces, str):
                    page_declared_namespaces = [ns.strip() for ns in page_declared_namespaces.split(',') if ns.strip()]
                elif not isinstance(page_declared_namespaces, (list, tuple, set)):
                    page_declared_namespaces = []

                for parent_ns_str in page_declared_namespaces:
                    if not page_name: continue # Page must have a name to form child namespace

                    # Target namespace for page content is parent_ns_str + "." + page_name
                    # Handle quoted segments in page_name for namespace construction
                    quoted_page_name = f"'{page_name}'" if ' ' in page_name or '.' in page_name else page_name
                    
                    content_ns_str = f"{parent_ns_str}.{quoted_page_name}" if parent_ns_str else quoted_page_name

                    # Find the NamespaceTreeNode for content_ns_str
                    # Handle quoted segments in the namespace
                    parts = []
                    current_part = ""
                    in_quotes = False
                    
                    # Parse the namespace string handling quoted segments
                    for char in content_ns_str:
                        if char == "'" and not in_quotes:  # Start of quoted segment
                            in_quotes = True
                        elif char == "'" and in_quotes:  # End of quoted segment
                            in_quotes = False
                        elif char == '.' and not in_quotes:  # Namespace separator (only outside quotes)
                            # Only add non-empty parts
                            if current_part:
                                parts.append(current_part)
                            current_part = ""
                        else:  # Regular character or dot within quotes
                            current_part += char
                    
                    # Add the last part if not empty
                    if current_part:
                        parts.append(current_part)
                    
                    # Skip if no valid parts
                    if not parts:
                        continue
                        
                    # Navigate/build the tree
                    target_tns = self.namespace_tree
                    
                    # Keep track of the full namespace path as we build it
                    current_namespace = ""
                    
                    for i, part in enumerate(parts):
                        # Update the current namespace path
                        if current_namespace:
                            current_namespace += f".{part}"
                        else:
                            current_namespace = part
                            
                        if part not in target_tns.children:
                            target_tns.children[part] = NamespaceTreeNode(part)
                            
                        # Move to the next node in the tree
                        target_tns = target_tns.children[part]
                    
                    # ALSO find the namespace folder for the parent namespace
                    parent_tns = self.namespace_tree
                    parent_parts = []
                    current_part = ""
                    in_quotes = False
                    
                    # Parse the parent namespace string to get its parts
                    for char_idx, char_val in enumerate(parent_ns_str):
                        if char_val == "'" and (char_idx == 0 or parent_ns_str[char_idx-1] != '\\'):
                            in_quotes = not in_quotes
                        elif char_val == '.' and not in_quotes:
                            if current_part: parent_parts.append(current_part)
                            current_part = ""
                        else:
                            current_part += char_val
                    
                    if current_part: parent_parts.append(current_part)
                    
                    # Navigate to parent namespace node
                    found_parent_tns = True
                    for part in parent_parts:
                        if part in parent_tns.children:
                            parent_tns = parent_tns.children[part]
                        else:
                            found_parent_tns = False
                            break
                    
                    # If we found both the parent and child namespace nodes
                    if found_parent_tns and target_tns.name == parts[-1]:
                        target_tns.representative_node = page_id_str
                        logger.debug(f"Setting representative_node for TNS '{content_ns_str}' to page {page_id_str} ({page_name})")
                        
                        # IMPORTANT: If this page node is directly in the node_ids list of parent_tns,
                        # mark it for removal to prevent duplication
                        if page_id_str in parent_tns.node_ids:
                            # We can't remove while iterating, so just mark with a flag attribute
                            if not hasattr(parent_tns, 'nodes_to_remove'):
                                parent_tns.nodes_to_remove = set()
                            parent_tns.nodes_to_remove.add(page_id_str)
                            logger.debug(f"Marked page node {page_id_str} ({page_name}) for removal from parent TNS to prevent duplication")
                   
        
        # Pass 3: Clean up the marked nodes to remove from parent namespaces
        self._remove_marked_nodes_from_tree(self.namespace_tree)

    def _remove_marked_nodes_from_tree(self, tree_node):
        """Remove marked nodes from tree_node and its children recursively."""
        # Remove nodes marked for removal
        if hasattr(tree_node, 'nodes_to_remove') and tree_node.nodes_to_remove:
            for node_id in tree_node.nodes_to_remove:
                if node_id in tree_node.node_ids:
                    tree_node.node_ids.remove(node_id)
                    logger.debug(f"Removed node {node_id} from TNS {tree_node.name} to prevent duplication")
        
        # Recursively process children
        for child_node in tree_node.children.values():
            self._remove_marked_nodes_from_tree(child_node)

    def add_namespace_to_tree(self, namespace, node_id, source_type, node_name=''):
        """Add a namespace to the tree structure."""
        # Handle quoted segments in the namespace
        parts = []
        current_part = ""
        in_quotes = False
        
        # Parse the namespace string handling quoted segments
        for char in namespace:
            if char == "'" and not in_quotes:  # Start of quoted segment
                in_quotes = True
            elif char == "'" and in_quotes:  # End of quoted segment
                in_quotes = False
            elif char == '.' and not in_quotes:  # Namespace separator (only outside quotes)
                # Only add non-empty parts
                if current_part:
                    parts.append(current_part)
                current_part = ""
            else:  # Regular character or dot within quotes
                current_part += char
        
        # Add the last part if not empty
        if current_part:
            parts.append(current_part)
        
        # Skip if no valid parts
        if not parts:
            return
            
        # Navigate/build the tree
        current_node = self.namespace_tree
        
        # Keep track of the full namespace path as we build it
        current_namespace = ""
        
        for i, part in enumerate(parts):
            # Update the current namespace path
            if current_namespace:
                current_namespace += f".{part}"
            else:
                current_namespace = part
                
            if part not in current_node.children:
                current_node.children[part] = NamespaceTreeNode(part)
                
            # Move to the next node in the tree
            current_node = current_node.children[part]
            
            # Check if this is the leaf namespace part and node name matches the namespace part
            # For example, if namespace is "projects.research" and node name is "research"
            if i == len(parts) - 1 and node_name == part:
                # This node should represent the folder itself
                current_node.representative_node = node_id
                logger.debug(f"Node '{node_name}' ({node_id}) will represent namespace '{current_namespace}'")
        
        # Add node ID to the leaf node
        if node_id not in current_node.node_ids:
            current_node.node_ids.append(node_id)
    
    def update_tree_widget(self):
        """Update the tree widget with the namespace hierarchy."""
        self.tree_widget.clear()
        
        # Update the focus combo with all available namespaces
        self.focus_combo.clear()
        all_namespaces = self._collect_all_namespaces(self.namespace_tree)
        for ns in sorted(all_namespaces):
            self.focus_combo.addItem(ns)
        
        # Add namespaces from the tree
        total_nodes = self.build_tree_widget_from_node(self.namespace_tree, self.tree_widget)
        
        # Expand to first level by default
        self.tree_widget.expandToDepth(1)

    def _collect_all_namespaces(self, tree_node, current_path=""):
        """Recursively collect all namespace paths in the tree."""
        namespaces = set()
        
        for name, child_node in tree_node.children.items():
            # Build the full path to this node
            path = f"{current_path}.{name}" if current_path else name
            
            # Add this path
            namespaces.add(path)
            
            # Recursively add child paths
            child_namespaces = self._collect_all_namespaces(child_node, path)
            namespaces.update(child_namespaces)
            
        return namespaces
    
    def build_tree_widget_from_node(self, tree_node, parent_widget_item):
        """Recursively build tree widget items from the namespace tree."""
        total_nodes = 0
        
        # Sort child nodes alphabetically
        sorted_children = sorted(tree_node.children.items())
        
        for name, child_node in sorted_children:
            # Create tree item
            if isinstance(parent_widget_item, QtWidgets.QTreeWidget):
                item = QtWidgets.QTreeWidgetItem(parent_widget_item)
            else:
                item = QtWidgets.QTreeWidgetItem(parent_widget_item)
            
            # Get count of all nodes in this subtree
            child_count = len(child_node.node_ids)
            subtree_count = 0
            
            # Check if this namespace node has a representative
            is_represented_by_node = child_node.representative_node is not None
            
            # Extract the index prefix if in Zettelkasten mode
            index_prefix = ""
            if self.current_view_mode == "zettelkasten":
                # Try to extract the index from the name (assuming format: "1.2. Name")
                parts = name.split(".", 1)
                if len(parts) > 1 and parts[0].strip().isdigit():
                    index_prefix = f"[{parts[0].strip()}] "
                else:
                    # Try to find any numeric prefix before a dot or space
                    import re
                    match = re.match(r'^(\d+(\.\d+)*)[.\s]', name)
                    if match:
                        index_prefix = f"[{match.group(1)}] "
            
            # If the namespace is represented by a node, use that node's data
            if is_represented_by_node:
                node_id = child_node.representative_node
                node_data = self.get_node_data(node_id)
                
                # Set text and tooltip from the representative node
                node_name = node_data.get('name') or node_data.get('title', name)
                display_name = f"{index_prefix}{node_name}"  # Add index prefix in Zettelkasten mode
                item.setText(0, display_name)
                item.setToolTip(0, f"Node: {node_name} representing namespace {name}")
                
                # Store the node ID so we can open/edit it
                item.setData(0, Qt.ItemDataRole.UserRole, node_id)
                
                # Use the appropriate icon based on node type
                node_type = node_data.get('node_type', '')
                if node_type and node_type in self.node_type_icons:
                    item.setIcon(0, self.node_type_icons[node_type])
                else:
                    # Default to special combined folder+node icon if available
                    item.setIcon(0, self.folder_icon)
                    
                # Add a visual indicator that this is both a node and a folder
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
            else:
                # Regular namespace folder
                # In Zettelkasten mode, preserve the index in the display
                display_name = name
                if self.current_view_mode == "zettelkasten" and index_prefix:
                    display_name = f"{index_prefix}{name.split('.', 1)[1].strip() if '.' in name else name}"
                    
                item.setText(0, display_name)
                item.setIcon(0, self.folder_icon)
            
            # Always process children, even for representative nodes
            if child_node.children:
                subtree_count = self.build_tree_widget_from_node(child_node, item)
            
            # Add direct node IDs as children - skip the representative node if it exists
            if child_node.node_ids:
                # Sort node IDs to ensure alphabetical display
                sorted_nodes = []
                for node_id in child_node.node_ids:
                    # Skip the representative node as it's already represented by the folder
                    if node_id == child_node.representative_node:
                        continue
                    
                    # Skip if this node is the representative of a child folder
                    is_representative_of_child = False
                    for child_name, grandchild in child_node.children.items():
                        if grandchild.representative_node == node_id:
                            is_representative_of_child = True
                            break
                    
                    if is_representative_of_child:
                        logger.debug(f"Skipping node {node_id} as it represents a child folder")
                        continue
                        
                    label = self.get_node_label(node_id)
                    sorted_nodes.append((label, node_id))
                
                # Sort by the label for alphabetical order
                sorted_nodes.sort()
                
                for label, node_id in sorted_nodes:
                    node_item = QtWidgets.QTreeWidgetItem(item)
                    # In Zettelkasten mode, add the node's position in the child list as a prefix
                    if self.current_view_mode == "zettelkasten":
                        # Extract parent index from item text
                        parent_text = item.text(0)
                        parent_index = ""
                        if "[" in parent_text and "]" in parent_text:
                            parent_index = parent_text.split("[", 1)[1].split("]", 1)[0]
                        
                        # Add child position after parent index
                        child_position = sorted_nodes.index((label, node_id)) + 1
                        if parent_index:
                            node_prefix = f"[{parent_index}.{child_position}] "
                        else:
                            node_prefix = f"[{child_position}] "
                        
                        node_item.setText(0, f"{node_prefix}{label}")
                    else:
                        node_item.setText(0, label)
                    
                    # Choose appropriate icon based on node type
                    node_type = self.get_node_type(node_id)
                    if node_type and node_type in self.node_type_icons:
                        node_item.setIcon(0, self.node_type_icons[node_type])
                    else:
                        node_item.setIcon(0, self.default_icon)
                    
                    # Store node ID in the item data for click handling
                    node_item.setData(0, Qt.ItemDataRole.UserRole, node_id)
            
            # Calculate total count and set text with count in parentheses
            total_count = child_count + subtree_count
            if total_count > 0 and not is_represented_by_node:
                # In regular mode, append count. In Zettelkasten mode, keep the brackets format
                if self.current_view_mode == "namespaces":
                    item.setText(0, f"{item.text(0)} ({total_count})")
                else:
                    # Add count but preserve the index prefix
                    current_text = item.text(0)
                    if "] " in current_text:  # If the text already has an index prefix
                        prefix, rest = current_text.split("] ", 1)
                        item.setText(0, f"{prefix}] {rest} ({total_count})")
                    else:
                        item.setText(0, f"{current_text} ({total_count})")
            
            total_nodes += total_count
        
        return total_nodes
    
    def get_node_label(self, node_id):
        """Get a readable label for a node."""
        graph = self.main_window.graph
        if not graph:
            return f"Node {node_id}"
            
        try:
            # Try to convert string to UUID if needed
            if isinstance(node_id, str):
                import uuid
                node_id = uuid.UUID(node_id)
                
            # Check if node exists
            if node_id in graph.nodes:
                node_data = graph.nodes[node_id]
                name = node_data.get('name', '')
                label = node_data.get('label', str(node_id))
                
                if name:
                    return f"{name} ({label})"
                return label
        except Exception as e:
            logger.debug(f"Error getting node label: {e}")
            
        # Default fallback
        return f"Node {node_id}"
    
    def get_node_type(self, node_id):
        """Get the type of a node."""
        graph = self.main_window.graph
        if not graph:
            return None
            
        try:
            # Handle string node_id if needed
            if isinstance(node_id, str):
                import uuid
                node_id = uuid.UUID(node_id)
                
            # Get node data
            if node_id in graph.nodes:
                return graph.nodes[node_id].get('node_type', '')
        except Exception as e:
            logger.debug(f"Error getting node type: {e}")
            
        return None
    
    def filter_namespaces(self):
        """Filter the namespaces tree based on user input."""
        filter_text = self.namespace_filter.text().lower()
        
        # Apply filter recursively to all items
        for i in range(self.tree_widget.topLevelItemCount()):
            self._filter_item_recursive(self.tree_widget.topLevelItem(i), filter_text)
    
    def _filter_item_recursive(self, item, filter_text):
        """Recursively filter an item and its children."""
        # Count visible children
        visible_children = 0
        
        # Process all children first
        for i in range(item.childCount()):
            child = item.child(i)
            if self._filter_item_recursive(child, filter_text):
                visible_children += 1
        
        # Check if this item matches
        item_text = item.text(0).lower()
        visible = filter_text in item_text
        
        # Item is visible if it matches or has visible children
        should_show = visible or visible_children > 0
        item.setHidden(not should_show)
        
        # If filter is active and this item matches, expand it
        if filter_text and visible:
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()
            item.setExpanded(True)
        
        return should_show
    
    def update_status_label(self):
        """Update the status label with the refresh results."""
        # Count all namespaces and nodes
        total_namespaces = self._count_namespaces(self.namespace_tree)
        
        # Update status text
        if self.current_view_mode == "namespaces":
            self.status_label.setText(f"Found {total_namespaces} namespaces")
            self.notation_indicator.setVisible(False)
        else:  # zettelkasten mode
            self.status_label.setText(f"Found {total_namespaces} Zettelkasten indices")
            self.notation_indicator.setVisible(True)
    
    def _count_namespaces(self, tree_node):
        """Recursively count namespaces in the tree."""
        count = len(tree_node.children)
        for child_node in tree_node.children.values():
            count += self._count_namespaces(child_node)
        return count

    def on_item_clicked(self, item, column):
        """Store information about the clicked item and start timer."""
        # Store the clicked item information
        self.clicked_item = item
        self.clicked_column = column
        # Reset double click flag
        self.is_double_click = False
        # Start timer to detect if this is followed by a double click
        self.click_timer.start(250)  # 250ms is typical for double-click interval
    
    def on_item_double_clicked(self, item, column):
        """Handle double click immediately and prevent single click processing."""
        # Set flag to prevent single click handler from executing
        self.is_double_click = True
        # Stop the single click timer if running
        if self.click_timer.isActive():
            self.click_timer.stop()
        
        # Now handle the double click
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not node_id:
            # This is a namespace folder, not a node
            return
        
        logger.info(f"Double click on item: {item.text(0)}, Node ID: {node_id}")
        
        try:
            # Convert string node_id to UUID if needed
            import uuid
            if isinstance(node_id, str):
                node_id = uuid.UUID(node_id)
            
            # Always open the node dialog on double click
            logger.info(f"Opening node dialog for {node_id}")
            asyncio.create_task(edit_node_by_uuid(self.main_window, node_id))
                
        except Exception as e:
            logger.exception(f"Error handling double click: {e}")
    
    def process_single_click(self):
        """Process a single click after ensuring it's not part of a double click."""
        # If this was actually part of a double click, don't process
        if self.is_double_click or not self.clicked_item:
            return
        
        item = self.clicked_item
        
        # Get the node ID from item data
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not node_id:
            # This is a standard namespace folder without a representative node, not a clickable item
            return
        
        logger.info(f"Single click on item: {item.text(0)}, Node ID: {node_id}")
        
        try:
            # Convert string node_id to UUID if needed
            import uuid
            if isinstance(node_id, str):
                node_id = uuid.UUID(node_id)
            
            # Get node data to check for PDF files before calling open_by_id
            if self.main_window.graph and node_id in self.main_window.graph:
                # Use the new universal open_by_id method 
                if hasattr(self.main_window, 'open_by_id'):
                    logger.info("Using open_by_id method")
                    self.main_window.open_by_id(node_id)
                else:
                    # Fallback to legacy method if open_by_id doesn't exist
                    logger.warning("open_by_id method not found, falling back to edit_node_by_uuid")
                    asyncio.create_task(edit_node_by_uuid(self.main_window, node_id))
            else:
                logger.warning(f"Node {node_id} not found in graph")
        except Exception as e:
            logger.exception(f"Error handling single click: {e}")

    def restructure_tree_for_focus(self, focused_namespaces):
        """Restructure the tree to show focused namespaces at the top while preserving hierarchy."""
        # Remember the currently selected item if any
        current_item = self.tree_widget.currentItem()
        current_node_id = current_item.data(0, Qt.ItemDataRole.UserRole) if current_item else None
        
        # Clear the tree
        self.tree_widget.clear()
        
        # Process each focused namespace
        for namespace in sorted(focused_namespaces):
            # Split the namespace into parts
            parts = namespace.split('.')
            
            # Extract all nodes that match this namespace from the full tree
            focused_tree = self._extract_subtree(self.namespace_tree, parts)
            if focused_tree:
                # Build the tree widget using the extracted subtree
                item = QtWidgets.QTreeWidgetItem(self.tree_widget)
                item.setText(0, namespace)
                item.setIcon(0, self.folder_icon)
                
                # Count nodes in this subtree
                count = self._count_nodes_in_subtree(focused_tree)
                
                # Set text with count in parentheses 
                if count > 0:
                    item.setText(0, f"{namespace} ({count})")
                else:
                    item.setText(0, namespace)
                
                # Build the tree widget from the subtree
                if focused_tree.children:
                    self._build_widget_from_subtree(focused_tree, item)
                
                # Add direct nodes for this namespace
                self._add_nodes_to_item(focused_tree.node_ids, item)
                
                # Expand the root item
                item.setExpanded(True)
        
        # Apply type filtering
        self.filter_by_types()
        
        # Restore selection if possible
        if current_node_id:
            self._select_node_by_id(current_node_id)

    def _extract_subtree(self, tree_node, parts):
        """Extract a subtree that matches the given namespace parts."""
        if not parts:
            return None
        
        current_part = parts[0]
        
        # Check if this part exists in the current node's children
        if current_part not in tree_node.children:
            return None
        
        # Get the child node
        child_node = tree_node.children[current_part]
        
        if len(parts) == 1:
            # This is the target namespace, return a deep copy of its subtree
            return self._copy_tree_node(child_node)
        
        # Continue traversing down the tree
        return self._extract_subtree(child_node, parts[1:])

    def _copy_tree_node(self, node):
        """Create a deep copy of a namespace tree node."""
        copy = NamespaceTreeNode(node.name)
        copy.node_ids = node.node_ids.copy()
        
        for name, child in node.children.items():
            copy.children[name] = self._copy_tree_node(child)
        
        return copy

    def _count_nodes_in_subtree(self, tree_node):
        """Count all nodes in a subtree."""
        count = len(tree_node.node_ids)
        
        for child in tree_node.children.values():
            count += self._count_nodes_in_subtree(child)
        
        return count

    def _build_widget_from_subtree(self, tree_node, parent_item):
        """Build tree widget items from a subtree."""
        # Sort children alphabetically
        sorted_children = sorted(tree_node.children.items())
        
        for name, child_node in sorted_children:
            # Create item for this child
            item = QtWidgets.QTreeWidgetItem(parent_item)
            item.setIcon(0, self.folder_icon)
            
            # Count nodes in this child's subtree
            count = self._count_nodes_in_subtree(child_node)
            
            # Set text with count in parentheses
            if count > 0:
                item.setText(0, f"{name} ({count})")
            else:
                item.setText(0, name)
            
            # Add direct nodes for this child
            self._add_nodes_to_item(child_node.node_ids, item)
            
            # Continue recursively
            if child_node.children:
                self._build_widget_from_subtree(child_node, item)

    def _add_nodes_to_item(self, node_ids, parent_item):
        """Add node items as children of a tree item."""
        if not node_ids:
            return
        
        # Sort nodes by label for consistent display
        sorted_nodes = []
        for node_id in node_ids:
            label = self.get_node_label(node_id)
            sorted_nodes.append((label, node_id))
        
        # Sort by label
        sorted_nodes.sort()
        
        # Add items
        for label, node_id in sorted_nodes:
            node_item = QtWidgets.QTreeWidgetItem(parent_item)
            node_item.setText(0, label)
            
            # Set icon based on node type
            node_type = self.get_node_type(node_id)
            if node_type and node_type in self.node_type_icons:
                node_item.setIcon(0, self.node_type_icons[node_type])
            else:
                node_item.setIcon(0, self.default_icon)
            
            # Store node ID in the item data
            node_item.setData(0, Qt.ItemDataRole.UserRole, node_id)

    def _collect_nodes_in_namespace(self, namespace):
        """Collect all node IDs in a specific namespace and its child namespaces."""
        node_ids = []
        
        # Handle both explicit and file path namespaces
        graph = self.main_window.graph
        if not graph:
            return node_ids
        
        # Check each node to see if it belongs to the namespace
        for node_id, node_data in graph.nodes(data=True):
            try:
                # Check explicit namespaces
                if 'namespaces' in node_data:
                    namespaces = node_data['namespaces']
                    
                    # Convert to list of namespace strings
                    ns_list = []
                    if isinstance(namespaces, str):
                        # Split by commas
                        ns_list = [ns.strip() for ns in namespaces.split(',')]
                    elif isinstance(namespaces, (list, tuple, set)):
                        ns_list = [str(ns).strip() for ns in namespaces]
                    
                    # Check if this namespace or any parent namespace matches
                    for ns in ns_list:
                        # Check if the namespace exactly matches or is a child of the target namespace
                        if ns == namespace or ns.startswith(namespace + '.'):
                            node_ids.append(str(node_id))
                            break
                
                # Check file path namespaces
                if 'file_path' in node_data and node_id not in node_ids:  # Skip if already added
                    file_path = node_data['file_path']
                    if file_path and isinstance(file_path, str):
                        # Extract directory structure
                        path = os.path.dirname(file_path)
                        if path:
                            # Convert path separators to dots
                            norm_path = os.path.normpath(path)
                            parts = [p for p in norm_path.replace('\\', '/').split('/') if p]
                            if parts:
                                path_namespace = '.'.join(parts)
                                if path_namespace == namespace or path_namespace.startswith(namespace + '.'):
                                    node_ids.append(str(node_id))
            except Exception as e:
                logger.debug(f"Error processing node {node_id} for namespace {namespace}: {e}")
        
        logger.info(f"Found {len(node_ids)} nodes in namespace '{namespace}'")
        return node_ids

    def get_node_data(self, node_id):
        """Get data for a node from the graph."""
        graph = self.main_window.graph
        if not graph:
            return {}
            
        try:
            # Convert string to UUID if needed
            if isinstance(node_id, str):
                import uuid
                node_id = uuid.UUID(node_id)
                
            # Get node data
            if node_id in graph.nodes:
                return dict(graph.nodes[node_id])
        except Exception as e:
            logger.debug(f"Error getting node data: {e}")
            
        return {}

    def _select_node_by_id(self, node_id):
        """Find and select a node in the tree by its ID."""
        # Recursively search all items
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            found_item = self._find_item_by_node_id(item, node_id)
            if found_item:
                self.tree_widget.setCurrentItem(found_item)
                return True
        return False

    def _find_item_by_node_id(self, item, node_id):
        """Recursively find an item with the given node ID."""
        # Check if this item has the node ID
        if item.data(0, Qt.ItemDataRole.UserRole) == node_id:
            return item
            
        # Check child items
        for i in range(item.childCount()):
            child = item.child(i)
            found = self._find_item_by_node_id(child, node_id)
            if found:
                return found
        
        return None

    def on_view_mode_combo_changed(self, index):
        """Handle view mode change from the dropdown."""
        if index == 0:  # Standard Namespaces
            self.current_view_mode = "namespaces"
            self.jitter_container.setEnabled(False)
            self.notation_indicator.setVisible(False)
            self.status_label.setText("Switching to standard namespace view...")
        else:  # Zettelkasten Index
            self.current_view_mode = "zettelkasten"
            self.jitter_container.setEnabled(True)
            self.notation_indicator.setVisible(True)
            self.status_label.setText("Switching to Zettelkasten index view...")
        
        # Refresh the view with the new mode
        self.refresh_async()

    def on_jitter_changed(self, value):
        """Handle jitter slider value changes."""
        self.jitter_value = value / 100.0  # Convert to 0.0-1.0 range
        self.jitter_value_label.setText(f"{self.jitter_value:.2f}")
        
        # Only update immediately if in Zettelkasten mode
        if self.current_view_mode == "zettelkasten":
            self.refresh_async()

    def show_zettelkasten_help(self):
        """Show help dialog explaining Zettelkasten notation."""
        help_text = """
<h3>Zettelkasten Index Notation</h3>

<p>The Zettelkasten system uses hierarchical indexing to organize related notes:</p>

<ul>
<li><b>Main topics</b>: Numbered sequentially (1, 2, 3, ...)</li>
<li><b>Subtopics</b>: Main topic number + dot + sequential number (1.1, 1.2, 1.3, ...)</li>
<li><b>Further subtopics</b>: Continue with more dots and numbers (1.1.1, 1.1.2, ...)</li>
</ul>

<p>This creates a flexible system where related notes are grouped by similar numbers and each note has a unique address.</p>

<p>Adjust the <b>randomness</b> slider to explore different possible organizations of your content.</p>
"""
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Zettelkasten Index Help")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(help_text)
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        msg_box.exec()

    def convert_zettelkasten_to_tree(self, indexed_nodes, graph):
        """Convert Zettelkasten index format to namespace tree structure."""
        # Find all root nodes in the Zettelkasten index
        root_nodes = [node_id for node_id, data in indexed_nodes.items() if data.get('is_root', False)]
        
        if not root_nodes:
            self.status_label.setText("No root nodes found in Zettelkasten index")
            return
        
        # Sort root nodes by index
        root_nodes.sort(key=lambda node_id: indexed_nodes[node_id].get('index', ''))
        
        # Update notation indicator with actual numbering sample
        sample_indices = []
        if len(root_nodes) > 0:
            sample_node = root_nodes[0]
            if sample_node in indexed_nodes:
                sample_indices.append(indexed_nodes[sample_node].get('index', '1'))
                
                # Get a child if available
                children = indexed_nodes[sample_node].get('children', [])
                if children and children[0] in indexed_nodes:
                    sample_indices.append(indexed_nodes[children[0]].get('index', '1.1'))
                    
                    # Get a grandchild if available
                    grandchildren = indexed_nodes[children[0]].get('children', [])
                    if grandchildren and grandchildren[0] in indexed_nodes:
                        sample_indices.append(indexed_nodes[grandchildren[0]].get('index', '1.1.1'))
        
        if sample_indices:
            self.notation_indicator.setText(f"Format: {' → '.join(sample_indices)}")
        else:
            self.notation_indicator.setText("Format: Number.Subnumber")
        
        # Build the namespace tree from the indexed nodes
        for node_id in root_nodes:
            # Create a tree node for this root
            if node_id in graph.nodes:
                node_data = graph.nodes[node_id]
                node_name = node_data.get('name', node_data.get('title', str(node_id)[:8]))
                
                # Get index from Zettelkasten structure
                index = indexed_nodes[node_id].get('index', '')
                namespace = f"{index}. {node_name}"
                
                # Add this node to the root of our namespace tree
                if namespace not in self.namespace_tree.children:
                    self.namespace_tree.children[namespace] = NamespaceTreeNode(namespace)
                
                # Add this node ID to the namespace tree node
                self.namespace_tree.children[namespace].node_ids.append(str(node_id))
                
                # Add the node's representative role
                self.namespace_tree.children[namespace].representative_node = str(node_id)
                
                # Process children recursively
                self._add_zettelkasten_children(
                    node_id, 
                    indexed_nodes, 
                    graph, 
                    self.namespace_tree.children[namespace]
                )
    
    def _add_zettelkasten_children(self, parent_id, indexed_nodes, graph, parent_tree_node):
        """Recursively add children from Zettelkasten index to the namespace tree."""
        if parent_id not in indexed_nodes:
            return
            
        # Get children of this node from the Zettelkasten index
        children = indexed_nodes[parent_id].get('children', [])
        
        # Sort children by their index
        sorted_children = []
        for child_id in children:
            if child_id in indexed_nodes:
                child_index = indexed_nodes[child_id].get('index', '')
                sorted_children.append((child_index, child_id))
        sorted_children.sort()  # Sort by index
        
        # Process each child
        for index, child_id in sorted_children:
            if child_id in graph.nodes:
                node_data = graph.nodes[child_id]
                node_name = node_data.get('name', node_data.get('title', str(child_id)[:8]))
                
                # Form namespace from index and name
                namespace = f"{index}. {node_name}"
                
                # Add this child to the parent tree node
                if namespace not in parent_tree_node.children:
                    parent_tree_node.children[namespace] = NamespaceTreeNode(namespace)
                
                # Add this node ID to the tree node
                parent_tree_node.children[namespace].node_ids.append(str(child_id))
                
                # Add the node's representative role
                parent_tree_node.children[namespace].representative_node = str(child_id)
                
                # Continue recursively
                self._add_zettelkasten_children(
                    child_id,
                    indexed_nodes,
                    graph,
                    parent_tree_node.children[namespace]
                )
    
    def transfer_nodes_to_target(self):
        """Transfer selected nodes from source to target namespace."""
        self._transfer_nodes(self.source_panel, self.target_panel)

    def transfer_nodes_to_source(self):
        """Transfer selected nodes from target to source namespace."""
        self._transfer_nodes(self.target_panel, self.source_panel)

    def _transfer_nodes(self, source_panel, target_panel):
        """Transfer selected nodes from source to target namespace."""
        try:
            # Get selected nodes from source
            selected_items = source_panel.node_list.selectedItems()
            if not selected_items:
                self.status_label.setText("No nodes selected to transfer")
                return
                
            # Get source and target namespaces
            source_namespace = source_panel.namespace_input.text().strip()
            target_namespace = target_panel.namespace_input.text().strip()
            
            if not target_namespace:
                self.status_label.setText("Target namespace is empty")
                return
                
            # Collect node IDs to transfer
            node_ids = []
            for item in selected_items:
                node_id = item.data(Qt.ItemDataRole.UserRole)
                if node_id:
                    node_ids.append(node_id)
            
            if not node_ids:
                self.status_label.setText("No valid nodes selected to transfer")
                return
                
            # Use the communication to transfer nodes in the backend
            asyncio.create_task(self._async_transfer_nodes(node_ids, source_namespace, target_namespace))
            
        except Exception as e:
            logger.error(f"Error transferring nodes: {e}")
            self.status_label.setText(f"Error transferring nodes: {str(e)}")

    async def _async_transfer_nodes(self, node_ids, source_namespace, target_namespace):
        """Asynchronously transfer nodes from one namespace to another."""
        try:
            # Show status
            self.status_label.setText(f"Transferring {len(node_ids)} nodes to '{target_namespace}'...")
            
            # Process each node individually
            success_count = 0
            error_count = 0
            
            for node_id in node_ids:
                # First, get the current node data including namespaces
                get_success, get_content, get_error = await self.communication.request_and_get_response(
                    operation="get_node",
                    params={"node_id": node_id},
                    sender="NamespacesView"
                )
                
                if get_success and get_content and "result" in get_content:
                    # Extract node data from the result field, not from a "node" field
                    node_data = get_content["result"]
                    
                    # Parse existing namespaces
                    current_namespaces = []
                    if "namespaces" in node_data:
                        if isinstance(node_data["namespaces"], str):
                            current_namespaces = [ns.strip() for ns in node_data["namespaces"].split(',') if ns.strip()]
                        elif isinstance(node_data["namespaces"], (list, tuple)):
                            current_namespaces = [str(ns).strip() for ns in node_data["namespaces"] if str(ns).strip()]
                    
                    # Remove source namespace if specified and present
                    if source_namespace and source_namespace in current_namespaces:
                        current_namespaces.remove(source_namespace)
                    
                    # Add target namespace if not already present
                    if target_namespace not in current_namespaces:
                        current_namespaces.append(target_namespace)
                    
                    # Format as comma-separated string
                    new_namespaces = ", ".join(current_namespaces)
                    
                    # Update the node with modified namespaces
                    edit_success, edit_content, edit_error = await self.communication.request_and_get_response(
                        operation="edit_node",
                        params={
                            "node_id": node_id,
                            "attributes": {
                                "namespaces": new_namespaces
                            }
                        },
                        sender="NamespacesView"
                    )
                    
                    if edit_success and edit_content and edit_content.get("result"):
                        success_count += 1
                    else:
                        error_count += 1
                        error_msg = edit_error or "Unknown error during node update"
                        logger.error(f"Error updating node {node_id}: {error_msg}")
                else:
                    error_count += 1
                    error_msg = get_error or "Unknown error retrieving node data"
                    logger.error(f"Error getting node {node_id}: {error_msg}")
            
            # Update status based on results
            if error_count == 0:
                self.status_label.setText(f"Successfully transferred {success_count} nodes to '{target_namespace}'")
            else:
                self.status_label.setText(f"Transferred {success_count} nodes, failed to transfer {error_count} nodes")
        
            # Refresh the graph to show changes immediately
            if success_count > 0 and hasattr(self.main_window, 'show_graph'):
                # Refresh the main window graph to reflect changes
                await self.main_window.show_graph(None)  # None means fetch latest from backend
            
            # Refresh the namespaces view itself
            self.refresh_async()
            
            # Update source and target panels
            source_text = self.source_panel.namespace_input.text().strip()
            target_text = self.target_panel.namespace_input.text().strip()
            
            if source_text:
                self.update_namespace_node_list(source_text, self.source_panel)
                
            if target_text:
                self.update_namespace_node_list(target_text, self.target_panel)
            
        except Exception as e:
            logger.error(f"Error in async transfer nodes: {e}")
            self.status_label.setText(f"Error transferring nodes: {str(e)}")

    def update_namespace_node_list(self, text, panel):
        """Update the node list based on the namespace text input."""
        try:
            panel.node_list.clear()
            
            if not text.strip():
                panel.node_count_label.setText("0 nodes")
                return
                
            # Find nodes in this namespace
            nodes = self._collect_nodes_in_namespace(text.strip())
            
            if not nodes:
                panel.node_count_label.setText("No nodes found")
                return
                
            # Add nodes to list with icons
            for node_id in nodes:
                try:
                    # Get node data
                    node_data = self.get_node_data(node_id)
                    node_name = node_data.get('name') or node_data.get('title', '')
                    node_type = node_data.get('node_type', '')
                    
                    # Create list item
                    item = QtWidgets.QListWidgetItem()
                    display_text = f"{node_name} ({node_id})" if node_name else node_id
                    item.setText(display_text)
                    
                    # Set icon based on node type
                    if node_type and node_type in self.node_type_icons:
                        item.setIcon(self.node_type_icons[node_type])
                    else:
                        item.setIcon(self.default_icon)
                        
                    # Store node ID in item data
                    item.setData(Qt.ItemDataRole.UserRole, node_id)
                    
                    # Add to list
                    panel.node_list.addItem(item)
                except Exception as e:
                    logger.debug(f"Error adding node {node_id} to list: {e}")
            
            # Update count label
            panel.node_count_label.setText(f"{len(nodes)} nodes")
            
        except Exception as e:
            logger.error(f"Error updating namespace node list: {e}")
            panel.node_count_label.setText("Error loading nodes")


