import os
import sys  # Add for better path handling
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QUrl, QEvent

logger = logging.getLogger('DocumentationView')

class DocumentationView(QWidget):
    """Widget to display local HTML documentation."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create web view with better settings for responsive content
        self.web_view = QWebEngineView()
        
        # Configure a custom profile with optimized settings
        profile = QWebEngineProfile("documentation", self)
        page = QWebEnginePage(profile, self.web_view)
        
        # Configure settings for better responsiveness
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        
        # Set custom page on the view
        self.web_view.setPage(page)
        
        # Apply custom CSS to help with responsive sizing
        # This injects CSS to make the content more responsive to container size changes
        self.web_view.loadFinished.connect(self._apply_responsive_styling)
        
        layout.addWidget(self.web_view)

        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Navigate three levels up from .../frontend/ModularTabs/ to .../ResearchGuideUnearth/
        # Then into docs/_build/html/index.html
        relative_path_to_index_html = os.path.join("..", "..", "..", "build_docs", "html", "index.html")
        docs_path = os.path.abspath(os.path.join(current_script_dir, relative_path_to_index_html))
        
        self.web_view.setUrl(QUrl.fromLocalFile(docs_path))
        
        # Install event filter to handle resize events
        self.installEventFilter(self)

    def _apply_responsive_styling(self, success):
        """Apply responsive CSS styling to the documentation HTML."""
        if success:
            # Inject CSS to make content responsive to container width
            js_code = """
            (function() {
                var style = document.createElement('style');
                style.textContent = `
                    body, html {
                        width: 100% !important;
                        height: 100% !important;
                        margin: 0 !important;
                        padding: 0 !important;
                        overflow-x: hidden !important;
                    }
                    .wy-nav-content, .document {
                        width: 100% !important; 
                        max-width: 100% !important;
                    }
                    .wy-nav-content-wrap {
                        margin-left: 300px !important;
                    }
                    @media screen and (max-width: 768px) {
                        .wy-nav-content-wrap {
                            margin-left: 0 !important;
                        }
                    }
                    img {
                        max-width: 100% !important;
                        height: auto !important;
                    }
                `;
                document.head.appendChild(style);
                
                // Create viewport meta tag for better mobile handling
                var meta = document.createElement('meta');
                meta.name = 'viewport';
                meta.content = 'width=device-width, initial-scale=1.0';
                document.head.appendChild(meta);
            })();
            """
            self.web_view.page().runJavaScript(js_code)
            logger.info("Applied responsive styling to documentation")

    def eventFilter(self, obj, event):
        """Handle resize events to ensure documentation adapts to container size."""
        if event.type() == QEvent.Type.Resize:
            # When resized, update the viewport width
            if hasattr(self, 'web_view'):
                # Use window.visualViewport to update the viewport size and zoom
                js_code = f"""
                (function() {{
                    // Force layout recalculation
                    document.body.style.width = '{self.width()}px';
                    
                    // Adjust for high-DPI screens if needed
                    if (typeof window.devicePixelRatio === 'number') {{
                        document.body.style.zoom = 1.0;
                    }}
                    
                    // Trigger a reflow
                    void(document.body.offsetHeight);
                }})();
                """
                self.web_view.page().runJavaScript(js_code)
        
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        """Handle resize events for the widget."""
        super().resizeEvent(event)
        # Ensure the web view is properly sized
        if hasattr(self, 'web_view'):
            self.web_view.setGeometry(self.rect())

    def get_tab_title(self):
        """Return the title for this tab."""
        return "Documentation"

    def refresh(self):
        """Reload the documentation page."""
        if hasattr(self, 'web_view'):
            self.web_view.reload()
            # Re-apply responsive styling after reload
            self.web_view.loadFinished.connect(self._apply_responsive_styling)
