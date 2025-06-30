"""
Bird View Tab
=============
A simplified view of the entire graph structure from a high-level perspective.
"""
import logging
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QComboBox, QCheckBox,
                            QSlider, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # Import for 3D plotting
import networkx as nx
import numpy as np
from ResearchGuidePackage.FrontendModule.mpl_canvas import MplCanvas
from ResearchGuidePackage.FrontendModule.visualization_controls import VisualizationControls

logger = logging.getLogger('BirdViewTab')

class BirdViewTab(QWidget):
    """
    A tab showing a high-level view of the entire graph structure.
    Provides a simplified "bird's eye" perspective with visualization controls.
    """
    
    def __init__(self, parent=None):
        """Initialize the Bird View tab."""
        super().__init__(parent)
        self.main_window = None
        self.canvas = None
        self.vis_controls = None
        # Set view mode defaults
        self.use_3d_view = False
        self.show_folder_labels = False
        self.show_central_labels = False
        self.central_label_threshold = 0.3  # Default threshold for centrality
        self._setup_ui()
        logger.info("Bird View tab initialized")
        
    def _setup_ui(self):
        """Set up the user interface components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== First row: Main controls =====
        control_row1 = QWidget()
        control_layout1 = QHBoxLayout(control_row1)
        control_layout1.setContentsMargins(8, 8, 8, 4)
        
        # Layout selector
        control_layout1.addWidget(QLabel("Layout:"))
        
        self.layout_combo = QComboBox()
        self.layout_combo.addItem("Spring", "spring")
        self.layout_combo.addItem("Circular", "circular")
        self.layout_combo.addItem("Shell", "shell")
        self.layout_combo.addItem("Kamada Kawai", "kamada_kawai")
        self.layout_combo.addItem("Spectral", "spectral")
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)
        self.layout_combo.setFixedWidth(120)
        control_layout1.addWidget(self.layout_combo)
        
        control_layout1.addSpacing(15)
        
        # 3D View Toggle
        self.view_3d_checkbox = QCheckBox("3D View")
        self.view_3d_checkbox.setChecked(self.use_3d_view)
        self.view_3d_checkbox.stateChanged.connect(self._on_3d_view_toggled)
        control_layout1.addWidget(self.view_3d_checkbox)
        
        control_layout1.addSpacing(15)
        
        # All Labels checkbox
        self.labels_checkbox = QCheckBox("All Labels")
        self.labels_checkbox.setChecked(False)
        self.labels_checkbox.stateChanged.connect(self._on_labels_toggled)
        control_layout1.addWidget(self.labels_checkbox)
        
        # Add stretch to push remaining controls to the right
        control_layout1.addStretch(1)
        
        # Refresh button 
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setToolTip("Refresh the graph view")
        refresh_btn.clicked.connect(self.refresh)
        control_layout1.addWidget(refresh_btn)
        
        main_layout.addWidget(control_row1)
        
        # ===== Second row: Label controls =====
        control_row2 = QWidget()
        control_layout2 = QHBoxLayout(control_row2)
        control_layout2.setContentsMargins(8, 4, 8, 8)
        
        # Folder Labels checkbox
        self.folder_labels_checkbox = QCheckBox("Folder Labels")
        self.folder_labels_checkbox.setChecked(self.show_folder_labels)
        self.folder_labels_checkbox.stateChanged.connect(self._on_folder_labels_toggled)
        control_layout2.addWidget(self.folder_labels_checkbox)
        
        control_layout2.addSpacing(10)
        
        # Central Node Labels checkbox
        self.central_labels_checkbox = QCheckBox("Central Node Labels")
        self.central_labels_checkbox.setChecked(self.show_central_labels)
        self.central_labels_checkbox.stateChanged.connect(self._on_central_labels_toggled)
        control_layout2.addWidget(self.central_labels_checkbox)
        
        control_layout2.addSpacing(10)
        
        # Centrality threshold slider with label
        control_layout2.addWidget(QLabel("Centrality:"))
        
        self.central_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.central_threshold_slider.setRange(0, 100)
        self.central_threshold_slider.setValue(int(self.central_label_threshold * 100))
        self.central_threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.central_threshold_slider.setTickInterval(25)
        self.central_threshold_slider.valueChanged.connect(self._on_central_threshold_changed)
        self.central_threshold_slider.setFixedWidth(120)  # Limit slider width
        control_layout2.addWidget(self.central_threshold_slider)
        
        self.threshold_value_label = QLabel(f"{self.central_label_threshold:.2f}")
        self.threshold_value_label.setFixedWidth(40)  # Fixed width for the value label
        control_layout2.addWidget(self.threshold_value_label)
        
        # Add stretch to push everything to the left
        control_layout2.addStretch(1)
        
        main_layout.addWidget(control_row2)
        
        # Add separator line
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #cccccc;")
        main_layout.addWidget(separator)
        
        # Create the canvas for graph visualization
        self.canvas = MplCanvas(self)
        self.canvas.labels_visible = False  # Start with labels disabled
        
        # Create the visualization controls (node type filtering, stickiness)
        # This will be instantiated when set_main_window is called
        self.vis_controls_container = QWidget()
        self.vis_controls_layout = QHBoxLayout(self.vis_controls_container)
        self.vis_controls_layout.setContentsMargins(5, 5, 5, 5)
        
        # Set up matplotlib toolbar
        self.mpl_toolbar = NavigationToolbar2QT(self.canvas, self)
        
        # Add UI elements in correct order
        main_layout.addWidget(self.vis_controls_container)  # Visualization controls
        main_layout.addWidget(self.mpl_toolbar)  # MatplotLib toolbar
        main_layout.addWidget(self.canvas, 1)  # Canvas gets all remaining space
        
    def set_main_window(self, main_window):
        """Set the main window reference and initialize visualization controls."""
        self.main_window = main_window
        
        # Now we can create the visualization controls with the main_window reference
        self.vis_controls = VisualizationControls(self.main_window, self.canvas)
        
        # Clear any existing items from the vis_controls_layout
        while self.vis_controls_layout.count():
            item = self.vis_controls_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Add the visualization controls to the container
        self.vis_controls_layout.addWidget(self.vis_controls)
        
        # Set up canvas specific properties for this view
        self.canvas.node_type_colors = {
            'page': '#4CAF50',      # Green
            'text_block': '#2196F3', # Blue
            'source': '#FF9800',     # Orange
            'concept': '#9C27B0',    # Purple
            'person': '#E91E63',     # Pink
            'document': '#607D8B',   # Blue-Gray
            'file': '#795548',       # Brown
            'task': '#F44336'        # Red
        }
        
        # Update the graph if available
        if main_window and hasattr(main_window, 'graph'):
            self.refresh()
        
    def _on_layout_changed(self, index):
        """Handle layout algorithm change."""
        layout_algo = self.layout_combo.currentData()
        logger.info(f"Changing layout to: {layout_algo}")
        self.refresh()
        
    def _on_labels_toggled(self, state):
        """Handle labels checkbox toggle."""
        show_labels = (state == Qt.CheckState.Checked)
        if self.canvas:
            self.canvas.labels_visible = show_labels
            logger.info(f"All labels visibility set to: {show_labels}")
            self.refresh()
    
    def _on_folder_labels_toggled(self, state):
        """Handle folder labels checkbox toggle."""
        self.show_folder_labels = (state == Qt.CheckState.Checked)
        logger.info(f"Folder labels visibility set to: {self.show_folder_labels}")
        self.refresh()
    
    def _on_central_labels_toggled(self, state):
        """Handle central node labels checkbox toggle."""
        self.show_central_labels = (state == Qt.CheckState.Checked)
        logger.info(f"Central node labels visibility set to: {self.show_central_labels}")
        self.refresh()
    
    def _on_central_threshold_changed(self, value):
        """Handle central node threshold slider change."""
        self.central_label_threshold = value / 100.0
        self.threshold_value_label.setText(f"{self.central_label_threshold:.2f}")
        if self.show_central_labels:
            self.refresh()
    
    def _on_3d_view_toggled(self, state):
        """Handle 3D view checkbox toggle."""
        self.use_3d_view = (state == Qt.CheckState.Checked)
        logger.info(f"3D view toggled to: {self.use_3d_view}")
        
        # Update layout combobox to disable unsupported layouts
        if self.use_3d_view:
            # Store current layout
            current_layout = self.layout_combo.currentData()
            
            # Force a compatible layout
            if current_layout in ["circular", "shell"]:
                # Switch to spring layout as it works best for 3D
                spring_index = self.layout_combo.findData("spring")
                if spring_index >= 0:
                    logger.info("Switching to spring layout for 3D view")
                    self.layout_combo.setCurrentIndex(spring_index)
        
        # Force recreation of the entire plot
        self.refresh()
        
    def refresh(self):
        """Refresh the graph visualization."""
        if not self.main_window or not hasattr(self.main_window, 'graph') or not self.main_window.graph:
            logger.warning("No graph available to visualize")
            return
            
        try:
            graph = self.main_window.graph
            self._render_graph(graph)
        except Exception as e:
            logger.error(f"Error refreshing graph: {e}", exc_info=True)
            
    def _render_graph(self, graph):
        """Render the graph using the selected layout algorithm."""
        if not graph or not self.canvas:
            return
            
        # Clear the canvas
        self.canvas.figure.clear()
        
        # Get the layout algorithm
        layout_algo = self.layout_combo.currentData()
        
        # For 3D view, force using a compatible layout algorithm
        if self.use_3d_view and layout_algo in ["circular", "shell"]:
            layout_algo = "spring"
            logger.info(f"Changed to spring layout for 3D view")
        
        # Set up the plot - 3D if enabled, or regular 2D
        if self.use_3d_view:
            # Create 3D axes properly
            logger.info("Creating 3D subplot")
            ax = self.canvas.figure.add_subplot(111, projection='3d')
            # Ensure the backend recognizes it's 3D
            self.canvas.figure.subplots_adjust(top=0.9, bottom=0.1, right=0.9, left=0.1)
        else:
            ax = self.canvas.figure.add_subplot(111)
        
        # Filter nodes based on visualization controls (if available)
        visible_node_types = None
        if hasattr(self.canvas, 'node_type_visibility'):
            visible_node_types = {nt for nt, visible in self.canvas.node_type_visibility.items() if visible}
        
        visible_nodes = []
        node_colors = []
        node_sizes = []
        node_labels = {}
        node_types = {}
        
        for node in graph.nodes():
            node_data = graph.nodes[node]
            node_type = node_data.get('node_type', 'unknown')
            
            # Skip nodes that aren't visible based on type filtering
            if visible_node_types is not None and node_type not in visible_node_types:
                continue
                
            visible_nodes.append(node)
            node_types[node] = node_type
            
            # Assign colors based on node type
            if node_type in self.canvas.node_type_colors:
                node_colors.append(self.canvas.node_type_colors[node_type])
            else:
                node_colors.append('#9E9E9E')  # Grey for unknown types
                
            # Assign sizes
            if node_type == 'page':
                node_sizes.append(100)
            elif node_type == 'text_block':
                node_sizes.append(50)
            elif node_type == 'source':
                node_sizes.append(80)
            else:
                node_sizes.append(70)
        
        # Create a subgraph with only the visible nodes
        subgraph = graph.subgraph(visible_nodes) if visible_nodes else graph
        
        # Create the layout positions - 3D or 2D as needed
        try:
            if self.use_3d_view:
                # Force 3D layout
                logger.info(f"Creating 3D layout with {layout_algo} algorithm")
                pos = self._create_3d_layout(subgraph, layout_algo)
            else:
                # Regular 2D layout
                if layout_algo == "spring":
                    pos = nx.spring_layout(subgraph)
                elif layout_algo == "circular":
                    pos = nx.circular_layout(subgraph)
                elif layout_algo == "shell":
                    pos = nx.shell_layout(subgraph)
                elif layout_algo == "kamada_kawai":
                    pos = nx.kamada_kawai_layout(subgraph)
                elif layout_algo == "spectral":
                    pos = nx.spectral_layout(subgraph)
                else:
                    pos = nx.spring_layout(subgraph)  # Default to spring layout
        except Exception as e:
            logger.error(f"Error creating layout: {e}", exc_info=True)
            # Fallback layouts with error handling
            if self.use_3d_view:
                logger.info("Using fallback random 3D layout after error")
                pos = self._create_random_3d_layout(subgraph)
            else:
                pos = nx.random_layout(subgraph)  # Fallback to random
        
        # Draw the graph - only if we have nodes
        if visible_nodes:
            if self.use_3d_view:
                # Only use the 3D drawing function when in 3D mode
                logger.info("Drawing 3D graph")
                self._draw_3d_graph(ax, subgraph, pos, node_colors, node_sizes)
            else:
                self._draw_2d_graph(ax, subgraph, pos, node_colors, node_sizes)
            
            # Handle label visibility based on settings
            if self.canvas.labels_visible:
                # All labels are visible
                for node in subgraph.nodes():
                    node_data = graph.nodes[node]
                    label = node_data.get('title', node_data.get('name', node_data.get('label', str(node)[:8])))
                    node_labels[node] = label
            else:
                # Selective label visibility
                if self.show_folder_labels or self.show_central_labels:
                    # Process folder nodes if requested
                    if self.show_folder_labels:
                        folder_nodes = self._identify_folder_nodes(subgraph)
                        for node in folder_nodes:
                            if node in subgraph:
                                node_data = graph.nodes[node]
                                label = node_data.get('title', node_data.get('name', node_data.get('label', str(node)[:8])))
                                node_labels[node] = label
                    
                    # Process central nodes if requested
                    if self.show_central_labels:
                        central_nodes = self._identify_central_nodes(subgraph, self.central_label_threshold)
                        for node in central_nodes:
                            if node in subgraph:
                                node_data = graph.nodes[node]
                                label = node_data.get('title', node_data.get('name', node_data.get('label', str(node)[:8])))
                                node_labels[node] = label
            
            # Draw labels if we have any to show
            if node_labels:
                if self.use_3d_view:
                    self._draw_3d_labels(ax, pos, node_labels)
                else:
                    nx.draw_networkx_labels(subgraph, pos, labels=node_labels, font_size=8, 
                                          font_color='black', ax=ax)
            
            # Adjust appearance specific to 3D view
            if self.use_3d_view:
                ax.set_title("3D Network Visualization", pad=20)
                # Set better angle for 3D viewing
                ax.view_init(elev=25, azim=45)  # More pronounced angle to see 3D effect
                
                # Make 3D plot more distinctive
                ax.grid(True)
                ax.xaxis.pane.fill = False
                ax.yaxis.pane.fill = False
                ax.zaxis.pane.fill = False
                
                # Don't use tight_layout for 3D plots - can cause issues
                self.canvas.figure.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
                
                # Set axis visibility
                ax.set_axis_on()
                
                logger.info("3D view configuration complete")
            else:
                # 2D mode - turn off axis
                ax.set_axis_off()
        else:
            ax.text(0.5, 0.5, "No nodes match the current filters",
                    horizontalalignment='center', verticalalignment='center')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_axis_off()
        
        # Update the canvas
        self.canvas.draw()
        logger.info(f"Graph rendered with {layout_algo} layout ({len(visible_nodes)} nodes), 3D: {self.use_3d_view}")

    def _create_3d_layout(self, graph, layout_algo):
        """Create a 3D layout for the graph."""
        try:
            # Start with 2D positions from networkx
            if layout_algo == "spring":
                pos_2d = nx.spring_layout(graph, dim=2)
            elif layout_algo == "kamada_kawai":
                pos_2d = nx.kamada_kawai_layout(graph, dim=2)
            elif layout_algo == "spectral":
                pos_2d = nx.spectral_layout(graph, dim=2)
            else:
                # Default to spring for 3D
                pos_2d = nx.spring_layout(graph, dim=2)
            
            # Add Z coordinate based on centrality or some other metric
            pos_3d = {}
            
            # Calculate centrality metrics to use for Z axis
            centrality = nx.degree_centrality(graph)
            
            for node in graph.nodes():
                # Get 2D position
                if node in pos_2d:
                    x, y = pos_2d[node]
                    
                    # Use scaled centrality for z-coordinate to increase visibility of 3D effect
                    z = centrality.get(node, 0.1) * 1.5
                    
                    # Ensure the z value is distinct enough to see in 3D
                    if z < 0.1:
                        z = 0.1
                        
                    pos_3d[node] = np.array([x, y, z])
                else:
                    # Fallback if node not in pos_2d
                    pos_3d[node] = np.array([0, 0, 0.1])  # Default z value
            
            logger.info(f"Created 3D layout with {len(pos_3d)} nodes")
            return pos_3d
            
        except Exception as e:
            logger.error(f"Error in 3D layout creation: {e}", exc_info=True)
            return self._create_random_3d_layout(graph)  # Fall back to random 3D

    def _create_random_3d_layout(self, graph):
        """Create a random 3D layout."""
        pos_3d = {}
        for node in graph.nodes():
            pos_3d[node] = np.array([
                np.random.random(),
                np.random.random(),
                np.random.random()
            ])
        return pos_3d

    def _draw_2d_graph(self, ax, graph, pos, node_colors, node_sizes):
        """Draw the graph in 2D."""
        nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=node_colors, 
                              node_size=node_sizes, alpha=0.8)
        nx.draw_networkx_edges(graph, pos, ax=ax, width=0.5, alpha=0.5, 
                              edge_color='#cccccc', arrows=True, arrowsize=5)

    def _draw_3d_graph(self, ax, graph, pos_3d, node_colors, node_sizes):
        """Draw the graph in 3D."""
        try:
            # Extract node positions
            xs = []
            ys = []
            zs = []
            colors = []
            sizes = []
            
            for i, node in enumerate(graph.nodes()):
                if node in pos_3d:
                    x, y, z = pos_3d[node]
                    xs.append(x)
                    ys.append(y)
                    zs.append(z)
                    
                    # Ensure proper colors and sizes
                    if i < len(node_colors):
                        colors.append(node_colors[i])
                    else:
                        colors.append('#888888')  # Default gray
                        
                    if i < len(node_sizes):
                        # Make nodes larger in 3D view for better visibility
                        sizes.append(node_sizes[i]/3)
                    else:
                        sizes.append(15)  # Default size
            
            # Draw nodes as 3D scatter plot with enhanced visual settings
            scatter = ax.scatter(
                xs, ys, zs, 
                c=colors, 
                s=sizes, 
                alpha=0.9, 
                depthshade=True,
                edgecolors='white',
                linewidths=0.5
            )
            
            # Draw edges as 3D lines with improved visibility
            for u, v in graph.edges():
                if u in pos_3d and v in pos_3d:
                    x = [pos_3d[u][0], pos_3d[v][0]]
                    y = [pos_3d[u][1], pos_3d[v][1]]
                    z = [pos_3d[u][2], pos_3d[v][2]]
                    ax.plot(x, y, z, c='#888888', alpha=0.6, linewidth=0.7)
            
            # Set better aspect ratio and labels
            ax.set_box_aspect([1, 1, 0.7])  # Slightly squash z-axis for better visibility
            
            # Add axis labels
            ax.set_xlabel('X', fontsize=10, labelpad=10)
            ax.set_ylabel('Y', fontsize=10, labelpad=10)
            ax.set_zlabel('Z (Centrality)', fontsize=10, labelpad=10)
            
            # Set visible grid lines for depth perception
            ax.grid(True)
            
            # Make tick labels smaller for better fit
            ax.tick_params(axis='both', which='major', labelsize=8)
            
            logger.info("3D graph drawn successfully")
        except Exception as e:
            logger.error(f"Error drawing 3D graph: {e}", exc_info=True)
            # Add error message to the plot
            ax.text(0, 0, 0.5, f"Error drawing 3D graph: {str(e)}", color='red')

    def _draw_3d_labels(self, ax, pos_3d, node_labels):
        """Draw node labels in 3D."""
        for node, label in node_labels.items():
            if node in pos_3d:
                x, y, z = pos_3d[node]
                ax.text(x, y, z, label, size=8, zorder=1)

    def _identify_folder_nodes(self, graph):
        """Identify nodes that represent folders or categories."""
        folder_nodes = []
        
        # Check graph for folder nodes based on node type or other attributes
        for node, data in graph.nodes(data=True):
            # Check if node has 'node_type' or other attributes suggesting it's a folder
            if data.get('node_type') == 'namespace' or data.get('is_folder', False):
                folder_nodes.append(node)
            # Check if node has many outgoing connections (likely a folder/namespace)
            elif graph.out_degree(node) > 5:
                folder_nodes.append(node)
            # Check for namespace attribute
            elif 'namespace' in data or 'namespaces' in data:
                folder_nodes.append(node)
            # Check node name/label for folder-like patterns
            elif any(folder_keyword in str(data.get('name', '')).lower() or 
                    folder_keyword in str(data.get('label', '')).lower() or
                    folder_keyword in str(data.get('title', '')).lower()
                    for folder_keyword in ['folder', 'category', 'namespace', 'group', 'collection']):
                folder_nodes.append(node)
        
        return folder_nodes

    def _identify_central_nodes(self, graph, threshold):
        """Identify central nodes in the graph based on centrality metrics."""
        central_nodes = []
        
        # Calculate various centrality metrics
        degree_centrality = nx.degree_centrality(graph)
        
        # Use other centrality metrics if the graph is not too large
        betweenness_centrality = {}
        if len(graph) <= 500:  # Only for smaller graphs due to computational cost
            try:
                betweenness_centrality = nx.betweenness_centrality(graph)
            except Exception as e:
                logger.warning(f"Error calculating betweenness centrality: {e}")
        
        # Combine centrality scores (weighted average)
        combined_centrality = {}
        for node in graph.nodes():
            degree_score = degree_centrality.get(node, 0)
            betweenness_score = betweenness_centrality.get(node, 0)
            
            # If we have betweenness, use weighted average
            if betweenness_centrality:
                combined_centrality[node] = 0.6 * degree_score + 0.4 * betweenness_score
            else:
                combined_centrality[node] = degree_score
        
        # Find nodes above threshold
        for node, score in combined_centrality.items():
            if score >= threshold:
                central_nodes.append(node)
        
        # If threshold resulted in no central nodes, take top 3 nodes
        if not central_nodes and graph.nodes():
            top_nodes = sorted(combined_centrality.items(), key=lambda x: x[1], reverse=True)
            central_nodes = [node for node, _ in top_nodes[:3]]
        
        return central_nodes

    def get_tab_title(self):
        """Return the title for this tab."""
        return "Bird View"
