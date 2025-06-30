"""
Drawing Tab
==========
A tab for freehand drawing and sketching.
"""
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QColorDialog, QSlider, QComboBox)
from PyQt6.QtGui import (QPainter, QPen, QColor, QPixmap, QIcon, 
                        QPainterPath, QImage, QBrush)
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QSize

logger = logging.getLogger('DrawingTab')

class DrawingCanvas(QWidget):
    """Canvas widget for drawing."""
    
    def __init__(self, parent=None):
        """Initialize the drawing canvas."""
        super().__init__(parent)
        
        # Set background color
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.white)
        self.setPalette(palette)
        
        # Drawing attributes
        self.drawing = False
        self.brush_size = 3
        self.brush_color = Qt.GlobalColor.black
        
        # Current path being drawn
        self.current_path = QPainterPath()
        
        # List of paths with their properties
        self.paths = []  # List of (path, pen) tuples
        
        # Last point for drawing
        self.last_point = QPoint()
        
        # Tool settings
        self.current_tool = "pen"  # pen, eraser, line, rect, ellipse
        self.temp_path = None
        self.start_point = None
        
        # Set focus policy to accept key events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def set_brush_size(self, size):
        """Set the brush size."""
        self.brush_size = size
    
    def set_brush_color(self, color):
        """Set the brush color."""
        self.brush_color = color
    
    def set_tool(self, tool):
        """Set the drawing tool."""
        self.current_tool = tool
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self.start_point = event.pos()
            
            if self.current_tool == "pen" or self.current_tool == "eraser":
                self.current_path = QPainterPath()
                self.current_path.moveTo(event.pos())
            
            self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.drawing:
            if self.current_tool == "pen" or self.current_tool == "eraser":
                # For pen and eraser, add to current path
                self.current_path.lineTo(event.pos())
            
            self.last_point = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            
            if self.current_tool == "pen":
                # Store the path with its properties
                pen = QPen(self.brush_color, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                self.paths.append((self.current_path, pen))
                self.current_path = QPainterPath()
            
            elif self.current_tool == "eraser":
                # Store eraser path
                pen = QPen(Qt.GlobalColor.white, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                self.paths.append((self.current_path, pen))
                self.current_path = QPainterPath()
            
            elif self.current_tool == "line":
                # Create a line path
                line_path = QPainterPath()
                line_path.moveTo(self.start_point)
                line_path.lineTo(event.pos())
                
                # Store the path with pen properties
                pen = QPen(self.brush_color, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                self.paths.append((line_path, pen))
            
            elif self.current_tool == "rect":
                # Create a rectangle path
                rect_path = QPainterPath()
                rect = QRect(self.start_point, event.pos()).normalized()
                rect_path.addRect(rect)
                
                # Store the path with pen properties
                pen = QPen(self.brush_color, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                self.paths.append((rect_path, pen))
            
            elif self.current_tool == "ellipse":
                # Create an ellipse path
                ellipse_path = QPainterPath()
                rect = QRect(self.start_point, event.pos()).normalized()
                ellipse_path.addEllipse(rect)
                
                # Store the path with pen properties
                pen = QPen(self.brush_color, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                self.paths.append((ellipse_path, pen))
            
            self.update()
    
    def paintEvent(self, event):
        """Handle paint events."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw all stored paths
        for path, pen in self.paths:
            painter.setPen(pen)
            painter.drawPath(path)
        
        # Draw current path while drawing
        if self.drawing:
            if self.current_tool == "pen":
                pen = QPen(self.brush_color, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawPath(self.current_path)
            
            elif self.current_tool == "eraser":
                pen = QPen(Qt.GlobalColor.white, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawPath(self.current_path)
            
            elif self.current_tool == "line":
                pen = QPen(self.brush_color, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawLine(self.start_point, self.last_point)
            
            elif self.current_tool == "rect":
                pen = QPen(self.brush_color, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                rect = QRect(self.start_point, self.last_point).normalized()
                painter.drawRect(rect)
            
            elif self.current_tool == "ellipse":
                pen = QPen(self.brush_color, self.brush_size, 
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                          Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                rect = QRect(self.start_point, self.last_point).normalized()
                painter.drawEllipse(rect)
    
    def clear(self):
        """Clear the canvas."""
        self.paths = []
        self.update()
    
    def save_image(self, path):
        """Save the canvas as an image."""
        try:
            # Create a pixmap and render the canvas to it
            image = QImage(self.size(), QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw all paths
            for path, pen in self.paths:
                painter.setPen(pen)
                painter.drawPath(path)
            
            painter.end()
            
            # Save the image
            success = image.save(path)
            return success
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return False

class ColorButton(QPushButton):
    """Button that shows a color and opens a color dialog."""
    
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, color=Qt.GlobalColor.black, parent=None):
        """Initialize the color button."""
        super().__init__(parent)
        self.setFixedSize(QSize(32, 32))
        self.color = QColor(color)
        self.update_icon()
        
        self.clicked.connect(self.choose_color)
    
    def choose_color(self):
        """Open color dialog to choose a new color."""
        color = QColorDialog.getColor(self.color, self)
        if color.isValid():
            self.color = color
            self.update_icon()
            self.color_changed.emit(self.color)
    
    def update_icon(self):
        """Update button icon to show current color."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(self.color)
        self.setIcon(QIcon(pixmap))
        self.setIconSize(QSize(24, 24))

class DrawingTab(QWidget):
    """Tab for drawing and sketching."""
    
    def __init__(self, main_window=None):
        """Initialize the drawing tab."""
        super().__init__()
        self.main_window = main_window
        self._setup_ui()
        logger.info("Drawing tab initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        
        # Tool buttons
        self.pen_button = QPushButton("Pen")
        self.pen_button.setCheckable(True)
        self.pen_button.setChecked(True)
        self.pen_button.clicked.connect(lambda: self.set_tool("pen"))
        toolbar_layout.addWidget(self.pen_button)
        
        self.eraser_button = QPushButton("Eraser")
        self.eraser_button.setCheckable(True)
        self.eraser_button.clicked.connect(lambda: self.set_tool("eraser"))
        toolbar_layout.addWidget(self.eraser_button)
        
        self.line_button = QPushButton("Line")
        self.line_button.setCheckable(True)
        self.line_button.clicked.connect(lambda: self.set_tool("line"))
        toolbar_layout.addWidget(self.line_button)
        
        self.rect_button = QPushButton("Rectangle")
        self.rect_button.setCheckable(True)
        self.rect_button.clicked.connect(lambda: self.set_tool("rect"))
        toolbar_layout.addWidget(self.rect_button)
        
        self.ellipse_button = QPushButton("Ellipse")
        self.ellipse_button.setCheckable(True)
        self.ellipse_button.clicked.connect(lambda: self.set_tool("ellipse"))
        toolbar_layout.addWidget(self.ellipse_button)
        
        # Group all tool buttons for exclusive selection
        self.tool_buttons = [
            self.pen_button, self.eraser_button, self.line_button,
            self.rect_button, self.ellipse_button
        ]
        
        toolbar_layout.addSpacing(20)
        
        # Color selection
        color_label = QLabel("Color:")
        toolbar_layout.addWidget(color_label)
        
        self.color_button = ColorButton()
        self.color_button.color_changed.connect(self.set_color)
        toolbar_layout.addWidget(self.color_button)
        
        toolbar_layout.addSpacing(20)
        
        # Brush size
        size_label = QLabel("Size:")
        toolbar_layout.addWidget(size_label)
        
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(1, 20)
        self.size_slider.setValue(3)
        self.size_slider.setFixedWidth(100)
        self.size_slider.valueChanged.connect(self.set_brush_size)
        toolbar_layout.addWidget(self.size_slider)
        
        self.size_value_label = QLabel("3")
        toolbar_layout.addWidget(self.size_value_label)
        
        toolbar_layout.addSpacing(20)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_canvas)
        toolbar_layout.addWidget(self.clear_button)
        
        # Save button
        self.save_button = QPushButton("Save...")
        self.save_button.clicked.connect(self.save_drawing)
        toolbar_layout.addWidget(self.save_button)
        
        # Add stretch to push everything to the left
        toolbar_layout.addStretch(1)
        
        # Add toolbar to main layout
        layout.addWidget(toolbar)
        
        # Add separator
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(separator)
        
        # Drawing canvas
        self.canvas = DrawingCanvas()
        layout.addWidget(self.canvas, 1)  # Canvas gets all remaining space
    
    def set_tool(self, tool):
        """Set the current drawing tool."""
        # Update canvas
        self.canvas.set_tool(tool)
        
        # Update UI buttons
        for button in self.tool_buttons:
            button.setChecked(False)
        
        if tool == "pen":
            self.pen_button.setChecked(True)
        elif tool == "eraser":
            self.eraser_button.setChecked(True)
        elif tool == "line":
            self.line_button.setChecked(True)
        elif tool == "rect":
            self.rect_button.setChecked(True)
        elif tool == "ellipse":
            self.ellipse_button.setChecked(True)
    
    def set_color(self, color):
        """Set the brush color."""
        self.canvas.set_brush_color(color)
    
    def set_brush_size(self, size):
        """Set the brush size."""
        self.canvas.set_brush_size(size)
        self.size_value_label.setText(str(size))
    
    def clear_canvas(self):
        """Clear the drawing canvas."""
        self.canvas.clear()
    
    def save_drawing(self):
        """Save the drawing to an image file."""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Drawing", "", "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
        )
        
        if filename:
            success = self.canvas.save_image(filename)
            if success:
                logger.info(f"Drawing saved to: {filename}")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Failed to save drawing to {filename}")
    
    def get_tab_title(self):
        """Return the title for this tab."""
        return "Draw"
    
    def refresh(self):
        """Refresh method to satisfy the tab interface."""
        # No need to refresh drawing tab
        pass
