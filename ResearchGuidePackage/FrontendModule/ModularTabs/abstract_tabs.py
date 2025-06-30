"""
Content Tab Widget
================
A tab widget that manages multiple content tabs, allowing users to
open different types of content (pages, namespaces, search, etc.) simultaneously.
"""
import logging
from PyQt6.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QPushButton, 
                            QHBoxLayout, QLabel, QScrollArea, QStackedWidget, 
                            QSplitter, QSizePolicy, QApplication, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QObject, QUuid, QTimer
from PyQt6.QtGui import QIcon
from ResearchGuidePackage.FrontendModule.ModularTabs.page_editor import PageEditor
from ResearchGuidePackage.FrontendModule.ModularTabs.content_selector import ContentSelector
from ResearchGuidePackage.FrontendModule.ModularTabs.namespaces_view import NamespacesView
from ResearchGuidePackage.FrontendModule.search_tool import SearchTool
from ResearchGuidePackage.FrontendModule.ModularTabs.discover_tab import GraphTab
from ResearchGuidePackage.FrontendModule.ModularTabs.documentation_view import DocumentationView
from ResearchGuidePackage.FrontendModule.ModularTabs.birdview_tab import BirdViewTab
from ResearchGuidePackage.FrontendModule.ModularTabs.databases_page import DatabasesPage  # Add this import
import os
import asyncio

logger = logging.getLogger('ContentTabWidget')

class TabInfo:
    """Simple class to store tab information."""
    def __init__(self, content_type="selector", data=None):
        self.content_type = content_type  # "selector", "page", "namespaces", "search"
        self.data = data  # Additional data (e.g., node_id for pages)

