from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMenu, QSlider, QHBoxLayout, QVBoxLayout, QWidget
from PyQt6.QtGui import QAction
import logging
import asyncio

logger = logging.getLogger('VisualizationControls')

class VisualizationControls(QWidget):
    """A widget containing visualization-specific controls."""
    def __init__(self, main_window, canvas):
        """Initialize VisualizationControls."""
        super().__init__()
        self.main_window = main_window
        self.canvas = canvas
        self.filter_menu = None  # Initialize filter_menu
        
        # Create the layout and add controls
        self.init_ui()
        
        # Start populating the node type filters
        if self.filter_menu:
            asyncio.create_task(self.populate_node_type_filters(self.filter_menu))
        
        logger.info("Visualization controls initialized.")
    
    def init_ui(self):
        """Initialize the UI components."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Add Node Type Filter button with dropdown menu
        filter_button = QtWidgets.QPushButton("Filter Types", self)
        filter_button.setToolTip("Show/hide different node types")
        main_layout.addWidget(filter_button)
        
        # Create the filter menu
        self.filter_menu = QMenu(filter_button)
        filter_button.setMenu(self.filter_menu)
        
        # Add "All Types" and "No Types" actions
        select_all_action = QAction("Show All Types", self.filter_menu)
        select_none_action = QAction("Hide All Types", self.filter_menu)
        
        self.filter_menu.addAction(select_all_action)
        self.filter_menu.addAction(select_none_action)
        self.filter_menu.addSeparator()
        
        # Connect actions
        select_all_action.triggered.connect(lambda: self.canvas.set_all_node_types_visible(True))
        select_none_action.triggered.connect(lambda: self.canvas.set_all_node_types_visible(False))
        
        # Add text block stickiness control
        main_layout.addSpacing(10)  # Add some space between controls
        
        sticky_label = QLabel("Text Block Stickiness:", self)
        main_layout.addWidget(sticky_label)
        
        stickiness_slider = QSlider(Qt.Orientation.Horizontal, self)
        stickiness_slider.setRange(0, 100)
        stickiness_slider.setValue(int(self.canvas.text_block_stickiness * 100))
        stickiness_slider.setFixedWidth(120)
        stickiness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        stickiness_slider.setTickInterval(20)
        stickiness_slider.setToolTip("Control how closely text blocks stick to their pages")
        
        if self.canvas:
            # Connect slider
            stickiness_slider.valueChanged.connect(lambda value: self.canvas.set_text_block_stickiness(value / 100.0))
        
        main_layout.addWidget(stickiness_slider)
        
        # Add stretch at the end to push everything to the left in visualization container
        main_layout.addStretch(1)
        
        # Set the layout
        self.setLayout(main_layout)
    
    async def populate_node_type_filters(self, filter_menu):
        """Populate the node type filter menu."""
        try:
            # Wait for the canvas to fetch node types first
            await self.canvas.fetch_node_type_colors()
            
            # Create checkable menu items for each node type
            for node_type, color in self.canvas.node_type_colors.items():
                # Create action with proper type name and make it checkable
                display_name = node_type.title()
                
                action = QAction(display_name, filter_menu)
                action.setCheckable(True)
                action.setChecked(True)  # All types visible by default
                
                # Store node type in user data
                action.setData(node_type)
                
                # Connect toggle action
                action.toggled.connect(lambda checked, nt=node_type: self.canvas.set_node_type_visibility(nt, checked))
                
                # Add to menu
                filter_menu.addAction(action)
            
            logger.info(f"Added {len(self.canvas.node_type_colors)} node types to filter menu")
        except Exception as e:
            logger.error(f"Error setting up node type filters: {e}")
