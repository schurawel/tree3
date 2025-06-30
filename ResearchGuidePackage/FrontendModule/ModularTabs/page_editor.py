from PyQt6 import QtWidgets, QtCore, QtGui, QtPrintSupport
from PyQt6.QtCore import Qt
import logging
import asyncio
import uuid
from ResearchGuidePackage.FrontendModule.bullet_points_edit import AbstractBulletPointsEdit
try:
    from ResearchGuidePackage.FrontendModule.clickable_text_edit import ClickableTextEdit
    from ResearchGuidePackage.FrontendModule.link_handler import handle_link_click
except ImportError:
    from clickable_text_edit import ClickableTextEdit
    from link_handler import handle_link_click

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('PageEditor')

class PageEditor(AbstractBulletPointsEdit):
    """Widget for editing page content with node selection."""
    def __init__(self, main_window):
        """Initialize PageEditor."""
        # Initialize parent class first to create scroll_area
        super().__init__(main_window)
        
        # Initialize PageEditor specific properties
        self.current_node_id = None
        self.current_view_type = "content"  # Changed default view type to content
        
        # Setup UI specific to PageEditor
        self._setup_ui()
        
        logger.info("PageEditor initialized.")

    def _setup_ui(self):
        """Setup UI elements specific to PageEditor."""
        # Control panel with node selector (insert at top of existing layout)
        control_layout = QtWidgets.QHBoxLayout()
        
        # Node selection dropdown
        self.node_dropdown = QtWidgets.QComboBox()
        self.node_dropdown.setMinimumWidth(200)
        self.node_dropdown.currentIndexChanged.connect(self.on_node_selected)
        control_layout.addWidget(self.node_dropdown)
        
        # Add view type dropdown
        self.view_type_dropdown = QtWidgets.QComboBox()
        self.view_type_dropdown.addItem("Metadata", "metadata")
        self.view_type_dropdown.addItem("Content", "content")
        self.view_type_dropdown.setMinimumWidth(120)
        self.view_type_dropdown.setCurrentIndex(1)  # Preselect "Content" option
        self.view_type_dropdown.currentIndexChanged.connect(self.on_view_type_changed)
        control_layout.addWidget(self.view_type_dropdown)
        
        # Add toggle mode button
        self.toggle_mode_button = QtWidgets.QPushButton("View Mode")
        self.toggle_mode_button.clicked.connect(self.toggle_text_edit_mode)
        control_layout.addWidget(self.toggle_mode_button)
        
        # Add save changes button
        self.save_changes_button = QtWidgets.QPushButton("Save Changes")
        self.save_changes_button.clicked.connect(self.save_changes)
        self.save_changes_button.setEnabled(False)  # Start disabled
        self.save_changes_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
        """)
        control_layout.addWidget(self.save_changes_button)
        
        # Add Copy Node ID button
        self.copy_id_button = QtWidgets.QPushButton("Copy ID")
        self.copy_id_button.setToolTip("Copy the node ID to clipboard")
        self.copy_id_button.clicked.connect(self.copy_node_id_to_clipboard)
        self.copy_id_button.setEnabled(False)  # Start disabled
        self.copy_id_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton:hover:enabled {
                background-color: #0b7dda;
            }
        """)
        control_layout.addWidget(self.copy_id_button)
        
        # Add spacer to push elements to the left
        control_layout.addStretch()
        
        # Add print button to the right with proper styling
        self.print_button = QtWidgets.QPushButton()
        
        # Create a better print icon - simple Unicode character
        self.print_button.setText("🖨️")
        self.print_button.setFont(QtGui.QFont("Arial", 14))
        
        # Style the button to look better
        self.print_button.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 4px;
                color: #888888;
            }
            QPushButton:enabled {
                color: black;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)
        
        self.print_button.setToolTip("Print current page")
        self.print_button.clicked.connect(self.print_page)
        self.print_button.setFixedSize(32, 32)
        self.print_button.setEnabled(False)  # Start disabled
        control_layout.addWidget(self.print_button)
        
        # Insert control layout at the top of main_layout with proper margins
        control_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.insertLayout(0, control_layout)
        
        # Ensure content widget has proper spacing between sections
        self.content_layout.setSpacing(10)
        
        # Populate node dropdown initially
        self.populate_node_dropdown()
    
    def on_view_type_changed(self, index):
        """Handle view type selection change."""
        self.current_view_type = self.view_type_dropdown.itemData(index)
        logger.info(f"Changed view type to: {self.current_view_type}")
        
        # Reload content with new view type if a node is selected
        if self.current_node_id:
            asyncio.create_task(self.load_node_content(self.current_node_id))
            
    def toggle_text_edit_mode(self):
        """Toggle between view and edit modes for all text edits."""
        # Determine new mode based on button text
        new_mode = "view" if self.toggle_mode_button.text() == "Edit Mode" else "edit"
        
        # Update all bullet editors
        for editor in self.bullet_editors.values():
            # Skip backlink editors - they should always remain in view mode
            if editor.property("is_backlink"):
                editor.set_mode("view")
                continue
            
            editor.set_mode(new_mode)
        
        # Update button text
        if new_mode == "edit":
            self.toggle_mode_button.setText("View Mode")
            self.save_changes_button.setEnabled(True)  # Enable save button in edit mode
        else:
            self.toggle_mode_button.setText("Edit Mode")
            self.save_changes_button.setEnabled(False)  # Disable save button in view mode
            
        logger.info(f"All text editors toggled to: {new_mode}")
            
    def populate_node_dropdown(self):
        """Populate the node dropdown with page nodes from the graph."""
        self.node_dropdown.clear()
        self.node_dropdown.addItem("Select a page...", None)  # Default empty selection
        
        # Check if graph exists
        if hasattr(self.main_window, 'graph') and self.main_window.graph:
            # Filter for nodes with node_type="page"
            page_nodes = []
            for node_id, node_data in self.main_window.graph.nodes(data=True):
                if node_data.get('node_type') == 'page':
                    # Get the best display name for the page - NO ICONS
                    display_text = node_data.get('title', 
                                  node_data.get('name', 
                                  node_data.get('label', str(node_id)[:8])))
                    
                    # No icons at all - just use the text
                    page_nodes.append((display_text, node_id))
            
            # Sort pages alphabetically
            page_nodes.sort()
            
            # Add sorted pages to dropdown
            for display_text, node_id in page_nodes:
                self.node_dropdown.addItem(display_text, str(node_id))
            
            logger.info(f"Populated node dropdown with {len(page_nodes)} page nodes")
        else:
            logger.warning("No graph available to populate node dropdown")
            
    def on_node_selected(self, index):
        """Handle node selection from dropdown."""
        # Clear previous content
        self.clear_content()
        
        if index <= 0:  # First item is a placeholder
            self.default_label.setText("No node selected")
            self.default_label.setVisible(True)
            self.current_node_id = None
            self.print_button.setEnabled(False)  # Disable print button
            self.copy_id_button.setEnabled(False)  # Disable copy ID button
            return
            
        node_id_str = self.node_dropdown.itemData(index)
        try:
            node_id = uuid.UUID(node_id_str)
            self.current_node_id = node_id
            self.print_button.setEnabled(True)  # Enable print button
            self.copy_id_button.setEnabled(True)  # Enable copy ID button
            
            # Update the tab title if this editor is in a tab widget
            self.update_tab_title()
            
            # Use asyncio to load node content
            asyncio.create_task(self.load_node_content(node_id))
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid node ID: {node_id_str}, error: {e}")
            self.default_label.setText(f"Error: Invalid node ID")
            self.default_label.setVisible(True)
            self.print_button.setEnabled(False)  # Disable print button
            self.copy_id_button.setEnabled(False)  # Disable copy ID button
    
    async def load_node_content(self, node_id):
        """Load the content for a specific node based on selected view type."""
        try:
            # Clear any existing content
            self.clear_content()
            
            if self.main_window.graph and node_id in self.main_window.graph:
                graph = self.main_window.graph
                node_data = graph.nodes[node_id]
                
                # Use title for page nodes, or fall back to name or label
                # IMPORTANT: Don't include icons here - get clean title
                node_display_name = node_data.get('title', 
                                  node_data.get('name', 
                                  node_data.get('label', str(node_id)[:8])))
                
                # Create title header with proper spacing
                title_container = QtWidgets.QWidget()
                title_layout = QtWidgets.QVBoxLayout(title_container)
                title_layout.setContentsMargins(10, 10, 10, 10)
                
                title_label = QtWidgets.QLabel(f"<h1>{node_display_name}</h1>")
                title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                title_label.setWordWrap(True)
                title_layout.addWidget(title_label)
                
                self.content_layout.addWidget(title_container)
                
                # Create spacing widget instead of separator
                spacer = QtWidgets.QWidget()
                spacer.setFixedHeight(10)
                self.content_layout.addWidget(spacer)
                
                # Display content based on selected view type
                if self.current_view_type == "metadata":
                    await self.load_metadata_view(node_id, node_data, graph)
                    # Disable save button for metadata view
                    self.save_changes_button.setEnabled(False)
                else:  # content view
                    await self.load_content_view(node_id, node_data)
                    # Enable save button if in edit mode
                    self.save_changes_button.setEnabled(self.toggle_mode_button.text() == "View Mode")
                
                # Start in edit mode
                self.toggle_mode_button.setText("View Mode")
                logger.info(f"Loaded {self.current_view_type} view for node: {node_display_name} ({node_id})")
            else:
                self.default_label.setText(f"Node {node_id} not found in graph")
                self.default_label.setVisible(True)
                logger.warning(f"Node {node_id} not found in graph")
        except Exception as e:
            logger.error(f"Error loading node content: {e}")
            self.default_label.setText(f"Error loading node content: {e}")
            self.default_label.setVisible(True)
    
    async def load_metadata_view(self, node_id, node_data, graph):
        """Load metadata view showing node attributes."""
        # Section 1: Node Attributes
        self.add_section_header("Node Attributes")
        
        # Create container for attributes bullet points with zero margins
        attr_container = self.create_bullet_points_container()
        
        # Add individual bullet points to the container
        self.add_bullet_point_to_container(attr_container, f"**ID:** {node_id}")
        
        for attr_name, attr_value in node_data.items():
            if attr_name not in ['name', 'label']:  # Name and label are already shown in title
                self.add_bullet_point_to_container(attr_container, f"**{attr_name}:** {attr_value}")
        
        # Add the attributes container to the main content layout
        self.content_layout.addWidget(attr_container)
    
    async def load_content_view(self, node_id, node_data):
        """Load content view showing content, links and backlinks."""
        graph = self.main_window.graph
        
        # Display text blocks directly without a section header
        content_container = self.create_bullet_points_container()
        content_container.setObjectName("content_section_container")  # Add identifier
        
        # Find text blocks associated with this page
        text_blocks = []
        for edge in graph.edges(node_id, data=True):
            # Get target node
            target_node_id = edge[1]
            # Check if this is a "contains" relationship to a text_block
            if edge[2].get('type') == 'contains':
                try:
                    target_data = graph.nodes[target_node_id]
                    if target_data.get('node_type') == 'text_block':
                        # Get weight as position for ordering
                        position = edge[2].get('weight', 0)
                        text_blocks.append((position, target_node_id, target_data))
                except Exception as e:
                    logger.warning(f"Failed to process text block: {e}")
        
        # Sort text blocks by position
        text_blocks.sort()
        
        # Store the original text blocks for comparison when saving
        self.original_text_blocks = []
        
        # Display text blocks
        if text_blocks:
            for idx, (position, text_block_id, text_block_data) in enumerate(text_blocks):
                # Get content and level from the text block
                content = text_block_data.get('content', '')
                level = int(text_block_data.get('level', 0))  # Convert to int in case it's stored as string
                block_type = text_block_data.get('type', 'Paragraph')
                
                # Add indent based on level
                indent = ' ' * (4 * level) if level > 0 else ''
                
                # Format content based on block type
                if block_type == 'Heading':
                    formatted_content = f"{indent}## {content}"
                elif block_type == 'Bullet':
                    formatted_content = f"{indent}• {content}"
                else:
                    formatted_content = f"{indent}{content}"
                
                # Add as bullet point and store editor reference with unique ID
                editor = self.add_bullet_point_to_container(content_container, formatted_content)
                
                # Explicitly set a unique object name for the editor to ensure it's tracked correctly
                editor_id = f"content_editor_{idx}"  # Use index for uniqueness
                editor.setObjectName(editor_id)
                
                # Store the original text block info with reliable ID mapping
                self.original_text_blocks.append({
                    "editor_id": editor_id,
                    "text_block_id": text_block_id,
                    "content": content,
                    "level": level,
                    "type": block_type,
                    "position": position
                })
        else:
            # If no text blocks, add empty paragraph
            editor = self.add_bullet_point_to_container(content_container, "")
            
            # Explicitly set a unique object name
            editor_id = "content_editor_0"
            editor.setObjectName(editor_id)
            
            self.original_text_blocks.append({
                "editor_id": editor_id,
                "text_block_id": None,
                "content": "",
                "level": 0,
                "type": "Paragraph",
                "position": 0
            })
        
        # Add content container to main layout
        self.content_layout.addWidget(content_container)
        
        # Add spacing widget instead of separator
        spacer1 = QtWidgets.QWidget()
        spacer1.setFixedHeight(20)
        self.content_layout.addWidget(spacer1)
        
        # Section: Links (outgoing connections)
        self.add_section_header("Links")
        links_container = self.create_bullet_points_container()
        links_container.setObjectName("links_section_container")  # Add identifier
        
        # Get outgoing connections
        outgoing_nodes = list(graph.successors(node_id)) if graph.is_directed() else list(graph.neighbors(node_id))
        has_links = False
        
        # Add all links including file sources - NO ICONS
        for target in outgoing_nodes:
            if target != node_id:  # Skip self-loops
                try:
                    target_data = graph.nodes[target]
                    # Skip text blocks (they're shown in content)
                    if target_data.get('node_type') == 'text_block':
                        continue
                    
                    # Get the edge data
                    edge_data = graph.get_edge_data(node_id, target)
                    edge_type = edge_data.get('type', 'default') if edge_data else 'default'
                    
                    # Get best display name for target
                    target_label = target_data.get('title', 
                                 target_data.get('name',
                                 target_data.get('label', str(target)[:8])))
                    
                    # No icons - just format the link
                    if edge_type == 'has_source':
                        file_path = target_data.get('file_path', '')
                        link_text = f"[{target_label}]({file_path}) (source file)"
                    else:
                        link_text = f"[{target_label}]({target}) (type: {edge_type})"
                    
                    self.add_bullet_point_to_container(links_container, link_text)
                    has_links = True
                except Exception as e:
                    logger.warning(f"Failed to process link: {e}")
        
        if not has_links:
            self.add_bullet_point_to_container(links_container, "")
        
        # Add links container to main layout
        self.content_layout.addWidget(links_container)
        
        # Section: Backlinks (incoming connections)
        self.add_section_header("Backlinks")
        backlinks_container = self.create_bullet_points_container()
        backlinks_container.setObjectName("backlinks_section_container")  # Add identifier
        
        # Get incoming connections
        if graph.is_directed():
            incoming_nodes = list(graph.predecessors(node_id))
        else:
            incoming_nodes = outgoing_nodes
        
        has_backlinks = False
        for source in incoming_nodes:
            # Skip self-loops and duplicates in undirected graphs
            if source != node_id and (graph.is_directed() or source not in outgoing_nodes):
                try:
                    source_data = graph.nodes[source]
                    edge_data = graph.get_edge_data(source, node_id)
                    edge_type = edge_data.get('type', 'default') if edge_data else 'default'
                    
                    # Skip text blocks that contain this node
                    if edge_type == 'contains' and source_data.get('node_type') == 'text_block':
                        continue
                    
                    source_label = source_data.get('title',
                                    source_data.get('name',
                                    source_data.get('label', str(source)[:8])))
                    
                    # No icons - just format the link
                    link_text = f"[{source_label}]({source}) (type: {edge_type})"
                    editor = self.add_bullet_point_to_container(backlinks_container, link_text)
                    
                    # Mark this editor as a backlink editor to keep it read-only
                    editor.setProperty("is_backlink", True)
                    editor.set_mode("view")  # Ensure it starts in view mode
                    
                    has_backlinks = True
                except Exception as e:
                    logger.warning(f"Failed to process backlink: {e}")
        
        if not has_backlinks:
            editor = self.add_bullet_point_to_container(backlinks_container, "")
            editor.setProperty("is_backlink", True)
            editor.set_mode("view")  # Ensure empty placeholder is also read-only
        
        # Add backlinks container to main layout
        self.content_layout.addWidget(backlinks_container)
    
    def add_separator_with_spacing(self):
        """Add a horizontal separator with spacing above and below."""
        # Add spacing before separator
        spacer1 = QtWidgets.QWidget()
        spacer1.setFixedHeight(10)
        self.content_layout.addWidget(spacer1)
        
        # Add horizontal separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        separator.setStyleSheet("margin: 0 8px; background-color: #cccccc;")
        separator.setMinimumHeight(2)
        self.content_layout.addWidget(separator)
        
        # Add spacing after separator
        spacer2 = QtWidgets.QWidget()
        spacer2.setFixedHeight(10)
        self.content_layout.addWidget(spacer2)
    
    def refresh(self):
        """Refresh the page editor, update dropdown and reload current node."""
        self.populate_node_dropdown()
        if self.current_node_id:
            # Find the current node in the dropdown
            for i in range(self.node_dropdown.count()):
                item_data = self.node_dropdown.itemData(i)
                if item_data == str(self.current_node_id):
                    self.node_dropdown.setCurrentIndex(i)
                    break
            # Reload current node content with current view type
            asyncio.create_task(self.load_node_content(self.current_node_id))

    def print_page(self):
        """Print the current page."""
        if not self.current_node_id:
            QtWidgets.QMessageBox.information(self, "Print", "No page selected to print.")
            return
            
        logger.info(f"Printing page for node: {self.current_node_id}")
        
        printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.PrinterMode.HighResolution)
        dialog = QtPrintSupport.QPrintDialog(printer, self)
        
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        
        # Create a document to print (capture the content from our layout)
        document = QtGui.QTextDocument()
        html = f"<html><body>"
        
        # Add title if available, ensuring no emoji icons
        if self.current_node_id and self.main_window.graph:
            node_data = self.main_window.graph.nodes[self.current_node_id]
            node_display_name = node_data.get('title', 
                              node_data.get('name', 
                              node_data.get('label', str(self.current_node_id)[:8])))

            html += f"<h1 style='text-align:center'>{node_display_name}</h1><hr>"
            
        # Get content from all bullet editors
        for editor_id, editor in self.bullet_editors.items():
            text = editor.toPlainText()
            if text.startswith("•"):
                # Remove bullet point marker for cleaner print
                text = text[1:].strip()
            html += f"<p>{text}</p>"
        
        html += "</body></html>"
        document.setHtml(html)
        
        # Print the document
        document.print(printer)
        
        logger.info("Print job sent to printer")

    def add_section_header(self, title):
        """Add a section header with the given title."""
        # Create a container for the header with proper spacing
        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(8, 16, 8, 8)
        container_layout.setSpacing(0)
        
        # Add the header label
        header_label = QtWidgets.QLabel(f"<h2>{title}</h2>")
        header_label.setWordWrap(True)
        container_layout.addWidget(header_label)
        
        # Add container to content layout
        self.content_layout.addWidget(container)
        self.section_editors[title] = header_label
        return header_label

    def get_tab_title(self):
        """Get a title for the tab based on the current node."""
        if not self.current_node_id or not hasattr(self.main_window, 'graph') or not self.main_window.graph:
            return "Page"
            
        try:
            # Try to get node data from the graph
            if self.current_node_id in self.main_window.graph:
                node_data = self.main_window.graph.nodes[self.current_node_id]
                # Use title for page nodes, then name, then label
                # No icons - just return the title
                return node_data.get('title', 
                         node_data.get('name', 
                         node_data.get('label', "Page")))
        except Exception as e:
            logger.error(f"Error getting tab title: {e}")
            
        return "Page"

    def update_tab_title(self):
        """Update the title of the tab containing this editor."""
        # Find the parent tab widget and update the tab title
        tab_title = self.get_tab_title()
        
        # Look for this widget in a tab widget
        parent = self.parent()
        while parent:
            if isinstance(parent, QtWidgets.QTabWidget):
                # Find the index of this widget in the tab widget
                for i in range(parent.count()):
                    if parent.widget(i) == self:
                        parent.setTabText(i, tab_title)
                        break
                break
            parent = parent.parent()

    def save_changes(self):
        """
        Non-async wrapper for save_changes_async to ensure the method can be called from non-async contexts.
        This fixes the "coroutine was never awaited" warning.
        """
        # Create a task that runs the async version
        asyncio.create_task(self.save_changes_async())
    
    async def save_changes_async(self):
        """Save changes to text blocks using only the ticket system."""
        if not self.current_node_id:
            QtWidgets.QMessageBox.warning(self, "Save Changes", "No page selected.")
            return
        
        if self.current_view_type != "content":
            QtWidgets.QMessageBox.warning(self, "Save Changes", "Changes can only be saved in content view.")
            return
                
        try:
            # Store the page ID for consistent reference
            page_node_id = self.current_node_id
            logger.info(f"Saving changes for page: {page_node_id}")
            
            # Get content blocks from editors
            current_blocks = self._extract_blocks_from_content_container()
            if current_blocks is None:
                return
            
            # Process text block changes
            await self._process_block_changes(page_node_id, current_blocks)
            
            # Update the page's timestamp
            await self.main_window.communication.request_and_get_response(
                operation="edit_node",
                params={
                    "node_id": str(page_node_id),
                    "attributes": {
                        "last_edited": str(QtCore.QDateTime.currentDateTime().toString())
                    },
                    "update_page": False
                },
                sender="PageEditor"
            )
            
            # Get fresh graph data from backend - no timeout
            success, response, error = await self.main_window.communication.request_and_get_response(
                operation="get_graph",
                params={},
                sender="PageEditor"
            )
            
            if success and "graph_data" in response:
                # Show success message
                QtWidgets.QMessageBox.information(self, "Save Changes", "Changes saved successfully.")
                
                # IMPORTANT: Wait for show_graph to complete before reloading page content
                graph_updated = await self.main_window.show_graph()
                
                # Only reload page content if graph update was successful
                if graph_updated:
                    logger.info(f"Graph update complete - now reloading page content for node {page_node_id}")
                    await self.load_node_content(page_node_id)
                else:
                    logger.warning("Graph update failed, skipping page content reload")
            else:
                logger.error(f"Failed to get updated graph: {error}")
                QtWidgets.QMessageBox.warning(self, "Warning", "Changes saved but failed to refresh graph.")
            
        except Exception as e:
            logger.error(f"Error saving changes: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")

    async def _process_block_changes(self, page_node_id, current_blocks):
        """Process changes between current blocks and original blocks."""
        # Get original blocks for comparison
        original_blocks_by_id = {block["editor_id"]: block for block in self.original_text_blocks if "editor_id" in block}
        
        # Track which blocks we've processed
        processed_ids = set()
        
        # STEP 1: Update existing blocks or create new ones
        for i, block in enumerate(current_blocks):
            editor_id = block["editor_id"]
            
            # Skip empty new blocks
            if not block["content"] and editor_id not in original_blocks_by_id:
                continue
                
            if editor_id in original_blocks_by_id:
                # Existing block - check if it needs updating
                original_block = original_blocks_by_id[editor_id]
                text_block_id = original_block.get("text_block_id")
                processed_ids.add(editor_id)
                
                if text_block_id:
                    # Update only if changed
                    needs_update = (block["content"] != original_block["content"] or 
                                    block["level"] != original_block["level"] or
                                    block["type"] != original_block["type"])
                                    
                    position_changed = i != original_block["position"]
                    
                    # Update content if changed
                    if needs_update:
                        await self.main_window.communication.request_and_get_response(
                            operation="edit_node",
                            params={
                                "node_id": str(text_block_id),
                                "attributes": {
                                    "content": block["content"],
                                    "level": block["level"],
                                    "type": block["type"]
                                },
                                "update_page": False
                            },
                            sender="PageEditor"
                        )
                    
                    # Update position if changed
                    if position_changed:
                        # First delete the old edge
                        await self.main_window.communication.request_and_get_response(
                            operation="delete_edge",
                            params={
                                "source_id": str(page_node_id),
                                "target_id": str(text_block_id),
                                "update_page": False
                            },
                            sender="PageEditor"
                        )
                        
                        # Then create a new edge with updated weight
                        await self.main_window.communication.request_and_get_response(
                            operation="add_edge",
                            params={
                                "source_id": str(page_node_id),
                                "target_id": str(text_block_id),
                                "weight": i,
                                "edge_type": "contains",
                                "update_page": False
                            },
                            sender="PageEditor"
                        )
                elif block["content"]:
                    # Text block ID is None but we have content - create new block
                    await self._create_text_block(page_node_id, block, i)
            elif block["content"]:
                # New block with content - create it
                await self._create_text_block(page_node_id, block, i)
        
        # STEP 2: Remove deleted blocks
        for editor_id, original_block in original_blocks_by_id.items():
            if editor_id not in processed_ids and original_block.get("text_block_id"):
                text_block_id = original_block["text_block_id"]
                
                # Delete the edge
                await self.main_window.communication.request_and_get_response(
                    operation="delete_edge",
                    params={
                        "source_id": str(page_node_id),
                        "target_id": str(text_block_id),
                        "update_page": False
                    },
                    sender="PageEditor"
                )
                
                # Only delete node if we're the last reference to it
                await self.main_window.communication.request_and_get_response(
                    operation="delete_node",
                    params={
                        "node_id": str(text_block_id),
                        "update_page": False
                    },
                    sender="PageEditor"
                )

    def _extract_blocks_from_content_container(self):
        """Extract block data from content container editors."""
        # Find content container
        content_container = None
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if isinstance(widget, QtWidgets.QWidget) and widget.objectName() == "content_section_container":
                content_container = widget
                break
        
        if not content_container:
            QtWidgets.QMessageBox.warning(self, "Save Changes", "Content container not found.")
            return None
        
        # Get blocks from content container
        blocks = []
        layout = content_container.layout()
        
        for i in range(layout.count()):
            editor = layout.itemAt(i).widget()
            if not editor or not hasattr(editor, 'toPlainText'):
                continue
            
            # Get editor ID or assign one
            editor_id = editor.objectName() or f"content_editor_new_{i}"
            if not editor.objectName():
                editor.setObjectName(editor_id)
            
            # Parse text content
            text = editor.toPlainText().strip()
            leading_spaces = len(text) - len(text.lstrip())
            level = leading_spaces // 4
            content = text.lstrip()
            
            # Determine block type
            block_type = "Paragraph"  # Default
            if content.startswith("##"):
                block_type = "Heading"
                content = content[2:].strip()
            elif content.startswith("•"):
                block_type = "Bullet"
                content = content[1:].strip()
            
            # Add to blocks
            blocks.append({
                "editor_id": editor_id,
                "content": content,
                "level": level,
                "type": block_type,
                "position": i
            })
        
        return blocks

    async def _create_text_block(self, page_node_id, block_data, position):
        """Create a new text block node and connect it to the page using the ticket system."""
        try:
            # Create text block using the ticket system
            success, response, error = await self.main_window.communication.request_and_get_response(
                operation="create_node",
                params={
                    "name": "",  # Text blocks don't need names
                    "node_type": "text_block",
                    "color": "#95D9C3",  
                    "size": 20,          
                    "content": block_data["content"],
                    "level": block_data["level"],
                    "type": block_data["type"],
                    "update_page": False  # Don't update page yet
                },
                sender="PageEditor"
            )
            
            if not success or not response or "result" not in response:
                logger.error(f"Failed to create text block: {error}")
                return None
                
            # Get the newly created text block ID
            text_block_id = uuid.UUID(response["result"]["node_id"])
            
            # Create edge using the ticket system
            edge_success, edge_response, edge_error = await self.main_window.communication.request_and_get_response(
                operation="add_edge",
                params={
                    "source_id": str(page_node_id),
                    "target_id": str(text_block_id),
                    "weight": position,
                    "edge_type": "contains",
                    "update_page": False  # Don't update page yet
                },
                sender="PageEditor"
            )
            
            if not edge_success:
                logger.error(f"Failed to create edge between page and text block: {edge_error}")
                
            logger.info(f"Created new text block {text_block_id} with content: '{block_data['content'][:30]}...'")
            return text_block_id
        except Exception as e:
            logger.error(f"Error in _create_text_block: {e}")
            return None

    def copy_node_id_to_clipboard(self):
        """Copy the current node ID to clipboard."""
        if not self.current_node_id:
            return
        
        # Get the clipboard and set text
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(str(self.current_node_id))
        
        # Show brief feedback tooltip
        QtWidgets.QToolTip.showText(
            self.copy_id_button.mapToGlobal(QtCore.QPoint(0, -30)),
            "Node ID copied to clipboard",
            self.copy_id_button,
            QtCore.QRect(),
            1500  # Show for 1.5 seconds
        )
        
        logger.info(f"Copied node ID to clipboard: {self.current_node_id}")


