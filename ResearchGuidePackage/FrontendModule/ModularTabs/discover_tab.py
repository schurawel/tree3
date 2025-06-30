from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import logging
import asyncio
from ResearchGuidePackage.FrontendModule.mpl_canvas import MplCanvas
from ResearchGuidePackage.FrontendModule.toolbar import create_toolbar
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GraphTab')

class GraphTab(QtWidgets.QWidget):
    """Tab for graph visualization in discover mode."""
    
    # Signal to indicate the current canvas has changed
    canvas_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        """Initialize GraphTab."""
        super().__init__(parent)
        self.parent_widget = parent
        self.main_window = None
        
        # Add a stored graph reference to prevent losing it when main_window.canvas changes
        self.stored_graph = None
        
        # Create the layout and components
        self.init_ui()
        
        # Initialize discover mode immediately
        self.initialize_discover_mode()
        
        logger.info("GraphTab initialized with discover mode.")
    
    def init_ui(self):
        """Initialize the UI components."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the discover page
        self.discover_page = QtWidgets.QWidget()
        discover_layout = QtWidgets.QVBoxLayout(self.discover_page)
        discover_layout.setContentsMargins(0, 0, 0, 0)
        
        # Initialize variables for discover mode
        self.discover_canvas = None
        self.discover_toolbar = None
        self.discover_controls = None
        self.discover_initialized = False
        
        # Add discover page placeholder (will be replaced when initialized)
        self.discover_placeholder = QtWidgets.QLabel("Initializing discover mode...", self.discover_page)
        self.discover_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.discover_placeholder.setStyleSheet("font-size: 14px; color: #666;")
        discover_layout.addWidget(self.discover_placeholder)
        
        # Add discover page to main layout
        main_layout.addWidget(self.discover_page)
        
        # Default canvas reference is None until initialized
        self.canvas = None
        
        logger.info("GraphTab UI shell initialized")
    
    def initialize_discover_mode(self):
        """Initialize the Discover mode components."""
        if self.discover_initialized:
            return
            
        # Clear the layout
        layout = self.discover_page.layout()
        if self.discover_placeholder:
            self.discover_placeholder.hide()
            layout.removeWidget(self.discover_placeholder)
            
        # Create discover canvas and toolbar
        self.discover_canvas = MplCanvas(self.discover_page)
        self.discover_toolbar = QtWidgets.QWidget()
        
        # Create discover controls
        self.discover_controls = QtWidgets.QWidget()
        controls_layout = QtWidgets.QHBoxLayout(self.discover_controls)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        
        # Add depth control
        depth_label = QtWidgets.QLabel("Exploration Depth:")
        controls_layout.addWidget(depth_label)
        
        self.depth_spinner = QtWidgets.QSpinBox()
        self.depth_spinner.setRange(1, 5)
        self.depth_spinner.setValue(2)  # Default depth
        self.depth_spinner.setToolTip("How many connection hops to explore")
        self.depth_spinner.valueChanged.connect(self.on_depth_changed)
        controls_layout.addWidget(self.depth_spinner)
        
        # Add max nodes control
        max_nodes_label = QtWidgets.QLabel("Max Nodes:")
        controls_layout.addWidget(max_nodes_label)
        
        self.max_nodes_spinner = QtWidgets.QSpinBox()
        self.max_nodes_spinner.setRange(5, 50)
        self.max_nodes_spinner.setValue(20)  # Default max nodes
        self.max_nodes_spinner.setToolTip("Maximum number of nodes to display")
        self.max_nodes_spinner.valueChanged.connect(self.on_max_nodes_changed)
        controls_layout.addWidget(self.max_nodes_spinner)
        
        # Add node selection button
        self.select_node_button = QtWidgets.QPushButton("Select Focus Node")
        self.select_node_button.clicked.connect(self.select_focus_node)
        controls_layout.addWidget(self.select_node_button)
        
        # Add reset button
        self.reset_button = QtWidgets.QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_discover)
        controls_layout.addWidget(self.reset_button)
        
        controls_layout.addStretch(1)  # Push everything to the left
        
        # Add components to layout
        layout.addWidget(self.discover_controls)
        layout.addWidget(self.discover_toolbar)
        layout.addWidget(self.discover_canvas)
        layout.setStretch(2, 1)  # Canvas takes maximum space
        
        # Explicitly enable labels for Discover mode
        self.discover_canvas.labels_visible = True
        
        # Enable discover mode flag in canvas
        self.discover_canvas.discover_mode = True
        
        # Mark as initialized
        self.discover_initialized = True
        logger.info("Discover mode initialized with labels visible")
        
        # Set canvas reference 
        self.canvas = self.discover_canvas
        
        # Flag to track if this tab has been replaced during a rebuild
        self.being_replaced = False
        
        # Update canvas reference in main window if it exists
        if hasattr(self, 'main_window') and self.main_window:
            # Don't overwrite main_window.canvas - just emit signal
            # self.main_window.canvas = self.discover_canvas
            self.canvas_changed.emit(self.discover_canvas)
            
            # Load the graph if main window has one
            if hasattr(self.main_window, 'graph') and self.main_window.graph:
                self.update_graph(self.main_window.graph)
    
    def set_toolbar(self, main_window):
        """Set the toolbar for the graph tab."""
        self.main_window = main_window
        
        # Set up toolbar if main window reference exists
        if self.main_window and self.discover_initialized:
            create_toolbar(self.main_window, self.discover_toolbar, self.discover_canvas)
            
            # NO LONGER update main window canvas reference - this can cause conflicts
            # self.main_window.canvas = self.discover_canvas
            self.canvas_changed.emit(self.discover_canvas)
            
            # If there's a graph, update the visualization
            if hasattr(self.main_window, 'graph') and self.main_window.graph:
                self.update_graph(self.main_window.graph)
    
    def setup_discover_mode(self):
        """Configure discover mode settings."""
        # Set parameters from spinners
        depth = self.depth_spinner.value()
        max_nodes = self.max_nodes_spinner.value()
        
        if not hasattr(self, 'discover_canvas') or not self.discover_canvas:
            return
            
        self.discover_canvas.set_explore_parameters(depth=depth, max_nodes=max_nodes)
        
        # Initialize with focus on a RANDOM node if none set yet
        if not hasattr(self.discover_canvas, 'focus_node') or not self.discover_canvas.focus_node:
            if hasattr(self.discover_canvas, 'graph') and self.discover_canvas.graph:
                nodes = list(self.discover_canvas.graph.nodes())
                if nodes:
                    # Choose a random node
                    focus_node = random.choice(nodes)
                    self.discover_canvas.set_discover_mode(True, focus_node=focus_node)
                    logger.info(f"Randomly selected focus node: {focus_node}")
                    
                    # Check if it's a page node and open it in the editor
                    self.open_page_if_applicable(focus_node)
    
    def on_depth_changed(self, value):
        """Handle depth spinner change."""
        if hasattr(self, 'discover_canvas'):
            self.discover_canvas.set_explore_parameters(depth=value)
    
    def on_max_nodes_changed(self, value):
        """Handle max nodes spinner change."""
        if hasattr(self, 'discover_canvas'):
            self.discover_canvas.set_explore_parameters(max_nodes=value)
    
    def select_focus_node(self):
        """Open dialog to select a focus node."""
        if not hasattr(self, 'discover_canvas') or not self.discover_canvas:
            return
        
        if not hasattr(self.discover_canvas, 'graph') or not self.discover_canvas.graph:
            QtWidgets.QMessageBox.information(self, "Info", "No graph available.")
            return
            
        graph = self.discover_canvas.graph
        if not graph.nodes():
            QtWidgets.QMessageBox.information(self, "Info", "No nodes available to select.")
            return
        
        # Create a dialog with a dropdown of nodes
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Select Focus Node")
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Add node selection dropdown
        node_label = QtWidgets.QLabel("Select a node to focus on:")
        layout.addWidget(node_label)
        
        node_combo = QtWidgets.QComboBox()
        # Add nodes to combo box - sort by label for better usability
        nodes_with_labels = []
        for node in graph.nodes():
            label = graph.nodes[node].get('title', 
                   graph.nodes[node].get('name',
                   graph.nodes[node].get('label', str(node))))
            nodes_with_labels.append((label, node))
        
        # Sort by label
        nodes_with_labels.sort()
        
        # Add nodes to combo box
        for label, node in nodes_with_labels:
            node_combo.addItem(label, node)
        layout.addWidget(node_combo)
        
        # Add buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Show dialog
        if dialog.exec():
            selected_node = node_combo.currentData()
            if selected_node:
                self.discover_canvas.set_discover_mode(True, focus_node=selected_node)
                logger.info(f"Focus set to node: {selected_node}")
                
                # Check if it's a page node and open it in the editor
                self.open_page_if_applicable(selected_node)
    
    def reset_discover(self):
        """Reset discover mode to default settings."""
        if hasattr(self, 'discover_canvas'):
            # Reset spinners
            self.depth_spinner.setValue(2)
            self.max_nodes_spinner.setValue(20)
            
            # Reset parameters
            self.discover_canvas.set_explore_parameters(depth=2, max_nodes=20)
            
            # Select a RANDOM focus node
            if hasattr(self.discover_canvas, 'graph') and self.discover_canvas.graph:
                nodes = list(self.discover_canvas.graph.nodes())
                if nodes:
                    # Choose a random node
                    focus_node = random.choice(nodes)
                    self.discover_canvas.set_discover_mode(True, focus_node=focus_node)
                    logger.info(f"Randomly selected focus node on reset: {focus_node}")
                    
                    # Check if it's a page node and open it in the editor
                    self.open_page_if_applicable(focus_node)
    
    def open_page_if_applicable(self, node_id):
        """Open node in page editor if it's a page node."""
        # Use stored graph instead of discover_canvas.graph for stability
        graph = self.stored_graph if self.stored_graph else (
            self.discover_canvas.graph if hasattr(self.discover_canvas, 'graph') else None
        )
        
        if hasattr(self, 'main_window') and graph:
            if node_id in graph.nodes():
                node_data = graph.nodes[node_id]
                node_type = node_data.get('node_type', '')
                
                # If it's a page node, open it in the editor
                if node_type == 'page':
                    logger.info(f"Opening page node {node_id} in editor")
                    self.main_window.open_node_in_page_editor(node_id)
    
    def update_graph(self, graph):
        """Update the graph visualization."""
        if graph is None:
            logger.warning("Attempted to update with null graph")
            return
            
        # Skip if this tab is being replaced
        if hasattr(self, 'being_replaced') and self.being_replaced:
            logger.info("Skipping graph update for tab being replaced")
            return
            
        logger.info("Updating graph in discover view")
        
        # Store our own copy of the graph to maintain independence
        try:
            self.stored_graph = graph.copy()  # Explicitly make a copy
        except Exception as e:
            logger.error(f"Error copying graph: {e}")
            self.stored_graph = graph  # Fallback to direct reference
        
        # Initialize discover mode if not already done
        if not self.discover_initialized:
            self.initialize_discover_mode()
                
        if self.discover_canvas:
            # Use our stored graph to avoid reference issues
            self.discover_canvas.plot_graph(self.stored_graph)
            self.setup_discover_mode()
            logger.info("Graph updated in discover canvas")

    # Add method to preserve discovery state during rebuild
    def get_state_for_rebuild(self):
        """Get state information needed to recreate this tab during rebuild."""
        state = {
            "focus_node": None,
            "explore_depth": self.depth_spinner.value() if hasattr(self, 'depth_spinner') else 2,
            "max_nodes": self.max_nodes_spinner.value() if hasattr(self, 'max_nodes_spinner') else 20
        }
        
        # Get focus node from canvas
        if hasattr(self, 'discover_canvas') and self.discover_canvas:
            if hasattr(self.discover_canvas, 'focus_node'):
                state["focus_node"] = self.discover_canvas.focus_node
        
        logger.info(f"Preserving discover tab state: focus={state['focus_node']}")
        return state
        
    def restore_state_from_rebuild(self, state):
        """Restore state after a tab rebuild."""
        if not state:
            return
            
        if 'explore_depth' in state and hasattr(self, 'depth_spinner'):
            self.depth_spinner.setValue(state['explore_depth'])
            
        if 'max_nodes' in state and hasattr(self, 'max_nodes_spinner'):
            self.max_nodes_spinner.setValue(state['max_nodes'])
            
        # Apply focus node
        focus_node = state.get('focus_node')
        if focus_node and hasattr(self, 'discover_canvas') and self.discover_canvas:
            self.discover_canvas.focus_node = focus_node
            
        # Explicitly refresh the graph with latest stored state
        if hasattr(self, 'stored_graph') and self.stored_graph:
            logger.info(f"Restoring discover tab with focus={focus_node}")
            self.discover_canvas.plot_graph(self.stored_graph)
            self.setup_discover_mode()
    
    def get_tab_title(self):
        """Get title for the tab."""
        return "Discover"
        
    def refresh(self):
        """Refresh the graph view."""
        # First check our stored graph, use it if available
        if self.stored_graph:
            self.update_graph(self.stored_graph)
            logger.info("Refreshed graph view from stored graph")
        # Fall back to main window's graph if stored graph is not available
        elif hasattr(self, 'main_window') and hasattr(self.main_window, 'graph'):
            self.update_graph(self.main_window.graph)
            logger.info("Refreshed graph view from main_window graph")
