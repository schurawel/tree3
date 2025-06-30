"""
Zettelkasten Index Widget
=========================
A UI widget that displays a graph as a hierarchical Zettelkasten with Luhmann-style indexing.
This widget is for visualization only.
"""
import logging
from PyQt6.QtWidgets import (QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                           QHBoxLayout, QSlider, QPushButton, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QBrush

logger = logging.getLogger('ZettelkastenIndexWidget')

class ZettelkastenIndexWidget(QWidget):
    """Widget that displays a graph in a Zettelkasten tree view with Luhmann-style indexing."""
    
    def __init__(self, parent=None):
        """Initialize the widget."""
        super().__init__(parent)
        # Rename 'parent' to 'parent_window' to avoid conflict with built-in parent() method
        self.parent_window = parent  # Store the parent window reference
        self.graph = None
        self.node_items = {}  # Maps node IDs to tree items
        self.jitter_value = 0.3  # Default jitter value
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the UI components."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create control layout for slider and button
        control_layout = QHBoxLayout()
        control_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Align controls to the left
        
        # Add jitter label
        jitter_label = QLabel("Jitter:")
        control_layout.addWidget(jitter_label)
        
        # Add jitter slider with limited size
        self.jitter_slider = QSlider(Qt.Orientation.Horizontal)
        self.jitter_slider.setMinimum(0)
        self.jitter_slider.setMaximum(100)
        self.jitter_slider.setValue(int(self.jitter_value * 100))  # Set initial value
        self.jitter_slider.setToolTip("Adjust the randomness of the Zettelkasten structure")
        self.jitter_slider.valueChanged.connect(self._on_slider_changed)
        self.jitter_slider.setFixedWidth(100)  # Limit slider width
        control_layout.addWidget(self.jitter_slider)
        
        # Add jitter value label
        self.jitter_value_label = QLabel(f"{self.jitter_value:.2f}")
        self.jitter_value_label.setFixedWidth(40)  # Set fixed width for label
        control_layout.addWidget(self.jitter_value_label)
        
        # Add update button
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self._on_update_clicked)
        self.update_button.setToolTip("Recalculate the Zettelkasten structure with current jitter value")
        self.update_button.setFixedWidth(80)  # Fixed width for button
        control_layout.addWidget(self.update_button)
        
        # Add vertical separator
        separator = QLabel("|")
        separator.setStyleSheet("color: gray;")
        control_layout.addWidget(separator)
        
        # Add collapse all button
        self.collapse_button = QPushButton("Collapse")
        self.collapse_button.clicked.connect(self._on_collapse_all_clicked)
        self.collapse_button.setToolTip("Collapse all nodes in the tree")
        self.collapse_button.setFixedWidth(80)
        control_layout.addWidget(self.collapse_button)
        
        # Add expand all button
        self.expand_button = QPushButton("Expand")
        self.expand_button.clicked.connect(self._on_expand_all_clicked)
        self.expand_button.setToolTip("Expand all nodes in the tree")
        self.expand_button.setFixedWidth(80)
        control_layout.addWidget(self.expand_button)
        
        # Add stretch to push everything to the left
        control_layout.addStretch(1)
        
        # Add control layout to main layout
        main_layout.addLayout(control_layout)
        
        # Create tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Zettelkasten Index")
        self.tree.setColumnCount(1)
        self.tree.setExpandsOnDoubleClick(True)
        
        # Change selection mode to allow selection
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        
        # Connect item double clicked signal to handler
        self.tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        
        # Add tree to main layout
        main_layout.addWidget(self.tree)
        
        # Set the layout
        self.setLayout(main_layout)

    def _on_slider_changed(self, value):
        """Handle slider value changes."""
        # Convert slider value (0-100) to jitter value (0.0-1.0)
        self.jitter_value = value / 100.0
        # Update the label
        self.jitter_value_label.setText(f"{self.jitter_value:.2f}")
    
    def _on_update_clicked(self):
        """Handle update button clicks."""
        # Only update if we have a graph
        if self.graph:
            # Update the tree with the current jitter value
            self.update_tree(self.graph)
            logger.info(f"Zettelkasten tree updated with jitter value: {self.jitter_value}")

    def _on_collapse_all_clicked(self):
        """Collapse all nodes in the tree, including root nodes."""
        if not self.tree.topLevelItemCount():
            return
            
        logger.info("Collapsing all tree nodes including roots")
        self.tree.collapseAll()
        # No longer re-expanding root nodes to ensure a complete collapse
    
    def _on_expand_all_clicked(self):
        """Expand all nodes in the tree."""
        if not self.tree.topLevelItemCount():
            return
            
        logger.info("Expanding all tree nodes")
        self.tree.expandAll()

    def _on_tree_item_double_clicked(self, item, column):
        """Handle tree item double click."""
        if not hasattr(item, 'node_id'):
            return
            
        node_id = item.node_id
        logger.info(f"Opening node from Zettelkasten: {node_id}")
        
        # Use parent_window instead of parent to avoid confusion with the parent() method
        if self.parent_window and hasattr(self.parent_window, 'open_node_in_page_editor'):
            if self.parent_window.open_node_in_page_editor(node_id):
                logger.info(f"Successfully opened node {node_id}")
            else:
                logger.warning(f"Failed to open node {node_id}")
        else:
            logger.warning("Parent window doesn't have open_node_in_page_editor method")

    def update_tree(self, graph, indexer=None):
        """
        Update the tree with a new graph.
        
        Args:
            graph: NetworkX graph to display
            indexer: Optional ZettelkastenIndexCalculator instance to use for indexing
        """
        if graph is None:
            return

        self.graph = graph
        self.tree.clear()
        self.node_items = {}
        
        if not graph.nodes:
            return
            
        try:
            # If no indexer is provided, import and use the default one
            if not indexer:
                from ResearchGuidePackage.FrontendModule.zettelkasten_index_calculator import ZettelkastenIndexCalculator
                # Create calculator with current jitter value
                indexer = ZettelkastenIndexCalculator(randomness_factor=self.jitter_value)
            
            # Get indexed nodes with error handling
            try:
                indexed_nodes = indexer.calculate_indices(graph)
                
                # Verify that we got a proper index structure
                if not indexed_nodes:
                    logger.warning("Index calculator returned empty result")
                    indexed_nodes = self._create_flat_index(graph)
            except RecursionError:
                # Handle recursion error gracefully
                logger.error("RecursionError encountered when calculating indices. Graph may contain cycles.")
                # Create a flat index as fallback
                indexed_nodes = self._create_flat_index(graph)
            except Exception as e:
                logger.error(f"Error calculating indices: {e}")
                # Create a flat index as fallback
                indexed_nodes = self._create_flat_index(graph)
            
            # Create tree items for root nodes only - children will be created recursively
            root_nodes = [node_id for node_id, data in indexed_nodes.items() if data.get('is_root', False)]
            if not root_nodes:
                logger.warning("No root nodes found in index, using flat structure")
                indexed_nodes = self._create_flat_index(graph)
                root_nodes = list(indexed_nodes.keys())
                
            # Sort root nodes by index
            root_nodes.sort(key=lambda node_id: indexed_nodes[node_id].get('index', ''))
                
            # Create tree items for each root node
            for node_id in root_nodes:
                self._create_tree_item(node_id, indexed_nodes[node_id], indexed_nodes)
            
            # Expand all root nodes
            for i in range(self.tree.topLevelItemCount()):
                self.tree.topLevelItem(i).setExpanded(True)
                
                # Also expand first level of children for better visibility
                top_item = self.tree.topLevelItem(i)
                for j in range(top_item.childCount()):
                    top_item.child(j).setExpanded(True)
                    
        except Exception as e:
            logger.error(f"Error updating Zettelkasten tree: {e}")
            # Show an error message in the tree
            error_item = QTreeWidgetItem(self.tree)
            error_item.setText(0, f"Error displaying Zettelkasten: {str(e)}")
            error_item.setForeground(0, QBrush(QColor("red")))

    def _create_flat_index(self, graph):
        """Create a simple flat index as a fallback when hierarchical indexing fails."""
        result = {}
        
        # Get a sorted list of nodes
        nodes = list(graph.nodes())
        nodes.sort(key=lambda n: graph.nodes[n].get('name', str(n)))
        
        # Create a simple flat index
        for i, node in enumerate(nodes):
            result[node] = {
                'index': str(i + 1),
                'is_root': True,  # All nodes are roots in flat view
                'children': [],
                'level': 0
            }
            
        return result

    def _create_tree_item(self, node_id, node_data, indexed_nodes, parent_item=None):
        """
        Recursively create tree items for a node and its children.
        
        Args:
            node_id: ID of the node to create a tree item for
            node_data: Data about the node with indexing information
            indexed_nodes: Dictionary of all nodes with their indexing data
            parent_item: Parent tree item or None for root nodes
        """
        # Skip if node doesn't exist in graph
        if node_id not in self.graph.nodes:
            logger.warning(f"Node {node_id} not found in graph, skipping")
            return None
            
        # Get node attributes from graph
        graph_node_attrs = self.graph.nodes[node_id]
        
        # Get information for display
        index = node_data.get('index', '')
        name = graph_node_attrs.get('name', str(node_id))
        node_type = graph_node_attrs.get('node_type', 'document')
        color = graph_node_attrs.get('color', 'lightblue')
        
        # Create display text with Luhmann index
        display_text = f"{index} {name}"
        
        # Create tree item
        if parent_item is None:
            item = QTreeWidgetItem(self.tree)
        else:
            item = QTreeWidgetItem(parent_item)
        
        # Set text and store node ID
        item.setText(0, display_text)
        item.node_id = str(node_id)  # Keep for reference but not for interaction
        
        # Style based on node type
        self._style_tree_item(item, node_type, color)
        
        # Store for later reference
        self.node_items[str(node_id)] = item
        
        # Create child items recursively - get children from indexed data, not directly from graph
        children = node_data.get('children', [])
        
        # Log child count for debugging
        if len(children) > 0:
            logger.debug(f"Node {node_id} ({name}) has {len(children)} children in index")
        
        # Sort children by their indices
        sorted_children = []
        for child_id in children:
            if child_id in indexed_nodes:
                child_index = indexed_nodes[child_id].get('index', '')
                sorted_children.append((child_index, child_id))
        sorted_children.sort()  # Sort by index
        
        # Create tree items for each child
        for _, child_id in sorted_children:
            if child_id in indexed_nodes:
                # Recursively create items for this child and its descendants
                self._create_tree_item(child_id, indexed_nodes[child_id], indexed_nodes, item)
        
        return item
        
    def _style_tree_item(self, item, node_type, color):
        """Style a tree item based on node type and color."""
        # Set font based on node type
        font = QFont()
        if node_type == 'heading':
            font.setBold(True)
        elif node_type == 'concept':
            font.setItalic(True)
        item.setFont(0, font)
        
        # Set color
        try:
            item.setForeground(0, QBrush(QColor(color)))
        except Exception:
            # Default to black if color not valid
            item.setForeground(0, QBrush(QColor("black")))
