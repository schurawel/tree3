from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import logging
import asyncio
from ResearchGuidePackage.FrontendModule.mpl_canvas import MplCanvas
from ResearchGuidePackage.FrontendModule.toolbar import create_toolbar
from ResearchGuidePackage.FrontendModule.visualization_controls import VisualizationControls
import random  # Add import for random selection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GraphTab')

class GraphTab(QtWidgets.QWidget):
    """Tab for graph visualization."""
    
    # Signal to indicate the current canvas has changed
    canvas_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        """Initialize GraphTab."""
        super().__init__(parent)
        
        # Create the layout and components
        self.init_ui()
        
        # Don't initialize ANY mode until it's selected!
        logger.info("Graph tab shell initialized.")
    
    def init_ui(self):
        """Initialize the UI components."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create mode selection controls at the top
        mode_container = QtWidgets.QWidget()
        mode_layout = QtWidgets.QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(10, 10, 10, 5)
        
        # Remove Mode label - directly add dropdown
        
        # Create mode dropdown
        self.mode_dropdown = QtWidgets.QComboBox(self)
        self.mode_dropdown.addItem("Overview", "overview")
        self.mode_dropdown.addItem("Discover", "discover")
        # Set Discover as the default selected mode
        self.mode_dropdown.setCurrentIndex(1)  # Index 1 = Discover
        
        # Connect dropdown changes to action
        self.mode_dropdown.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_dropdown)
        
        # Add stretch to push everything to the left
        mode_layout.addStretch(1)
        
        # Add the mode container to the main layout
        main_layout.addWidget(mode_container)
        
        # Add a separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #cccccc;")
        separator.setFixedHeight(1)
        main_layout.addWidget(separator)
        
        # Create a stacked widget to hold different mode pages
        self.stacked_widget = QtWidgets.QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        main_layout.setStretch(2, 1)  # Give stacked widget maximum stretch
        
        # === Overview Page - Initialize Empty Shell ===
        self.overview_page = QtWidgets.QWidget()
        overview_layout = QtWidgets.QVBoxLayout(self.overview_page)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        
        # Only placeholders - no canvas or toolbar yet
        self.overview_canvas = None
        self.overview_toolbar = None
        self.overview_initialized = False
        
        self.overview_placeholder = QtWidgets.QLabel("Overview mode will initialize when selected...", self.overview_page)
        self.overview_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overview_placeholder.setStyleSheet("font-size: 14px; color: #666;")
        overview_layout.addWidget(self.overview_placeholder)
        
        # === Discover Page - Initialize Empty Shell ===
        self.discover_page = QtWidgets.QWidget()
        discover_layout = QtWidgets.QVBoxLayout(self.discover_page)
        discover_layout.setContentsMargins(0, 0, 0, 0)
        
        # Only placeholders - no canvas or toolbar yet
        self.discover_canvas = None
        self.discover_toolbar = None
        self.discover_controls = None
        self.discover_initialized = False
        
        self.discover_placeholder = QtWidgets.QLabel("Discover mode will initialize when selected...", self.discover_page)
        self.discover_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.discover_placeholder.setStyleSheet("font-size: 14px; color: #666;")
        discover_layout.addWidget(self.discover_placeholder)
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.overview_page)
        self.stacked_widget.addWidget(self.discover_page)
        
        # Default canvas reference is None until initialized
        self.canvas = None
        
        # Start with discover mode (index 1)
        self.stacked_widget.setCurrentIndex(1)
        
        logger.info("Graph tab UI shells initialized - no canvases created yet")
    
    def initialize_active_mode(self):
        """Initialize the currently active mode."""
        current_index = self.stacked_widget.currentIndex()
        if current_index == 0 and not self.overview_initialized:
            self.initialize_overview_mode()
        elif current_index == 1 and not self.discover_initialized:
            self.initialize_discover_mode()
    
    def initialize_overview_mode(self):
        """Initialize the Overview mode components."""
        if self.overview_initialized:
            return
            
        # Clear the layout
        layout = self.overview_page.layout()
        if self.overview_placeholder:
            self.overview_placeholder.hide()
            layout.removeWidget(self.overview_placeholder)
            
        # Create the overview canvas
        self.overview_canvas = MplCanvas(self.overview_page)
        
        # Create overview toolbar widget and visualization controls
        self.overview_toolbar = QtWidgets.QWidget()
        
        # Add toolbar to overview layout
        layout.addWidget(self.overview_toolbar)
        
        # Create and add visualization controls below toolbar
        if hasattr(self, 'main_window'):
            self.vis_controls = VisualizationControls(self.main_window, self.overview_canvas)
            layout.addWidget(self.vis_controls)
            
        # Add canvas at the bottom
        layout.addWidget(self.overview_canvas)
        layout.setStretch(2, 1)  # Canvas takes up all available space
        
        # Explicitly disable labels for Overview mode
        self.overview_canvas.labels_visible = False
        
        # Mark as initialized
        self.overview_initialized = True
        logger.info("Overview mode initialized with labels hidden")
        
        # Set up toolbar if main window reference exists
        if hasattr(self, 'main_window'):
            create_toolbar(self.main_window, self.overview_toolbar, self.overview_canvas)
            
        # Update canvas reference
        self.canvas = self.overview_canvas
        
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
        
        # Set up toolbar if main window reference exists
        if hasattr(self, 'main_window'):
            create_toolbar(self.main_window, self.discover_toolbar, self.discover_canvas)
            
        # Update canvas reference
        self.canvas = self.discover_canvas
        
        # Enable discover mode on the canvas with labels shown
        self.setup_discover_mode()
    
    def set_toolbar(self, main_window):
        """Set the toolbar for the graph tab."""
        self.main_window = main_window
        
        # Don't initialize any mode here!
        # Just set up the main window relationship
        
        # Set main_window.canvas reference to null initially
        # The proper canvas will be set when a mode is selected
        main_window.canvas = None
        
        # Initialize the currently active mode based on the dropdown
        # This ensures the tab initializes with the correct mode
        self.on_mode_changed(self.mode_dropdown.currentIndex())
    
    def on_mode_changed(self, index):
        """Handle mode change from dropdown."""
        mode = self.mode_dropdown.itemData(index)
        
        if mode == "overview":
            # Initialize overview mode ONLY when it's selected
            if not self.overview_initialized:
                self.initialize_overview_mode()
                
            # Switch to overview page
            self.stacked_widget.setCurrentIndex(0)
            
            # Update canvas reference
            if self.overview_initialized:
                self.canvas = self.overview_canvas
                
                # Turn off discover mode if discover canvas exists
                if self.discover_initialized and self.discover_canvas:
                    self.discover_canvas.set_discover_mode(False)
                
            # When switching to overview, ensure labels button reflects the state
            if hasattr(self, 'main_window') and self.main_window:
                self.update_labels_button()
                
        elif mode == "discover":
            # Initialize discover mode ONLY when it's selected
            if not self.discover_initialized:
                self.initialize_discover_mode()
                
            # Switch to discover page
            self.stacked_widget.setCurrentIndex(1)
            
            # Update canvas reference
            if self.discover_initialized:
                self.canvas = self.discover_canvas
                
                # Enable discover mode
                self.setup_discover_mode()
            
            # When switching to discover, ensure labels button reflects the state
            if hasattr(self, 'main_window') and self.main_window:
                self.update_labels_button()
        
        # Notify that canvas has changed if we have a main window and canvas
        if hasattr(self, 'main_window') and self.canvas:
            self.main_window.canvas = self.canvas
            self.canvas_changed.emit(self.canvas)
            
        # If there's a graph, update the visualization for the current mode
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'graph') and self.main_window.graph:
            self.update_graph(self.main_window.graph)
            
        logger.info(f"Graph visualization mode changed to: {mode}")
    
    def setup_discover_mode(self):
        """Configure discover mode when switching to it."""
        # Enable discover mode on the canvas
        if not hasattr(self, 'discover_canvas') or not hasattr(self.discover_canvas, 'graph'):
            return
        
        # Set parameters from spinners
        depth = self.depth_spinner.value()
        max_nodes = self.max_nodes_spinner.value()
        self.discover_canvas.set_explore_parameters(depth=depth, max_nodes=max_nodes)
        
        # Initialize with focus on a RANDOM node if none set yet
        if not self.discover_canvas.focus_node:
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
        if not hasattr(self, 'discover_canvas') or not hasattr(self.discover_canvas, 'graph'):
            return
            
        graph = self.discover_canvas.graph
        if not graph or not graph.nodes():
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
        # Add nodes to combo box
        for node in graph.nodes():
            label = graph.nodes[node].get('label', str(node))
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
        if hasattr(self, 'main_window') and hasattr(self.discover_canvas, 'graph'):
            graph = self.discover_canvas.graph
            if node_id in graph.nodes():
                node_data = graph.nodes[node_id]
                node_type = node_data.get('node_type', '')
                
                # If it's a page node, open it in the editor
                if node_type == 'page':
                    logger.info(f"Opening page node {node_id} in editor")
                    self.main_window.open_node_in_page_editor(node_id)
    
    def update_graph(self, graph):
        """Update the graph visualization in ONLY the active canvas."""
        if graph is None:
            return
            
        # Get current mode index
        current_index = self.stacked_widget.currentIndex()
        
        # Only initialize and update the ACTIVE mode
        if current_index == 0:  # Overview
            if not self.overview_initialized:
                self.initialize_overview_mode()
                
            if self.overview_canvas:
                self.overview_canvas.plot_graph(graph)
                logger.info("Graph updated in overview canvas")
                
        elif current_index == 1:  # Discover
            if not self.discover_initialized:
                self.initialize_discover_mode()
                
            if self.discover_canvas:
                self.discover_canvas.plot_graph(graph)
                # Set up discover mode properly
                self.setup_discover_mode()
                logger.info("Graph updated in discover canvas")
    
    def update_labels_button(self):
        """Update the show/hide labels button to match current canvas state."""
        # Find the labels toggle button in the toolbar
        if hasattr(self.main_window, 'toolbar_widget'):
            toolbar = self.overview_toolbar if self.stacked_widget.currentIndex() == 0 else self.discover_toolbar
            if toolbar and toolbar.layout():
                # Search through the operations container to find the labels button
                for i in range(toolbar.layout().count()):
                    item = toolbar.layout().itemAt(i)
                    widget = item.widget()
                    if isinstance(widget, QtWidgets.QWidget) and widget.objectName() == "operations_container":
                        ops_layout = widget.layout()
                        if ops_layout:
                            for j in range(ops_layout.count()):
                                btn = ops_layout.itemAt(j).widget()
                                if isinstance(btn, QtWidgets.QPushButton) and btn.text() in ["Show Labels", "Hide Labels"]:
                                    # Found the button, update its text and style based on the canvas state
                                    from ResearchGuidePackage.FrontendModule.toolbar import update_button_text
                                    update_button_text(btn, self.canvas.labels_visible)
                                    break
