import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import networkx as nx
import logging
import asyncio
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QTimer
from ResearchGuidePackage.FrontendModule.link_handler import show_node_info
from ResearchGuidePackage.FrontendModule.client import APIClient
import matplotlib.patches as mpatches

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class MplCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas for visualization."""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """Initialize canvas with figure."""
        # Create figure and axis
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        # Set parent
        self.setParent(parent)
        # Set attributes
        self.setMinimumSize(100, 100)
        self.fig.tight_layout()
        # Initialize attributes for graph visualization
        self.node_positions = {}
        self.node_labels = {}
        self.labels_visible = False  # Initially labels are hidden
        self.node_colors = {}
        self.selected_node = None
        # Enable clicking on nodes - fix the method name to match what's implemented
        self.mpl_connect('button_press_event', self.on_node_click)  # Changed from on_click to on_node_click
        
        # Communication with backend
        self.communication = APIClient()
        
        # Node type color cache to avoid repeated backend requests
        self.node_type_colors = {}
        
        # Node type visibility tracking - empty set means all visible initially
        self.visible_node_types = set()
        
        # Text block stickiness to pages (0.0 to 1.0, higher = stickier)
        self.text_block_stickiness = 0.5  # Default mid-range stickiness
        
        # Add discover mode properties
        self.discover_mode = False
        self.focus_node = None
        self.explore_depth = 2  # Default exploration depth
        self.max_nodes = 20     # Default max nodes to show in discover mode
        
        # Add click handling attributes
        self.last_click_time = 0
        self.last_clicked_node = None
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.handle_single_click)
        self.double_click_interval = 400  # milliseconds
        
        logging.info("MplCanvas initialized.")
        
    async def fetch_node_type_colors(self):
        """Fetch node type colors from backend."""
        try:
            success, content, error = await self.communication.request_and_get_response(
                operation="get_node_types",
                params={},
                sender="Frontend"
            )
            
            if success and content and "result" in content:
                node_types = content["result"]
                # Cache the colors for each node type
                for type_id, type_data in node_types.items():
                    self.node_type_colors[type_id] = type_data.get("color", "skyblue")
                logging.info(f"Fetched colors for {len(self.node_type_colors)} node types")
                
                # Initialize visible_node_types with all available types
                self.visible_node_types = set(self.node_type_colors.keys())
            else:
                logging.error(f"Error fetching node types: {error}")
        except Exception as e:
            logging.error(f"Error in fetch_node_type_colors: {e}")
    
    def get_node_color(self, node_data):
        """Get color for a node based on its type, using cached colors."""
        # Try to get node type
        node_type = node_data.get('node_type', 'document')
        
        # If we have this type in cache, use its color as default
        if node_type in self.node_type_colors:
            default_color = self.node_type_colors[node_type]
        else:
            default_color = 'skyblue'  # Default fallback
            
        # Use node's own color if specified, otherwise use type default
        return node_data.get('color', default_color)

    def set_node_type_visibility(self, node_type, visible):
        """Set visibility for a specific node type."""
        if visible and node_type not in self.visible_node_types:
            self.visible_node_types.add(node_type)
            logging.info(f"Made node type '{node_type}' visible")
        elif not visible and node_type in self.visible_node_types:
            self.visible_node_types.remove(node_type)
            logging.info(f"Made node type '{node_type}' hidden")
            
        # Redraw the graph with new visibility settings
        if hasattr(self, 'graph'):
            self.plot_graph(self.graph)
            
    def toggle_node_type_visibility(self, node_type):
        """Toggle visibility of a specific node type."""
        is_visible = node_type in self.visible_node_types
        self.set_node_type_visibility(node_type, not is_visible)
        return not is_visible  # Return new state
    
    def set_all_node_types_visible(self, visible=True):
        """Make all node types visible or hidden."""
        if visible:
            # Add all known node types to visible set
            self.visible_node_types = set(self.node_type_colors.keys())
            logging.info("All node types set to visible")
        else:
            # Empty the set (nothing visible)
            self.visible_node_types = set()
            logging.info("All node types set to hidden")
            
        # Redraw the graph with new visibility settings
        if hasattr(self, 'graph'):
            self.plot_graph(self.graph)
    
    def set_text_block_stickiness(self, stickiness):
        """Set how sticky text blocks are to their parent pages (0.0-1.0)."""
        # Ensure value is between 0.0 and 1.0
        stickiness = max(0.0, min(1.0, stickiness))
        
        if self.text_block_stickiness != stickiness:
            self.text_block_stickiness = stickiness
            logging.info(f"Text block stickiness set to: {stickiness}")
            
            # Redraw the graph with new stickiness
            if hasattr(self, 'graph'):
                self.plot_graph(self.graph)
                
        return self.text_block_stickiness

    def set_discover_mode(self, enabled, focus_node=None):
        """Enable or disable discover mode with optional focus node."""
        self.discover_mode = enabled
        
        if enabled:
            # Enable labels automatically in discover mode
            self.labels_visible = True
            
            if focus_node:
                self.focus_node = focus_node
                # Redraw with discover mode settings
                if hasattr(self, 'graph') and self.graph:
                    self.plot_graph(self.graph)
                return True
        elif not enabled:
            # When exiting discover mode, keep labels state as-is
            self.focus_node = None
            if hasattr(self, 'graph') and self.graph:
                self.plot_graph(self.graph)
            return True
        return False
    
    def set_explore_parameters(self, depth=None, max_nodes=None):
        """Set the parameters for graph exploration in discover mode."""
        if depth is not None:
            self.explore_depth = max(1, min(5, depth))  # Limit depth between 1-5
        
        if max_nodes is not None:
            self.max_nodes = max(5, min(50, max_nodes))  # Limit nodes between 5-50
            
        # Update the graph if in discover mode
        if self.discover_mode and hasattr(self, 'graph') and self.graph:
            self.plot_graph(self.graph)
    
    def create_discover_subgraph(self):
        """Create a subgraph centered on the focus node with limited depth."""
        if not hasattr(self, 'graph') or not self.graph or not self.focus_node:
            return None
            
        try:
            # Create a new graph for the discover view
            G = nx.Graph()
            
            # Start with the focus node
            nodes_to_include = {self.focus_node}
            frontier = {self.focus_node}
            visited = set()
            
            # Map the depth each node is from the focus node
            depth_map = {self.focus_node: 0}
            
            # BFS traversal to specified depth
            for depth in range(1, self.explore_depth + 1):
                next_frontier = set()
                
                for node in frontier:
                    visited.add(node)
                    
                    # Get all neighbors (both predecessors and successors)
                    neighbors = set(self.graph.predecessors(node)).union(set(self.graph.successors(node)))
                    
                    # Add unvisited neighbors
                    for neighbor in neighbors:
                        if neighbor not in visited and neighbor not in frontier:
                            next_frontier.add(neighbor)
                            depth_map[neighbor] = depth
                
                # Add current frontier nodes
                nodes_to_include.update(frontier)
                
                # Update frontier
                frontier = next_frontier
                
                # Check if we've reached max_nodes
                if len(nodes_to_include) + len(frontier) > self.max_nodes:
                    # We need to limit the number of nodes
                    remaining = self.max_nodes - len(nodes_to_include)
                    if remaining > 0:
                        # Take a sample of the frontier
                        frontier_sample = list(frontier)[:remaining]
                        nodes_to_include.update(frontier_sample)
                    break
                else:
                    # We can add the entire frontier
                    nodes_to_include.update(frontier)
            
            # Create subgraph with the nodes to include
            subgraph = self.graph.subgraph(nodes_to_include)
            
            return subgraph, depth_map
            
        except Exception as e:
            logging.error(f"Error creating discover subgraph: {e}")
            return None, {}
    
    def plot_graph(self, graph):
        """Plot a NetworkX graph."""
        if graph is None:
            return
            
        try:
            self.clear_plot()
            # Set the graph attribute
            self.graph = graph
            
            # Handle discover mode
            depth_map = {}
            if self.discover_mode and self.focus_node:
                result = self.create_discover_subgraph()
                if result and result[0]:
                    graph = result[0]  # Use the limited subgraph
                    depth_map = result[1]  # Get depth mapping for node coloring
            
            # Filter nodes based on visible node types
            visible_nodes = []
            if not self.visible_node_types:  # If empty, all types are visible
                visible_nodes = list(graph.nodes())
            else:
                for node in graph.nodes():
                    node_type = graph.nodes[node].get('node_type', 'document')
                    if node_type in self.visible_node_types:
                        visible_nodes.append(node)
            
            # Create a subgraph with only the visible nodes
            subgraph = graph.subgraph(visible_nodes)
            
            # Generate positions for the subgraph
            if not hasattr(self, 'positions') or self.positions is None:
                # Create positions for all nodes in original graph
                self.positions = nx.spring_layout(graph)
            else:
                # Ensure all nodes in the graph have positions
                missing_nodes = [node for node in graph.nodes() if node not in self.positions]
                if missing_nodes:
                    logging.info(f"Adding {len(missing_nodes)} missing nodes to positions")
                    # Generate temporary positions for the entire graph
                    temp_pos = nx.spring_layout(graph, pos=self.positions, fixed=self.positions.keys())
                    # Update positions with new nodes only
                    for node in missing_nodes:
                        if node in temp_pos:
                            self.positions[node] = temp_pos[node]
            
            # Adjust positions for text blocks based on stickiness
            positions_copy = self.positions.copy()
            
            # Find all text blocks and their parent pages
            for node in graph.nodes():
                if node not in visible_nodes:
                    continue
                    
                node_data = graph.nodes[node]
                if node_data.get('node_type') == 'text_block':
                    # Find parent page (if any)
                    for pred in graph.predecessors(node):
                        pred_data = graph.nodes[pred]
                        edge_data = graph.get_edge_data(pred, node)
                        
                        if (pred_data.get('node_type') == 'page' and 
                            edge_data.get('type') == 'contains'):
                            
                            # Calculate new position based on stickiness
                            # Higher stickiness means position closer to parent page
                            if self.text_block_stickiness > 0.5:
                                # Increase stickiness: move text_block closer to page
                                factor = (self.text_block_stickiness - 0.5) * 2  # 0-1 range
                                positions_copy[node] = (
                                    self.positions[node][0] * (1 - factor) + self.positions[pred][0] * factor,
                                    self.positions[node][1] * (1 - factor) + self.positions[pred][1] * factor
                                )
                            elif self.text_block_stickiness < 0.5:
                                # Decrease stickiness: move text_block further from page
                                factor = (0.5 - self.text_block_stickiness) * 2  # 0-1 range
                                diff_x = self.positions[node][0] - self.positions[pred][0]
                                diff_y = self.positions[node][1] - self.positions[pred][1]
                                positions_copy[node] = (
                                    self.positions[node][0] + diff_x * factor,
                                    self.positions[node][1] + diff_y * factor
                                )
                            break
            
            # Prepare node sizes - make ONLY the focus node larger
            node_sizes = []
            for n in subgraph.nodes():
                if self.discover_mode and n == self.focus_node:
                    # Focus node is significantly larger
                    node_sizes.append(subgraph.nodes[n].get('size', 300) * 3.5)
                else:
                    node_sizes.append(subgraph.nodes[n].get('size', 300))
            
            # Always use the original node colors (from both overview and discover modes)
            node_colors = [subgraph.nodes[n].get('color', 'skyblue') for n in subgraph.nodes()]
            
            # Draw nodes with their colors and sizes (only draw once)
            nx.draw_networkx_nodes(
                subgraph,
                positions_copy,
                ax=self.ax,
                node_color=node_colors,
                node_size=node_sizes
            )
            
            # Set edge color based on mode
            edge_color = 'grey' if self.discover_mode else 'black'
            
            # Draw edges with adjusted styles for contains relationships
            for u, v in subgraph.edges():
                edge_data = subgraph.get_edge_data(u, v)
                edge_type = edge_data.get('type', 'default')
                
                if (edge_type == 'contains' and 
                    subgraph.nodes[u].get('node_type') == 'page' and 
                    subgraph.nodes[v].get('node_type') == 'text_block'):
                    # Adjust width based on stickiness
                    width = 1 + self.text_block_stickiness * 2  # Width from 1-3
                    style = 'dotted' if self.text_block_stickiness < 0.3 else 'solid'
                    
                    # Draw this edge with custom style
                    nx.draw_networkx_edges(
                        subgraph,
                        positions_copy,
                        ax=self.ax,
                        edgelist=[(u, v)],
                        arrows=True,
                        arrowstyle='-|>',
                        arrowsize=10,
                        width=width,
                        style=style,
                        edge_color=edge_color  # Use conditional edge color
                    )
                else:
                    # Draw regular edge
                    nx.draw_networkx_edges(
                        subgraph,
                        positions_copy,
                        ax=self.ax,
                        edgelist=[(u, v)],
                        arrows=True,
                        arrowstyle='-|>',
                        arrowsize=10,
                        width=1,
                        edge_color=edge_color  # Use conditional edge color
                    )
            
            # Draw labels only if they're visible
            if self.labels_visible:
                labels = {}
                for node in subgraph.nodes():
                    # In discover mode, show full labels without truncation
                    if self.discover_mode:
                        labels[node] = subgraph.nodes[node].get('name', str(node))
                    else:
                        # In overview mode, truncate long labels as before
                        name = subgraph.nodes[node].get('name', str(node))
                        if len(name) > 15:
                            name = name[:12] + "..."
                        labels[node] = name
                        
                # Draw node labels with adjusted font size and position
                nx.draw_networkx_labels(
                    subgraph,
                    positions_copy,
                    labels=labels,
                    font_size=10 if not self.discover_mode else 8,  # Smaller font in discover for readability
                    font_color='black',
                    ax=self.ax,
                    # Add slight vertical offset to avoid overlap with nodes
                    verticalalignment='bottom' if self.discover_mode else 'center'
                )
            
            # Remove axis
            self.ax.set_axis_off()
            
            # If in discover mode and we have a focus node, add a highlight circle
            if self.discover_mode and self.focus_node and self.focus_node in positions_copy:
                # Add title showing focus node name
                focus_label = graph.nodes[self.focus_node].get('name', str(self.focus_node))
                self.ax.set_title(f"Exploring from: {focus_label}")
                
                # Get position of focus node and size
                focus_x, focus_y = positions_copy[self.focus_node]
                focus_size = subgraph.nodes[self.focus_node].get('size', 300) * 3.5
                
                import numpy as np
                
                # Base circle radius on node size - consistent radius regardless of position
                circle_radius = (focus_size/300) * 0.17
                
                # Use a proper circle patch instead of dots
                from matplotlib.patches import Circle
                
                # Create a circle around the focus node
                highlight_circle = Circle(
                    (focus_x, focus_y),
                    radius=circle_radius,
                    fill=False,
                    edgecolor='black',
                    linestyle='dotted',
                    linewidth=2,
                    alpha=0.8,
                    zorder=0  # Below node
                )
                self.ax.add_patch(highlight_circle)
            else:
                self.ax.set_title("")
                
            # Refresh canvas
            self.draw()
            
        except Exception as e:
            logging.error(f"Error plotting graph: {e}")
            self.clear_plot()

    def toggle_labels(self):
        """Toggle the visibility of labels."""
        self.labels_visible = not self.labels_visible
        if hasattr(self, 'graph'):
            self.plot_graph(self.graph)  # Redraw graph with/without labels

    def on_node_click(self, event):
        """Handle node click event."""
        if event.inaxes != self.ax or self.graph is None or self.positions is None:
            return  # Click outside axes or no graph

        # Calculate distances only for nodes that have positions
        distances = []
        for node in self.graph.nodes():
            # Check if node exists in positions dictionary
            if node in self.positions:
                distance = (self.positions[node][0] - event.xdata)**2 + (self.positions[node][1] - event.ydata)**2
                distances.append((node, distance))
            else:
                logging.debug(f"Node {node} has no position defined, skipping in click detection")

        if not distances:
            return  # No nodes with positions

        # Find closest node
        closest_node, min_distance = min(distances, key=lambda x: x[1])

        # Check if click is close enough to the node
        if min_distance < 0.01:  # Adjust threshold as needed
            # Check if this is a double click on the same node
            import time
            current_time = time.time()
            
            if self.last_clicked_node == closest_node and \
               (current_time - self.last_click_time) * 1000 < self.double_click_interval:
                # This is a double click
                self.click_timer.stop()  # Cancel the single click timer
                self.handle_double_click(closest_node)
            else:
                # This is potentially a single click
                self.last_clicked_node = closest_node
                self.click_timer.start(self.double_click_interval)
            
            self.last_click_time = current_time
            
    def handle_single_click(self):
        """Handle single click event - change focus in discover mode."""
        if self.discover_mode and self.last_clicked_node:
            # Only change focus if we're in discover mode
            self.focus_node = self.last_clicked_node
            self.plot_graph(self.graph)
            logging.info(f"Focus changed to node: {self.last_clicked_node}")
            
            # Check if clicked node is a page, if so open it in the editor
            if self.graph and self.last_clicked_node in self.graph.nodes():
                node_data = self.graph.nodes[self.last_clicked_node]
                node_type = node_data.get('node_type', '')
                
                # If it's a page node, open it in the editor
                if node_type == 'page':
                    logging.info(f"Opening page node {self.last_clicked_node} in editor")
                    # Get the main window 
                    main_window = self.parent() if callable(self.parent) else self.parent
                    while main_window and not hasattr(main_window, 'open_node_in_page_editor'):
                        main_window = main_window.parent()
                    
                    if main_window and hasattr(main_window, 'open_node_in_page_editor'):
                        main_window.open_node_in_page_editor(self.last_clicked_node)
    
    def handle_double_click(self, node):
        """Handle double click event - open node dialog."""
        # Get the main window
        main_window = self.parent() if callable(self.parent) else self.parent
        
        # Show node info dialog
        show_node_info(main_window, node)
        logging.info(f"Node double-clicked: {node}")

    def save_plot_as_image(self):
        """Save the graph plot as an image."""
        logging.info("Saving plot as image...")
        try:
            file_dialog = QtWidgets.QFileDialog()
            file_path, _ = file_dialog.getSaveFileName(
                self.parent,
                "Save Plot as Image",
                "",
                "PNG (*.png);;JPG (*.jpg *.jpeg);;All Files (*)"
            )

            if file_path:
                self.fig.savefig(file_path)
                logging.info(f"Plot saved as image to {file_path}")
            else:
                logging.info("Save plot as image cancelled.")

        except Exception as e:
            logging.error(f"Error saving plot as image: {e}")
            QtWidgets.QMessageBox.critical(self.parent, "Error", f"Error saving plot as image: {e}")

    def clear_plot(self):
        """Clear the plot."""
        if hasattr(self, 'ax'):
            self.ax.clear()
            self.draw()