class ContentTabWidget(QWidget):
    """Widget for managing multiple content tabs in tabs or side-by-side"""
    
    def __init__(self, main_window):
        """Initialize the widget."""
        super().__init__()
        self.main_window = main_window
        self.content_tabs = []
        self.active_tab = None  # Track the active tab
        
        # Layout mode: 'tabs' or 'side_by_side'
        self.layout_mode = 'tabs'
        
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create stacked widget to hold both views
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # Connect the current changed signal to update highlighting
        self.tab_widget.currentChanged.connect(self.update_active_tab_highlight)
        
        # Remove custom stylesheet to restore standard Qt look
        
        # Add button to tab widget as corner widget
        self.setup_tab_corner_widget()
        
        self.stacked_widget.addWidget(self.tab_widget)
        
        # Create side-by-side widget
        self.create_side_by_side_widget()
        
        # Always start with one content selector tab
        self.add_content_tab()
        
        # Install global event filter to track ALL mouse clicks
        QApplication.instance().installEventFilter(self)
    
    def setup_tab_corner_widget(self):
        """Set up the corner widget for the tab widget."""
        corner_widget = QWidget()
        layout = QHBoxLayout(corner_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add button
        add_button = QPushButton("+")
        add_button.setToolTip("Add new content tab")
        add_button.setMaximumWidth(30)
        add_button.clicked.connect(self.add_content_tab)
        layout.addWidget(add_button)
        
        # Layout toggle button with symbol
        self.toggle_layout_button = QPushButton("◫")  # Symbol representing side-by-side
        self.toggle_layout_button.setToolTip("Toggle between tabbed and side-by-side layout")
        self.toggle_layout_button.setMaximumWidth(30)
        self.toggle_layout_button.clicked.connect(self.toggle_layout)
        layout.addWidget(self.toggle_layout_button)
        
        # Set corner widget
        self.tab_widget.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)
    
    def create_side_by_side_widget(self):
        """Create the widget for side-by-side layout."""
        # Create container widget
        side_by_side_container = QWidget()
        container_layout = QVBoxLayout(side_by_side_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a splitter for side-by-side layout
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)  # Don't allow tabs to be completely collapsed
        
        # Add the splitter directly to the container
        container_layout.addWidget(self.splitter)
        
        # Add the container to the stacked widget
        self.stacked_widget.addWidget(side_by_side_container)
        
        # Initialize dictionary to store individual tab widgets
        self.tab_widget_dict = {}
    
    def toggle_layout(self):
        """Toggle between tabbed and side-by-side layout, preserving tab order."""
        previous_active_tab = self.active_tab # Preserve to restore selection

        if self.layout_mode == 'tabs':
            # Switching from 'tabs' to 'side_by_side'
            self.layout_mode = 'side_by_side'
            
            # 1. Capture the current visual order of tabs from self.tab_widget
            ordered_tabs_from_widget = []
            for i in range(self.tab_widget.count()):
                ordered_tabs_from_widget.append(self.tab_widget.widget(i))
            
            # 2. Update self.content_tabs to this visual order. This list will be used by rebuild_side_by_side_view.
            self.content_tabs = ordered_tabs_from_widget
            
            # 3. Clear self.tab_widget. Content widgets are still referenced in self.content_tabs.
            while self.tab_widget.count() > 0:
                self.tab_widget.removeTab(0) # removeTab unparents the widget
            
            # 4. Rebuild the side-by-side view. It uses self.content_tabs.
            self.rebuild_side_by_side_view() 
            
            self.stacked_widget.setCurrentIndex(1) # Show side-by-side view

        else: # Switching from 'side_by_side' to 'tabs'
            self.layout_mode = 'tabs'
            
            # self.content_tabs should already reflect the visual order of the splitter panes.
            # rebuild_side_by_side_view populates the splitter based on self.content_tabs,
            # and close_side_by_side_tab maintains this list's integrity.

            # 1. Clear existing QTabWidget containers from the splitter and self.tab_widget_dict.
            #    Content tabs are preserved in self.content_tabs.
            self.tab_widget_dict.clear() # Clear the mapping
            while self.splitter.count() > 0:
                scroll_area = self.splitter.widget(0) # Get the first widget (QScrollArea)
                if scroll_area:
                    scroll_area.setParent(None) # Detach from splitter
                    container_tab_widget = scroll_area.widget() # This is the QTabWidget inside scroll_area
                    if container_tab_widget:
                        # Detach the content tab from this container_tab_widget.
                        # The content tab itself is already in self.content_tabs and won't be deleted.
                        if container_tab_widget.count() > 0:
                            container_tab_widget.removeTab(0) 
                        container_tab_widget.deleteLater() # Schedule the container for deletion
                    scroll_area.deleteLater() # Schedule the scroll area for deletion
            
            # 2. Clear the main tab_widget
            self.tab_widget.clear()
            
            # 3. Add content tabs (which are in splitter order) to the main tab_widget
            for tab_content in self.content_tabs:
                if self._is_deleted_object(tab_content): # Safety check
                    logger.warning(f"Skipping deleted tab {tab_content} when switching to tabs mode.")
                    continue
                
                title = "Tab"
                if hasattr(tab_content, 'get_tab_title') and callable(tab_content.get_tab_title):
                    try:
                        title = tab_content.get_tab_title()
                    except Exception: # pylint: disable=broad-except
                        pass # Keep default title "Tab"
                self.tab_widget.addTab(tab_content, title)
            
            self.stacked_widget.setCurrentIndex(0) # Show tabbed view

        # Restore active tab selection if possible
        if previous_active_tab and previous_active_tab in self.content_tabs and not self._is_deleted_object(previous_active_tab):
            self.active_tab = previous_active_tab
        elif self.content_tabs: # Fallback to first tab if previous_active_tab is invalid
            self.active_tab = self.content_tabs[0]
        else:
            self.active_tab = None

        # Update UI based on the new active tab and mode
        if self.layout_mode == 'tabs':
            if self.active_tab:
                try:
                    idx = self.content_tabs.index(self.active_tab) # self.content_tabs matches self.tab_widget order here
                    self.tab_widget.setCurrentIndex(idx) # This will trigger currentChanged and update_active_tab_highlight
                except ValueError: # Should not happen if active_tab is in content_tabs
                    if self.tab_widget.count() > 0: self.tab_widget.setCurrentIndex(0)
            elif self.tab_widget.count() > 0: # If no active_tab but tabs exist
                 self.tab_widget.setCurrentIndex(0)
            self.setup_tab_corner_widget() # Ensure corner widget is on the main tab_widget
        else: # side_by_side mode
            # rebuild_side_by_side_view handles setting focus and highlight for the active_tab
            # but we call update_side_by_side_buttons to ensure corner widget is correct.
            self.tab_widget.setCornerWidget(None) # Remove from main tab_widget if it was there
            self.update_side_by_side_buttons() 
            if self.active_tab: # Ensure highlight is applied if rebuild didn't catch it or if active_tab changed
                self.update_active_tab_highlight_side_by_side(None, self.active_tab)


        logger.info(f"Toggled to {self.layout_mode} mode with {len(self.content_tabs)} tabs. Active: {self.active_tab}")
    
    def update_side_by_side_buttons(self):
        """Update the control buttons in side-by-side mode to appear on the rightmost tab."""
        # First remove corner widgets from all tab widgets
        for i in range(self.splitter.count()):
            scroll_area = self.splitter.widget(i)
            if isinstance(scroll_area, QScrollArea):
                tab_widget = scroll_area.widget()
                if isinstance(tab_widget, QTabWidget):
                    tab_widget.setCornerWidget(None)
        
        # Now add buttons to the rightmost tab widget
        rightmost_index = self.splitter.count() - 1
        if (rightmost_index >= 0):  # Make sure there's at least one tab
            rightmost_scroll_area = self.splitter.widget(rightmost_index)
            if isinstance(rightmost_scroll_area, QScrollArea):
                rightmost_tab_widget = rightmost_scroll_area.widget()
                if isinstance(rightmost_tab_widget, QTabWidget):
                    # Create corner widget for buttons
                    corner_widget = QWidget()
                    layout = QHBoxLayout(corner_widget)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    # Add button
                    add_button = QPushButton("+")
                    add_button.setToolTip("Add new content tab")
                    add_button.setMaximumWidth(30)
                    add_button.clicked.connect(self.add_content_tab)
                    layout.addWidget(add_button)
                    
                    # Layout toggle button with symbol
                    toggle_button = QPushButton("◩")  # Symbol representing tabs
                    toggle_button.setToolTip("Switch to tabbed view")
                    toggle_button.setMaximumWidth(30)
                    toggle_button.clicked.connect(self.toggle_layout)
                    layout.addWidget(toggle_button)
                    
                    # Set corner widget
                    rightmost_tab_widget.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)
                    
                    # Ensure it's visible
                    corner_widget.show()
    
    def distribute_splitter_sizes(self):
        """Distribute the splitter sizes evenly among all tab widgets."""
        if self.splitter.count() > 0:
            # Calculate the total width available
            total_width = self.splitter.width()
            # Distribute evenly
            width_per_widget = total_width // self.splitter.count()
            # Set sizes
            self.splitter.setSizes([width_per_widget] * self.splitter.count())
    
    def resizeEvent(self, event):
        """Handle resize events to redistribute splitter sizes."""
        super().resizeEvent(event)
        if self.layout_mode == 'side_by_side':
            self.distribute_splitter_sizes()
    
    def close_side_by_side_tab(self, tab_widget_container, index):
        """Close a tab in side-by-side mode and replace with content selector if it's the last one.
        tab_widget_container is the QTabWidget holding the actual content tab.
        """
        try:
            tab_to_close = tab_widget_container.widget(index)
            if not tab_to_close:
                logger.warning("No tab found at this index to close.")
                return

            logger.info(f"Attempting to close tab: {tab_to_close.__class__.__name__}")

            if len(self.content_tabs) > 1:
                # Standard behavior for multiple tabs
                was_active = (self.active_tab == tab_to_close)
                
                if tab_to_close in self.content_tabs:
                    self.content_tabs.remove(tab_to_close)
                
                if tab_to_close in self.tab_widget_dict:
                    del self.tab_widget_dict[tab_to_close]

                if was_active:
                    self.active_tab = self.content_tabs[0] if self.content_tabs else None

                # Remove tab from its QTabWidget container
                tab_widget_container.removeTab(index)
                
                # Handle empty QTabWidget container
                if tab_widget_container.count() == 0:
                    scroll_area_to_remove = None
                    # Find the QScrollArea that parents this empty tab_widget_container
                    for i in range(self.splitter.count()):
                        widget = self.splitter.widget(i)
                        if isinstance(widget, QScrollArea) and widget.widget() == tab_widget_container:
                            scroll_area_to_remove = widget
                            break
                    
                    if scroll_area_to_remove:
                        scroll_area_to_remove.setParent(None) # Remove from splitter
                        # Schedule the now-empty container and its scroll area for deletion
                        tab_widget_container.deleteLater()
                        scroll_area_to_remove.deleteLater()
                        logger.info("Removed empty tab container and its scroll area.")

                # Rebuild side-by-side view to reflect changes
                QTimer.singleShot(0, self.rebuild_side_by_side_view)

                logger.info(f"Closed side-by-side tab. Remaining tabs: {len(self.content_tabs)}")
            else:
                # For the last tab, replace it with a content selector instead of closing
                logger.info("Replacing last tab with a content selector")
                
                # Create a new content selector
                content_selector = self._create_content_selector()
                
                # Replace the tab content at the current index in the container
                tab_widget_container.removeTab(index)
                tab_widget_container.insertTab(index, content_selector, "Choose...")
                tab_widget_container.setCurrentIndex(index)
                
                # Create a new mapping in tab_widget_dict
                self.tab_widget_dict[content_selector] = tab_widget_container
                
                # Update the content tabs list
                self.content_tabs = [content_selector]
                
                # Update active tab
                self.active_tab = content_selector
                
                # If the old tab was in tab_widget_dict, remove it
                if tab_to_close in self.tab_widget_dict:
                    del self.tab_widget_dict[tab_to_close]

        except Exception as e:
            logger.error(f"Error in close_side_by_side_tab: {e}", exc_info=True)
            # Attempt a full rebuild as a recovery measure
            QTimer.singleShot(0, self.rebuild_side_by_side_view)
    
    def _create_tab_by_type(self, content_type, data=None):
        """Create a tab of the specified type with optional data."""
        if content_type == "page":
            tab = PageEditor(self.main_window)
            if data:  # If we have a node ID
                # Store the node ID for later selection
                tab.current_node_id = data
        elif content_type == "namespaces":
            tab = NamespacesView(self.main_window)
        elif content_type == "search":
            tab = SearchTool(self.main_window)
        elif content_type == "documentation":
            tab = DocumentationView(self.main_window)
        elif content_type == "birdview":
            tab = BirdViewTab()
            tab.set_main_window(self.main_window)
        elif content_type == "databases":
            tab = DatabasesPage(self.main_window)
        elif content_type == "transcribe":
            # Import transcribe tab only when needed
            from ResearchGuidePackage.FrontendModule.ModularTabs.transcribe_tab import TranscribeTab
            tab = TranscribeTab(self.main_window)
        elif content_type == "import_export":
            # Import the new ImportExportPage
            from ResearchGuidePackage.FrontendModule.ModularTabs.import_export_page import ImportExportPage
            tab = ImportExportPage(self.main_window)
        elif content_type == "discover":
            # Create a graph tab with discover mode - handle passing state if needed
            if isinstance(data, dict) and 'focus_node' in data:
                # This is a state restoration situation
                logger.info(f"Creating discover tab with state: focus={data.get('focus_node')}")
                tab = self._create_discover_tab(state=data)
            else:
                tab = self._create_discover_tab()
        else:  # Default to content selector
            tab = self._create_content_selector()
            
        return tab
    
    def _create_discover_tab(self, state=None):
        """Create a graph tab specifically for discover mode."""
        # Create graph tab with appropriate main_window
        tab = GraphTab(self)
        
        # Reference the main window for proper toolbar creation
        tab.main_window = self.main_window
        
        # Set up the toolbar to ensure graph is loaded
        tab.set_toolbar(self.main_window)
        
        # Force a refresh to ensure graph is loaded - keep a local copy
        if hasattr(self.main_window, 'graph') and self.main_window.graph:
            try:
                # Always copy the graph for independence
                graph_copy = self.main_window.graph.copy()
                tab.update_graph(graph_copy)
            except Exception as e:
                logger.error(f"Error copying graph: {e}")
                # Fallback to direct reference if copy fails
                tab.update_graph(self.main_window.graph)
        
        # If we have state from a previous tab version, restore it
        if state:
            tab.restore_state_from_rebuild(state)
        
        return tab
    
    def _create_content_selector(self):
        """Create a new content selector with connected signals."""
        selector = ContentSelector(self.main_window)
        # Update the signal-slot connection to include the source tab parameter
        selector.content_selected.connect(self._on_content_selected)
        return selector
    
    def add_content_tab(self):
        """Add a new content selection tab."""
        new_tab_title = "Choose..." # Default title for new selector tabs
        content_selector = self._create_content_selector()
        self.content_tabs.append(content_selector)
        self.active_tab = content_selector # New tab becomes active

        if self.layout_mode == 'tabs':
            tab_index = self.tab_widget.addTab(content_selector, new_tab_title)
            self.tab_widget.setCurrentIndex(tab_index)
        else: # side_by_side mode
            # Create a new QTabWidget container for this new content_selector
            container_tab_widget = QTabWidget()
            container_tab_widget.setTabsClosable(True)
            container_tab_widget.setMovable(False) # Usually, individual tabs in side-by-side are not movable
            container_tab_widget.tabCloseRequested.connect(
                lambda index, tw=container_tab_widget: self.close_side_by_side_tab(tw, index)
            )
            
            container_tab_widget.addTab(content_selector, new_tab_title)
            self.tab_widget_dict[content_selector] = container_tab_widget
            
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll_area.setWidget(container_tab_widget)
            
            self.splitter.addWidget(scroll_area)
            
            self.update_side_by_side_buttons()
            self.distribute_splitter_sizes()
        
        logger.info(f"Added new content tab (total: {len(self.content_tabs)}) with title '{new_tab_title}'")
        return content_selector # Return the actual content widget
    
    def rebuild_side_by_side_view(self):
        """Rebuild side-by-side view after changes."""
        if self.layout_mode != 'side_by_side':
            return

        logger.info("Rebuilding side-by-side view...")
        try:
            current_active_content_tab = self.active_tab

            # 1. Clear tab_widget_dict (mapping content to its QTabWidget container)
            self.tab_widget_dict.clear()

            # 2. Clear the splitter: Detach and deleteLater existing scroll areas and their QTabWidget children
            while self.splitter.count() > 0:
                scroll_area = self.splitter.widget(0) 
                if scroll_area:
                    scroll_area.setParent(None) 
                    inner_tab_widget = scroll_area.widget()
                    if inner_tab_widget:
                        # Important: Detach content widgets from their old container before deleting the container
                        while inner_tab_widget.count() > 0:
                            inner_tab_widget.removeTab(0) # Content itself is not deleted
                        inner_tab_widget.deleteLater()
                    scroll_area.deleteLater()
            
            logger.info(f"Splitter cleared. Rebuilding with {len(self.content_tabs)} content tabs.")

            # Filter self.content_tabs to remove any deleted objects before rebuilding
            valid_content_tabs = []
            for content_tab_widget in list(self.content_tabs): # Iterate over a copy
                if self._is_deleted_object(content_tab_widget):
                    logger.warning(f"Skipping deleted content tab during rebuild: {content_tab_widget}")
                else:
                    valid_content_tabs.append(content_tab_widget)
            self.content_tabs = valid_content_tabs

            # 3. Re-populate the splitter with new containers for each valid content_tab_widget
            for content_tab_widget in self.content_tabs:
                # Create a new QTabWidget container
                container_tab_widget = QTabWidget()
                container_tab_widget.setTabsClosable(True)
                container_tab_widget.setMovable(False)
                container_tab_widget.tabCloseRequested.connect(
                    lambda index, tw=container_tab_widget: self.close_side_by_side_tab(tw, index)
                )

                title = "Tab"
                if hasattr(content_tab_widget, 'get_tab_title') and callable(content_tab_widget.get_tab_title):
                    try:
                        title = content_tab_widget.get_tab_title()
                    except Exception as e_title:
                        logger.warning(f"Error getting tab title for {content_tab_widget}: {e_title}")
                
                container_tab_widget.addTab(content_tab_widget, title) # Add content to its new container
                self.tab_widget_dict[content_tab_widget] = container_tab_widget

                # Create a new QScrollArea for this container_tab_widget
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
                scroll_area.setWidget(container_tab_widget)
                
                self.splitter.addWidget(scroll_area)

            # 4. Restore active tab focus
            self.active_tab = None # Reset before trying to set
            if current_active_content_tab and current_active_content_tab in self.content_tabs and not self._is_deleted_object(current_active_content_tab):
                self.active_tab = current_active_content_tab
            elif self.content_tabs: # Fallback if previous active tab is gone or invalid
                self.active_tab = self.content_tabs[0]
            
            if self.active_tab:
                 if self.active_tab in self.tab_widget_dict: # Ensure its container exists
                    self.tab_widget_dict[self.active_tab].setCurrentWidget(self.active_tab)
                 self.active_tab.setFocus() 
                 self.update_active_tab_highlight_side_by_side(None, self.active_tab)


            # 5. Update UI elements
            self.update_side_by_side_buttons()
            self.distribute_splitter_sizes()
            logger.info("Side-by-side view rebuilt successfully.")

        except Exception as e:
            logger.error(f"Error in rebuild_side_by_side_view: {e}", exc_info=True)
    
    def _is_deleted_object(self, obj):
        """Check if a Qt object has been deleted."""
        try:
            # Try to access a property that all QWidgets have
            if obj is None:
                return True
            # Just checking if the object exists and can be accessed is enough
            # This will raise an exception if the object has been deleted
            obj.isVisible()  # This will fail if object is deleted
            return False
        except RuntimeError:
            return True
        except Exception:
            # Any other exception means the object is not usable
            return True
            
    def eventFilter(self, watched, event):
        """Global event filter to track mouse clicks."""
        # Only track mouse press events
        if event.type() == QEvent.Type.MouseButtonPress:
            # Check which tab contains the click
            for tab in self.content_tabs:
                # Get global click position
                global_pos = event.globalPosition().toPoint()
                
                # Convert to tab's coordinate space
                tab_pos = tab.mapFromGlobal(global_pos)
                
                # Check if click is within tab
                if tab.rect().contains(tab_pos):
                    # This tab was clicked
                    if self.active_tab != tab:
                        prev_active = self.active_tab
                        self.active_tab = tab
                        logger.info(f"Mouse click detected in tab {id(tab)}, setting as active")
                        
                        # Update highlighting in side-by-side mode
                        if self.layout_mode == 'side_by_side':
                            self.update_active_tab_highlight_side_by_side(prev_active, tab)
                    break
                    
        # Let the event continue
        return False

    def update_active_tab_highlight(self, index=None):
        """Update the visual highlighting for the active tab in tabbed mode."""
        if self.layout_mode != 'tabs':
            return
            
        # In tabbed mode, the QTabWidget handles the visual highlighting
        # We just need to make sure the active_tab reference is updated
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            self.active_tab = current_tab
            
    def update_active_tab_highlight_side_by_side(self, previous_tab=None, new_tab=None):
        """Update the visual highlighting for active tabs in side-by-side mode."""
        if self.layout_mode != 'side_by_side':
            return
            
        # First, remove highlight from previous tab's container
        if previous_tab and previous_tab in self.tab_widget_dict:
            tab_widget = self.tab_widget_dict[previous_tab]
            tab_widget.setStyleSheet("")
            
        # Apply minimal highlighting to new active tab's container
        # Just a subtle border to indicate focus
        if new_tab and new_tab in self.tab_widget_dict:
            active_tab_widget = self.tab_widget_dict[new_tab]
            active_tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    border: 1px solid palette(highlight);
                }
            """)

    def get_current_tab(self):
        """Get the currently active content tab."""
        # In tabs mode, simply use the current tab
        if self.layout_mode == 'tabs':
            current = self.tab_widget.currentWidget()
            if current:
                self.active_tab = current
                return current
                
        # If we have tracked an active tab through clicks, use it
        if self.active_tab and self.active_tab in self.content_tabs:
            logger.info(f"Using tracked active tab: {id(self.active_tab)}")
            return self.active_tab
            
        # Otherwise use first tab as fallback
        if self.content_tabs:
            logger.info(f"No active tab tracked, using first tab: {id(self.content_tabs[0])}")
            self.active_tab = self.content_tabs[0]
            return self.content_tabs[0]
            
        return None

    def close_tab(self, index):
        """Close a tab and replace with a content selector if it's the last one."""
        # Get the tab from the tab widget
        tab = self.tab_widget.widget(index)
        
        if len(self.content_tabs) > 1:
            # Standard behavior for multiple tabs - remove it
            if tab in self.content_tabs:
                self.content_tabs.remove(tab)
            
            # Remove the tab
            self.tab_widget.removeTab(index)
            
            # Also update side-by-side layout if we're in that mode
            if self.layout_mode == 'side_by_side':
                self.rebuild_side_by_side_view()
            
            logger.info(f"Closed tab at index {index} (remaining: {len(self.content_tabs)})")
        else:
            # For the last tab, replace it with a content selector instead of closing
            logger.info("Replacing last tab with a content selector")
            
            # Create a new content selector
            content_selector = self._create_content_selector()
            
            # Replace the tab content at the current index
            self.tab_widget.removeTab(index)
            self.tab_widget.insertTab(index, content_selector, "Choose...")
            self.tab_widget.setCurrentIndex(index)
            
            # Update the content tabs list
            self.content_tabs = [content_selector]
            
            # Update active tab
            self.active_tab = content_selector
    
    def refresh_all(self):
        """Refresh all content tabs."""
        for tab in self.content_tabs:
            if hasattr(tab, 'refresh') and callable(tab.refresh):
                tab.refresh()
    
    def refresh_current(self):
        """Refresh only the current tab."""
        current_tab = self.get_current_tab()
        if current_tab and hasattr(current_tab, 'refresh') and callable(current_tab.refresh):
            current_tab.refresh()

    def _on_content_selected(self, content_type, data, source_tab=None):
        """
        Handle content selection from ContentSelector.
        
        Args:
            content_type: The type of content to load (page, namespaces, search, discover)
            data: Additional data specific to the content type
            source_tab: The specific ContentSelector tab that triggered this action
        """
        # Determine which tab to modify - use source_tab if provided, otherwise use current tab
        target_tab = source_tab if source_tab and source_tab in self.content_tabs else self.get_current_tab()
        
        # Import NodeIDEntryPage here to avoid circular imports
        from ResearchGuidePackage.FrontendModule.ModularTabs.id_entry_page import NodeIDEntryPage
        
        # Check if target_tab is a ContentSelector or NodeIDEntryPage
        # Allow NodeIDEntryPage to accept both custom_widget and node_editor content types
        is_valid_target = (isinstance(target_tab, ContentSelector) or 
                           (isinstance(target_tab, NodeIDEntryPage) and 
                            content_type in ["custom_widget", "node_editor", "page"]))
                            
        if not is_valid_target:
            logger.warning(f"Target tab is not a valid target: {type(target_tab)} for content type {content_type}")
            return
            
        # Create new content based on selection
        if content_type == "custom_widget":
            # For custom widget, we directly use the provided widget
            if isinstance(data, QWidget):
                new_tab = data
                tab_title = new_tab.get_tab_title() if hasattr(new_tab, 'get_tab_title') and callable(new_tab.get_tab_title) else "Custom"
                
                # Hide loading indicator if this was a ContentSelector
                if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                    source_tab.hide_loading_indicator()
            else:
                logger.warning("Custom widget data is not a QWidget")
                return
        elif content_type == "node_editor":
            # Import node editor tab
            from ResearchGuidePackage.FrontendModule.ModularTabs.node_editor_tab import NodeEditorTab
            
            # Handle node editor tab - data contains mode and optional node_id
            mode = data.get("mode", "add") if isinstance(data, dict) else "add"
            node_id = data.get("node_id", None) if isinstance(data, dict) else None
            
            new_tab = NodeEditorTab(self.main_window, mode=mode, node_id=node_id)
            tab_title = new_tab.get_tab_title()
            
            # Connect to operation_completed signal for graph updates
            new_tab.operation_completed.connect(self._handle_node_editor_completion)
            
            # Hide loading indicator if this was a ContentSelector
            if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                source_tab.hide_loading_indicator()
        
        elif content_type == "page":
            new_tab = PageEditor(self.main_window)
            tab_title = "Page"
            
            # If we have a page ID, set it
            if data:
                # Find the page in the dropdown
                for i in range(new_tab.node_dropdown.count()):
                    if new_tab.node_dropdown.itemData(i) == data:
                        # Select this page
                        new_tab.node_dropdown.setCurrentIndex(i)
                        # Update tab title based on selected page
                        tab_title = new_tab.get_tab_title()
                        break
        elif content_type == "namespaces":
            new_tab = NamespacesView(self.main_window)
            tab_title = "Index"  # Changed from "Namespaces" to "Index"
        elif content_type == "search":
            new_tab = SearchTool(self.main_window)
            tab_title = "Search"
        elif content_type == "documentation":
            new_tab = DocumentationView(self.main_window)
            tab_title = "Documentation"
        elif content_type == "birdview":
            new_tab = BirdViewTab()
            new_tab.set_main_window(self.main_window)
            tab_title = "Bird View"
        elif content_type == "draw":
            # Import drawing module only when needed
            try:
                from ResearchGuidePackage.FrontendModule.ModularTabs.drawing_tab import DrawingTab
                new_tab = DrawingTab(self.main_window)
                tab_title = "Draw"  # ⚠️ Explicitly set tab title
                # Hide loading indicator if this was a ContentSelector
                if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                    source_tab.hide_loading_indicator()
            except ImportError:
                logger.error("Drawing module not available")
                # Hide loading indicator if this was a ContentSelector
                if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                    source_tab.hide_loading_indicator()
                QMessageBox.critical(self, "Error", "Drawing module not available")
                return
        elif content_type == "discover":
            new_tab = self._create_discover_tab()
            tab_title = "Discover"
        elif content_type == "researchbot":
            # Import the ResearchBot tab
            from ResearchGuidePackage.FrontendModule.ModularTabs.research_bot_tab import ResearchBotTab
            new_tab = ResearchBotTab(self.main_window)
            tab_title = "ResearchBot"
            
            # Hide loading indicator if this was a ContentSelector
            if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                source_tab.hide_loading_indicator()
        elif content_type == "transcribe":
            # Import transcribe tab only when needed
            from ResearchGuidePackage.FrontendModule.ModularTabs.transcribe_tab import TranscribeTab
            new_tab = TranscribeTab(self.main_window)
            tab_title = "Transcribe"
            # Hide loading indicator if this was a ContentSelector
            if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                source_tab.hide_loading_indicator()
        elif content_type == "databases":
            new_tab = DatabasesPage(self.main_window)
            tab_title = "Databases"
            # Hide loading indicator if this was a ContentSelector
            if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                source_tab.hide_loading_indicator()
        elif content_type == "import_export":
            from ResearchGuidePackage.FrontendModule.ModularTabs.import_export_page import ImportExportPage
            new_tab = ImportExportPage(self.main_window)
            tab_title = "Import/Export"
            # Hide loading indicator if this was a ContentSelector
            if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                source_tab.hide_loading_indicator()
        else:
            logger.warning(f"Unknown content type: {content_type}")
            # Hide loading indicator if this was a ContentSelector
            if hasattr(source_tab, 'hide_loading_indicator') and source_tab:
                source_tab.hide_loading_indicator()
            return
        
        # Replace the content selector with the new content
        if self.layout_mode == 'tabs':
            # Find the index of the target tab
            target_index = self.tab_widget.indexOf(target_tab)
            if target_index >= 0:
                # Replace with new tab - FORCE UPDATE TAB TITLE
                self.tab_widget.removeTab(target_index)
                self.tab_widget.insertTab(target_index, new_tab, tab_title)
                self.tab_widget.setCurrentIndex(target_index)
                
                # ENSURE TAB TITLE IS SHOWN - add this line to force a refresh
                self.tab_widget.setTabText(target_index, tab_title)
                logger.info(f"Tab title explicitly set to: {tab_title}")
                
                # Update our list - safely replace the reference
                if target_tab in self.content_tabs:
                    idx = self.content_tabs.index(target_tab)
                    self.content_tabs[idx] = new_tab
                    # Only update active_tab if this was already the active tab
                    if target_tab == self.active_tab:
                        self.active_tab = new_tab
        else:
            # Side-by-side mode: find the tab in content_tabs and replace it
            if target_tab in self.content_tabs:
                # We need to be extra careful here to avoid accessing deleted objects
                try:
                    index = self.content_tabs.index(target_tab)
                    
                    # Replace in our list - keep a reference to old tab temporarily
                    old_tab = self.content_tabs[index]
                    
                    # If replacing a GraphTab, mark it as being replaced to avoid unnecessary updates
                    if isinstance(old_tab, GraphTab) and hasattr(old_tab, 'being_replaced'):
                        old_tab.being_replaced = True

                    # Complete the rest of the tab replacement process
                    self.content_tabs[index] = new_tab
                    
                    # Update active_tab only if we're replacing the active tab
                    if old_tab == self.active_tab:
                        self.active_tab = new_tab
                    
                    # Remove old tab from dictionary to avoid referencing it later
                    if old_tab in self.tab_widget_dict:
                        old_tab_widget = self.tab_widget_dict[old_tab]
                        # Replace the tab in the same tab widget rather than rebuilding everything
                        if not self._is_deleted_object(old_tab_widget):
                            for i in range(old_tab_widget.count()):
                                if old_tab_widget.widget(i) == old_tab:
                                    old_tab_widget.removeTab(i)
                                    old_tab_widget.insertTab(i, new_tab, tab_title)
                                    old_tab_widget.setCurrentIndex(i)
                                    # Update the dictionary entry
                                    self.tab_widget_dict[new_tab] = old_tab_widget
                                    del self.tab_widget_dict[old_tab]

                                    # After replacing the tab, refresh the graph view for discover tabs
                                    # to ensure they have the correct graph reference
                                    if content_type == "discover":
                                        logger.info("Refreshing new discover tab to ensure graph is loaded")
                                        new_tab.refresh()
                                        
                                    logger.info(f"Tab replaced in side-by-side view: {content_type}")
                                    return
                    
                    # If we couldn't find or update the tab widget, rebuild the entire view
                    logger.info("Rebuilding side-by-side view after content selection")
                    self.rebuild_side_by_side_view()
                except ValueError:
                    # If target_tab isn't in content_tabs anymore, just log the error
                    logger.error("Target tab not found in content_tabs")
                except Exception as e:
                    logger.error(f"Error replacing tab in side-by-side mode: {e}")
            else:
                logger.warning("Target tab not found in content_tabs")
                
        # After tab is replaced, ensure discover tabs are refreshed
        if content_type == "discover":
            logger.info("Refreshing new discover tab to ensure graph is loaded")
            if isinstance(new_tab, GraphTab):
                new_tab.refresh()
                
        logger.info(f"Changed tab content to {content_type}")
    
    def _handle_node_editor_completion(self, result):
        """Handle completion signal from node editor tab."""
        # Log the result
        logger.info(f"Node editor operation completed: {result.get('action')} - Success: {result.get('success')}")
        
        # Update graph if not already done by the node editor tab
        if result.get('success'):
            result_data = result.get('result')
            
            # Check if result is a dictionary before trying to access 'graph'
            if isinstance(result_data, dict) and result_data.get('graph') and hasattr(self.main_window, 'show_graph'):
                # Use create_task instead of directly awaiting since this is a slot
                asyncio.create_task(self.main_window.show_graph(result_data['graph']))
            elif result.get('success') and hasattr(self.main_window, 'refresh_graph'):
                # If no graph data but operation was successful, refresh the graph
                asyncio.create_task(self.main_window.refresh_graph())

    # Methods to open specific content types directly
    
    def open_page(self, page_id=None):
        """Open a page editor in the current tab or a new tab."""
        current_tab = self.get_current_tab()
        
        # If current tab is a content selector, replace it
        if isinstance(current_tab, ContentSelector):
            self._on_content_selected("page", page_id)
        else:
            # Otherwise add a new tab
            new_tab = self.add_content_tab()
            if isinstance(new_tab, ContentSelector):
                self._on_content_selected("page", page_id)
        
        return self.get_current_tab()
    
    def open_namespaces(self):
        """Open the index view in the current tab or a new tab."""
        current_tab = self.get_current_tab()
        
        # If current tab is a content selector, replace it
        if isinstance(current_tab, ContentSelector):
            self._on_content_selected("namespaces", None)
        else:
            # Otherwise add a new tab
            new_tab = self.add_content_tab()
            if isinstance(new_tab, ContentSelector):
                self._on_content_selected("namespaces", None)
        
        return self.get_current_tab()
    
    def open_search(self):
        """Open the search tool in the current tab or a new tab."""
        current_tab = self.get_current_tab()
        
        # If current tab is a content selector, replace it
        if isinstance(current_tab, ContentSelector):
            self._on_content_selected("search", None)
        else:
            # Otherwise add a new tab
            new_tab = self.add_content_tab()
            if isinstance(new_tab, ContentSelector):
                self._on_content_selected("search", None)
        
        return self.get_current_tab()
    
    def open_discover(self):
        """Open the discover view in the current tab or a new tab."""
        current_tab = self.get_current_tab()
        
        # If current tab is a content selector, replace it
        if isinstance(current_tab, ContentSelector):
            self._on_content_selected("discover", None, current_tab)
        else:
            # Otherwise add a new tab
            new_tab = self.add_content_tab()
            if isinstance(new_tab, ContentSelector):
                self._on_content_selected("discover", None, new_tab)
        
        return self.get_current_tab()

    # Method to open documentation directly (optional, for consistency)
    def open_documentation(self):
        """Open the documentation view in the current tab or a new tab."""
        current_tab = self.get_current_tab()
        
        if isinstance(current_tab, ContentSelector):
            self._on_content_selected("documentation", None, current_tab)
        else:
            new_tab = self.add_content_tab() # This creates a "Choose..." tab
            if isinstance(new_tab, ContentSelector): # Then we replace it
                self._on_content_selected("documentation", None, new_tab)
        
        return self.get_current_tab()

    # Method to open bird view directly
    def open_birdview(self):
        """Open the bird view in the current tab or a new tab."""
        current_tab = self.get_current_tab()
        
        if isinstance(current_tab, ContentSelector):
            self._on_content_selected("birdview", None, current_tab)
        else:
            new_tab = self.add_content_tab()
            if isinstance(new_tab, ContentSelector):
                self._on_content_selected("birdview", None, new_tab)
        
        return self.get_current_tab()

    # Add this method to handle opening PDF files
    def open_pdf_viewer(self, pdf_data):
        """Open a PDF viewer tab with the specified PDF data.
        
        Args:
            pdf_data: Dictionary containing PDF information
                - file_path: Path to the PDF file
                - node_id: Optional node ID associated with the PDF
                
        Returns:
            PDFViewer: The created PDF viewer instance or None if failed
        """
        try:
            # Import the PDF viewer here to avoid circular imports
            from ResearchGuidePackage.FrontendModule.ModularTabs.pdf_viewer import PDFViewer
            
            current_tab = self.get_current_tab()
            
            # Create a new PDF viewer
            pdf_viewer = PDFViewer(self.main_window)
            
            # If current tab is a content selector, replace it
            if isinstance(current_tab, ContentSelector):
                # Find the index of the current tab
                tab_idx = self.tab_widget.indexOf(current_tab)
                
                if self.layout_mode == 'tabs':
                    if tab_idx >= 0:
                        # Get file name for the tab title
                        tab_title = os.path.basename(pdf_data.get('file_path', 'PDF File'))
                        
                        # Replace content selector with PDF viewer
                        self.tab_widget.removeTab(tab_idx)
                        self.tab_widget.insertTab(tab_idx, pdf_viewer, tab_title)
                        self.tab_widget.setCurrentIndex(tab_idx)
                        
                        # Update content tabs list
                        idx = self.content_tabs.index(current_tab)
                        self.content_tabs[idx] = pdf_viewer
                        
                        # Update active tab
                        self.active_tab = pdf_viewer
                else:  # side_by_side mode
                    # Update content tabs list first
                    idx = self.content_tabs.index(current_tab)
                    self.content_tabs[idx] = pdf_viewer
                    
                    # Update active tab
                    self.active_tab = pdf_viewer
                    
                    # Find the tab container
                    if current_tab in self.tab_widget_dict:
                        tab_widget = self.tab_widget_dict[current_tab]
                        # Replace the tab in container
                        for i in range(tab_widget.count()):
                            if tab_widget.widget(i) == current_tab:
                                title = os.path.basename(pdf_data.get('file_path', 'PDF File'))
                                tab_widget.removeTab(i)
                                tab_widget.insertTab(i, pdf_viewer, title)
                                tab_widget.setCurrentIndex(i)
                                # Update dictionary
                                self.tab_widget_dict[pdf_viewer] = tab_widget
                                del self.tab_widget_dict[current_tab]
                                break
                    else:
                        # If no container found, rebuild the view
                        self.rebuild_side_by_side_view()
            else:
                # Add a new tab
                new_tab = self.add_content_tab()
                # This will be a content selector, so we replace it
                if isinstance(new_tab, ContentSelector):
                    # Call this method recursively with the new selector tab
                    return self.open_pdf_viewer(pdf_data)
                return None
            
            # Initialize the PDF viewer with data
            pdf_viewer.setup_pdf_viewer(pdf_data)
            
            return pdf_viewer
        except Exception as e:
            logger.error(f"Error opening PDF viewer: {e}", exc_info=True)
            return None

    def add_custom_tab(self, widget, title):
        """Add a custom widget as a new tab.
        
        Args:
            widget: The widget to add as a tab
            title: Title for the tab
        
        Returns:
            The added widget
        """
        # Add widget to content tabs list
        self.content_tabs.append(widget)
        self.active_tab = widget  # Set as active
        
        if self.layout_mode == 'tabs':
            # Add to tab widget
            tab_index = self.tab_widget.addTab(widget, title)
            self.tab_widget.setCurrentIndex(tab_index)
        else:  # side_by_side mode
            # Create a container tab widget
            container_tab_widget = QTabWidget()
            container_tab_widget.setTabsClosable(True)
            container_tab_widget.setMovable(False) 
            container_tab_widget.tabCloseRequested.connect(
                lambda index, tw=container_tab_widget: self.close_side_by_side_tab(tw, index)
            )
            
            # Add the widget to container
            container_tab_widget.addTab(widget, title)
            self.tab_widget_dict[widget] = container_tab_widget
            
            # Create scroll area for the container
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll_area.setWidget(container_tab_widget)
            
            # Add to splitter
            self.splitter.addWidget(scroll_area)
            
            # Update buttons and layout
            self.update_side_by_side_buttons()
            self.distribute_splitter_sizes()
        
        logger.info(f"Added custom tab with title '{title}'")
        return widget

# For backwards compatibility
PageEditorTabWidget = ContentTabWidget
