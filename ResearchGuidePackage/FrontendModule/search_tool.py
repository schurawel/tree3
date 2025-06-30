from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
import logging
import asyncio
import uuid
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('SearchTool')

class ResultItemDelegate(QtWidgets.QStyledItemDelegate):
    """Custom delegate to render search result items with better formatting."""
    
    def paint(self, painter, option, index):
        """Custom painting for result items."""
        if index.column() == 1:  # Title column
            # Extract data
            title = index.data(Qt.ItemDataRole.DisplayRole)
            
            # Draw highlighted background if selected
            if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            
            # Setup font for title - make bold but keep normal font size
            title_font = painter.font()  # Use the current font
            title_font.setBold(True)     # Make it bold
            # No font size increase
            
            # Draw with proper colors
            if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
                painter.setPen(option.palette.highlightedText().color())
            else:
                painter.setPen(option.palette.text().color())
                
            painter.setFont(title_font)
            text_rect = option.rect.adjusted(8, 4, -8, -4)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, title)
        
        elif index.column() == 4:  # Preview column
            # Extract data
            preview = index.data(Qt.ItemDataRole.DisplayRole)
            
            # Use a distinct background for preview cells
            if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            else:
                painter.fillRect(option.rect, QtGui.QColor(248, 248, 248))
                
            # Draw text with custom formatting
            if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
                painter.setPen(option.palette.highlightedText().color())
            else:
                painter.setPen(option.palette.text().color())
            
            # Format preview by replacing [highlighted] with actual highlighting
            text_rect = option.rect.adjusted(8, 4, -8, -4)
            
            # Check if we have highlighted portions
            parts = []
            in_highlight = False
            current_part = ""
            i = 0
            while i < len(preview):
                if preview[i:i+1] == "[" and not in_highlight:
                    if current_part:
                        parts.append((current_part, False))
                        current_part = ""
                    in_highlight = True
                    i += 1
                    continue
                elif preview[i:i+1] == "]" and in_highlight:
                    if current_part:
                        parts.append((current_part, True))
                        current_part = ""
                    in_highlight = False
                    i += 1
                    continue
                current_part += preview[i]
                i += 1
            
            if current_part:
                parts.append((current_part, in_highlight))
            
            # If we didn't find any formatting, just draw normally
            if not parts:
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, preview)
                return
                
            # Draw the formatted text
            x = text_rect.left()
            y = text_rect.top() + 2
            font_metrics = painter.fontMetrics()
            
            for text, is_highlight in parts:
                if is_highlight:
                    highlight_font = painter.font()
                    highlight_font.setBold(True)
                    painter.setFont(highlight_font)
                    painter.setPen(QtGui.QColor(200, 0, 0))
                else:
                    normal_font = painter.font()
                    normal_font.setBold(False)
                    painter.setFont(normal_font)
                    if option.state & QtWidgets.QStyle.StateFlag.State_Selected:
                        painter.setPen(option.palette.highlightedText().color())
                    else:
                        painter.setPen(option.palette.text().color())
                
                text_width = font_metrics.horizontalAdvance(text)
                if x + text_width > text_rect.right():
                    # Truncate text if it would overflow
                    available_width = text_rect.right() - x
                    text = font_metrics.elidedText(text, Qt.TextElideMode.ElideRight, available_width)
                    text_width = font_metrics.horizontalAdvance(text)
                
                painter.drawText(QtCore.QRect(x, y, text_width, text_rect.height() - 4), 
                                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
                x += text_width
        else:
            # For other columns, use default rendering
            super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        """Custom size hint for rows."""
        size = super().sizeHint(option, index)
        if index.column() == 1 or index.column() == 4:  # Title or Preview column
            size.setHeight(size.height() + 8)  # Make rows a bit taller for readability
        return size

class SearchTool(QtWidgets.QWidget):
    """Tool for searching nodes in the graph by various criteria."""
    
    def __init__(self, main_window):
        """Initialize the search tool."""
        super().__init__()
        self.main_window = main_window
        self.search_results = []
        
        # Create and setup UI components
        self.setup_ui()
        
        logger.info("Search tool initialized")
    
    def setup_ui(self):
        """Set up the UI components."""
        # Apply modern style
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 16px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2a66c8;
            }
            QPushButton:pressed {
                background-color: #1a56b8;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QComboBox {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QTableWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                alternate-background-color: #f9f9f9;
                gridline-color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                border: none;
                border-right: 1px solid #cccccc;
                border-bottom: 1px solid #cccccc;
            }
        """)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # Search bar at the top (more prominent)
        search_container = QtWidgets.QWidget()
        search_layout = QtWidgets.QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.returnPressed.connect(self.perform_search)
        self.search_input.setMinimumHeight(36)
        font = self.search_input.font()
        font.setPointSize(font.pointSize() + 1)
        self.search_input.setFont(font)
        
        search_button = QtWidgets.QPushButton("Search")
        search_button.clicked.connect(self.perform_search)
        search_button.setMinimumHeight(36)
        
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(search_button, 0)
        
        main_layout.addWidget(search_container)
        
        # Search options in collapsible panel
        options_group = QtWidgets.QGroupBox("Search Options")
        options_layout = QtWidgets.QVBoxLayout(options_group)
        
        # Options container
        options_container = QtWidgets.QWidget()
        options_grid = QtWidgets.QGridLayout(options_container)
        options_grid.setContentsMargins(0, 0, 0, 0)
        
        # Node type filter (first row)
        options_grid.addWidget(QtWidgets.QLabel("Node Type:"), 0, 0)
        self.node_type_combo = QtWidgets.QComboBox()
        self.node_type_combo.addItem("All Types", None)
        options_grid.addWidget(self.node_type_combo, 0, 1)
        
        # Search fields (second row)
        field_widget = QtWidgets.QWidget()
        field_layout = QtWidgets.QHBoxLayout(field_widget)
        field_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_title_check = QtWidgets.QCheckBox("Title/Name")
        self.search_title_check.setChecked(True)
        self.search_content_check = QtWidgets.QCheckBox("Content")
        self.search_content_check.setChecked(True)
        self.search_tags_check = QtWidgets.QCheckBox("Tags")
        self.search_tags_check.setChecked(True)
        
        field_layout.addWidget(QtWidgets.QLabel("Search in:"))
        field_layout.addWidget(self.search_title_check)
        field_layout.addWidget(self.search_content_check)
        field_layout.addWidget(self.search_tags_check)
        field_layout.addStretch()
        
        options_grid.addWidget(field_widget, 1, 0, 1, 2)
        
        # Additional options (third row)
        options_widget = QtWidgets.QWidget()
        options_secondary_layout = QtWidgets.QHBoxLayout(options_widget)
        options_secondary_layout.setContentsMargins(0, 0, 0, 0)
        
        self.case_sensitive_check = QtWidgets.QCheckBox("Case Sensitive")
        self.exact_match_check = QtWidgets.QCheckBox("Exact Match")
        
        options_secondary_layout.addWidget(QtWidgets.QLabel("Options:"))
        options_secondary_layout.addWidget(self.case_sensitive_check)
        options_secondary_layout.addWidget(self.exact_match_check)
        options_secondary_layout.addStretch()
        
        options_grid.addWidget(options_widget, 2, 0, 1, 2)
        
        options_layout.addWidget(options_container)
        main_layout.addWidget(options_group)
        
        # Results section
        results_container = QtWidgets.QWidget()
        results_layout = QtWidgets.QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(8)
        
        # Results header
        results_header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(results_header)
        header_layout.setContentsMargins(2, 2, 2, 2)
        
        results_title = QtWidgets.QLabel("Search Results")
        results_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.results_count_label = QtWidgets.QLabel("No results")
        
        header_layout.addWidget(results_title)
        header_layout.addStretch()
        header_layout.addWidget(self.results_count_label)
        
        results_layout.addWidget(results_header)
        
        # Results table - simplified columns
        self.results_table = QtWidgets.QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Type", "Title", "Preview"])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setStyleSheet("QTableWidget { border: none; }")
        self.results_table.cellDoubleClicked.connect(self.navigate_to_result)
        
        # Set column properties
        self.results_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Type
        self.results_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)      # Title
        self.results_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)          # Preview
        
        # Set custom delegate for better rendering
        self.results_table.setItemDelegate(ResultItemDelegate())
        
        results_layout.addWidget(self.results_table)
        
        # Status bar for additional info
        self.status_bar = QtWidgets.QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        results_layout.addWidget(self.status_bar)
        
        main_layout.addWidget(results_container, 1)  # Give results area more space
        
        # Populate node types
        self.populate_node_types()
        
        # Initially hide the status bar
        self.status_bar.hide()
        
        # Store the currently selected row for status bar updates
        self.results_table.itemSelectionChanged.connect(self.update_status_bar)
    
    def populate_node_types(self):
        """Populate the node type dropdown with available types."""
        async def fetch_node_types():
            try:
                success, content, error = await self.main_window.communication.request_and_get_response(
                    operation="get_node_types",
                    params={},
                    sender="Frontend"
                )
                
                if success and content and content.get("result"):
                    node_types = content["result"]
                    # Clear previous items except "All Types"
                    while self.node_type_combo.count() > 1:
                        self.node_type_combo.removeItem(1)
                    
                    # Add node types to dropdown
                    for node_type_id, type_data in node_types.items():
                        self.node_type_combo.addItem(type_data.get("name", node_type_id), node_type_id)
                    
                    logger.info(f"Populated {self.node_type_combo.count()-1} node types in search dropdown")
                else:
                    logger.error(f"Error fetching node types: {error}")
            except Exception as e:
                logger.error(f"Error populating node types: {e}")
        
        # Start async task to fetch node types
        asyncio.create_task(fetch_node_types())
    
    def perform_search(self):
        """Perform search based on current inputs."""
        search_term = self.search_input.text().strip()
        if not search_term:
            QtWidgets.QMessageBox.warning(self, "Search", "Please enter a search term.")
            return
        
        # Get search parameters
        node_type = self.node_type_combo.currentData()
        search_in_content = self.search_content_check.isChecked()
        search_in_title = self.search_title_check.isChecked()
        search_in_tags = self.search_tags_check.isChecked()
        case_sensitive = self.case_sensitive_check.isChecked()
        exact_match = self.exact_match_check.isChecked()
        
        # Create search params
        search_params = {
            "term": search_term,
            "node_type": node_type,
            "in_content": search_in_content,
            "in_title": search_in_title,
            "in_tags": search_in_tags,
            "case_sensitive": case_sensitive,
            "exact_match": exact_match
        }
        
        # Start the search
        asyncio.create_task(self.run_search(search_params))
    
    async def run_search(self, search_params: dict):
        """Execute the search operation asynchronously."""
        # Get the graph if not provided through search params
        if not hasattr(self.main_window, 'graph') or not self.main_window.graph:
            QtWidgets.QMessageBox.warning(self, "Search", "No graph loaded.")
            return
        
        # Show loading indicator
        self.results_count_label.setText("Searching...")
        QtWidgets.QApplication.processEvents()  # Force UI update
        
        try:
            # Perform the search with the graph in memory
            results = await self.search_graph(self.main_window.graph, search_params)
            
            # Display the results
            self.display_search_results(results)
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            self.results_count_label.setText(f"Error: {e}")
            # Clear results table
            self.results_table.setRowCount(0)
    
    async def search_graph(self, graph, search_params: dict) -> List[Dict[str, Any]]:
        """Search the graph based on parameters."""
        results = []
        term = search_params["term"]
        node_type = search_params["node_type"]
        case_sensitive = search_params["case_sensitive"]
        exact_match = search_params["exact_match"]
        
        # Normalize search term if not case sensitive
        if not case_sensitive:
            term = term.lower()
        
        # Iterate through all nodes
        for node_id, node_data in graph.nodes(data=True):
            # Filter by node type if specified
            if node_type and node_data.get("node_type") != node_type:
                continue
            
            # Search in different fields
            matches = []
            score = 0
            preview_text = ""  # Initialize preview text
            
            # Helper function for comparing strings
            def check_match(text, field_name):
                nonlocal preview_text
                if text is None:
                    return False, 0, ""
                
                if not isinstance(text, str):
                    text = str(text)
                
                original_text = text  # Keep the original text for preview
                if not case_sensitive:
                    text = text.lower()
                
                if exact_match:
                    is_match = term == text
                    match_score = 100 if is_match else 0
                    # For exact match, use the whole string as preview
                    match_preview = original_text if is_match else ""
                else:
                    is_match = term in text
                    # Calculate score based on match position and text length
                    if is_match:
                        pos = text.find(term)
                        length_factor = len(term) / max(1, len(text))
                        pos_factor = 1 - (pos / max(1, len(text)))
                        match_score = int(50 * length_factor + 50 * pos_factor)
                        
                        # Extract context for preview (30 chars before and after the match)
                        orig_pos = original_text.lower().find(term.lower()) if not case_sensitive else original_text.find(term)
                        start_pos = max(0, orig_pos - 30)
                        end_pos = min(len(original_text), orig_pos + len(term) + 30)
                        
                        # Create preview with highlighting
                        if start_pos > 0:
                            prefix = "..." + original_text[start_pos:orig_pos]
                        else:
                            prefix = original_text[start_pos:orig_pos]
                            
                        highlight = original_text[orig_pos:orig_pos + len(term)]
                        
                        if end_pos < len(original_text):
                            suffix = original_text[orig_pos + len(term):end_pos] + "..."
                        else:
                            suffix = original_text[orig_pos + len(term):end_pos]
                        
                        match_preview = f"{prefix}[{highlight}]{suffix}"
                    else:
                        match_score = 0
                        match_preview = ""
                
                if is_match and match_preview:
                    if preview_text:
                        preview_text += " ... "
                    preview_text += f"{field_name}: {match_preview}"
                
                return is_match, match_score, match_preview
            
            # Check title/name
            if search_params["in_title"]:
                # Try different name fields
                for field in ["title", "name", "label"]:
                    if field in node_data:
                        match, field_score, preview = check_match(node_data[field], field)
                        if match:
                            matches.append(field)
                            score = max(score, field_score)
            
            # Check content
            if search_params["in_content"] and "content" in node_data:
                match, content_score, preview = check_match(node_data["content"], "content")
                if match:
                    matches.append("content")
                    score = max(score, content_score)
            
            # Check tags
            if search_params["in_tags"] and "tags" in node_data:
                match, tags_score, preview = check_match(node_data["tags"], "tags")
                if match:
                    matches.append("tags")
                    score = max(score, tags_score)
            
            # If we found matches, add to results
            if matches:
                result = {
                    "node_id": str(node_id),
                    "node_data": node_data.copy(),  # Copy to avoid modifying original
                    "matches": matches,
                    "score": score,
                    "node_type": node_data.get("node_type", "unknown"),
                    "name": node_data.get("title", node_data.get("name", node_data.get("label", str(node_id)))),
                    "preview": preview_text  # Add the preview text
                }
                results.append(result)
        
        # Sort results by score (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Add a small delay to ensure UI is responsive
        await asyncio.sleep(0.1)
        
        return results
    
    def display_search_results(self, results: List[Dict[str, Any]]):
        """Display search results in the table with improved visual presentation."""
        self.search_results = results
        self.results_table.setRowCount(len(results))
        
        if not results:
            self.results_count_label.setText("No matching results found")
            self.status_bar.hide()
            return
        
        self.results_count_label.setText(f"Found {len(results)} result(s)")
        
        # Populate table with simplified columns
        for row, result in enumerate(results):
            # Type column - kept smaller
            type_item = QtWidgets.QTableWidgetItem(result["node_type"].title())
            type_item.setData(Qt.ItemDataRole.UserRole, result["node_id"])
            self.results_table.setItem(row, 0, type_item)
            
            # Title column - more prominent
            name_item = QtWidgets.QTableWidgetItem(result["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, result["node_id"])
            self.results_table.setItem(row, 1, name_item)
            
            # Preview column - matches with context
            preview_text = result.get("preview", "")
            preview_item = QtWidgets.QTableWidgetItem(preview_text)
            preview_item.setData(Qt.ItemDataRole.UserRole, result["node_id"])
            preview_item.setToolTip(preview_text)
            self.results_table.setItem(row, 2, preview_item)
        
        # Adjust row heights for better readability
        for row in range(len(results)):
            self.results_table.setRowHeight(row, 44)
        
        # Set reasonable widths for columns
        table_width = self.results_table.viewport().width()
        self.results_table.setColumnWidth(1, min(int(table_width * 0.3), 200))  # Title column around 30%
    
    def navigate_to_result(self, row, column):
        """Navigate to the selected search result."""
        if row < 0 or row >= len(self.search_results):
            return
        
        node_id = self.search_results[row]["node_id"]
        logger.info(f"Navigating to search result: {node_id}")
        
        # Switch to graph tab and highlight the node
        self.main_window.switch_to_graph_tab_and_highlight_node(uuid.UUID(node_id))
        
        # Also show detailed info for the node
        from ResearchGuidePackage.FrontendModule.link_handler import show_node_info
        show_node_info(self.main_window, uuid.UUID(node_id))
    
    def refresh(self):
        """Refresh the search tool (e.g., when graph changes)."""
        # Clear search results
        self.results_table.setRowCount(0)
        self.results_count_label.setText("No results")
        
        # Update node types
        self.populate_node_types()
        
        # If there was a previous search term, re-run the search
        if self.search_input.text().strip():
            self.perform_search()
    
    def update_status_bar(self):
        """Update status bar with details of the selected result."""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_bar.hide()
            return
            
        row = selected_rows[0].row()
        if row >= 0 and row < len(self.search_results):
            result = self.search_results[row]
            
            # Show match details and score
            matches = ", ".join(result["matches"])
            score = result["score"]
            self.status_bar.showMessage(f"Matched in: {matches} | Score: {score}")
            self.status_bar.show()
        else:
            self.status_bar.hide()
