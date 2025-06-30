from PyQt6.QtWidgets import QTextEdit, QFileDialog, QMessageBox, QMenu
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QMimeData
from PyQt6.QtGui import QTextCursor, QAction, QKeySequence, QGuiApplication
import logging
import re
import markdown2

# Konfiguriert Debug-Level Logging für detaillierte Entwicklerinfos
logging.basicConfig(
    level=logging.DEBUG,                         
    format='%(asctime)s - %(message)s'          
)

# Definiert spezielle Aktion für das Öffnen von Dateien
OPEN_FILE_ACTION = "open_file"                   

class ClickableTextEdit(QTextEdit):              # Hauptklasse für den erweiterten Editor
    # Signal wird ausgelöst, wenn ein Link geklickt wird
    link_clicked = pyqtSignal(str)               

    def __init__(self, parent=None):             
        super().__init__(parent)                 # Initialisiert Basis-Editor
        self._mode = "view"                      # Startet im Nur-Lese-Modus
        self.logging = logging.getLogger(__name__)  # Erstellt spezifischen Logger
        
        # Grundeinstellungen
        self.setReadOnly(True)                   # Aktiviert Nur-Lese-Modus
        self._markdown_text = "Enter and edit text here... [Open File](open_file) [Example Link](https://www.example.com)"  # Setzt Initial-Text
        
        # Verbindet Cursor-Bewegungen mit Update-Funktion
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        
        # Verschiedene Status-Flags zur Vermeidung von Rekursion
        self._last_cursor_position = None        # Speichert letzte Cursor-Position
        self._is_handling_cursor = False         # Verhindert mehrfache Cursor-Verarbeitung
        self._is_cursor_on_link = False         # Zeigt an, ob Cursor auf Link ist
        self._is_rendering = False              # Verhindert mehrfaches Rendern
        self._active_link_url = None  # Speichert die URL des aktiven Links
        self._active_link_start = None  # Speichert die Startposition des aktiven Links statt URL
        self._placeholder_text = ""   # Store placeholder text when needed
        
        # Komplexe Regex für verschiedene Link-Formate
        self.markdown_link_regex = r'(\[([^\]]+)\]\(([^)]+)\)|\[\[([^\]]+)\]\]\(([^)]+)\)|\!\[([^\]]+)\]\(([^)]+)\)|\[([^\]|]+)\|([^\]|]+)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)\(*\)?|\[([^\]]+)\])'

        # Add tracking for context menu position
        self._context_menu_position = None

    # Add focus event handlers
    def focusInEvent(self, event):
        """Handle gaining focus - show bullet point for editing."""
        super().focusInEvent(event)
        
        # Check if we need to convert from placeholder to bullet point
        if self.property("is_placeholder") and self.get_mode() == "edit":
            # Save the placeholder text
            current_text = self._markdown_text.strip()
            if current_text.startswith("•"):
                placeholder = current_text[1:].strip()
                if placeholder:
                    self._placeholder_text = placeholder
            
            # Set clean bullet point
            self.blockSignals(True)
            self._markdown_text = "• "
            self.setProperty("is_placeholder", False)
            self.render_text()
            
            # Position cursor at the end
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            self.blockSignals(False)
            
            self.logging.debug("Converted placeholder to bullet point on focus")

    def focusOutEvent(self, event):
        """Handle losing focus - show placeholder text if content is empty."""
        # Check if we should convert to placeholder
        if self.get_mode() == "edit":
            # Get current text without bullet point
            text = self._markdown_text.strip()
            is_empty = text == "•" or text == "• " or not text
            has_placeholder = hasattr(self, "_placeholder_text") and self._placeholder_text
            
            if is_empty and has_placeholder:
                # Content is empty, show placeholder
                self.blockSignals(True)
                self._markdown_text = f"• <i style='color: gray;'>{self._placeholder_text}</i>"
                self.setProperty("is_placeholder", True)
                self.render_text()
                self.blockSignals(False)
                self.logging.debug(f"Restored placeholder text: {self._placeholder_text}")
        
        super().focusOutEvent(event)

    def set_mode(self, mode):                    # Wechselt zwischen Bearbeiten/Ansehen
        """Set the mode of the text edit."""
        if mode not in ["view", "edit"]:
            raise ValueError("Invalid mode. Must be 'view' or 'edit'.")
        self._mode = mode
        self.setReadOnly(mode == "view")
        self.render_text()

    def get_mode(self):                          # Gibt aktuellen Modus zurück
        """Get the current mode of the text edit."""
        return self._mode                        # Liefert "view" oder "edit"

    def setText(self, text):                     # Setzt neuen Markdown-Text
        """Set the text as Markdown."""
        self._markdown_text = text               # Speichert Text
        self.render_text()                       # Rendert neu

    def toPlainText(self):                       # Gibt rohen Markdown-Text zurück
        """Return the text as Markdown."""
        return self._markdown_text               # Liefert unformatierten Text

    def render_text(self):                       # Konvertiert Markdown zu HTML
        """Render the text as HTML with dynamic link display."""
        if self._is_rendering:                   # Verhindert Rekursion
            return
        
        try:
            self._is_rendering = True            # Setzt Rendering-Flag
            cursor = self.textCursor()           # Speichert Cursor-Position
            pos = cursor.position()              # Aktuelle Position
            anchor = cursor.anchor()             # Startpunkt der Auswahl
            
            # Neues Debug-Logging für Cursor-Position beim Rendern
            self.logging.debug(f"Rendering text. Cursor position: {pos}, anchor: {anchor}")
            
            # Speichere aktiven Link für markdown_to_html
            active_link = self._active_link_url
            
            # Rendert Text je nach Modus mit aktivem Link
            html = self.markdown_to_html(self._markdown_text, active_link)  # Konvertiert zu HTML
            super().setHtml(html)                # Setzt HTML im Editor
            
            if self._mode == "edit":             # Im Edit-Modus
                cursor.setPosition(anchor)       # Stellt Cursor wieder her
                cursor.setPosition(pos, QTextCursor.MoveMode.KeepAnchor if anchor != pos else QTextCursor.MoveMode.MoveAnchor)
                self.setTextCursor(cursor)       # Aktualisiert Cursor
            
            self.update()                        # Aktualisiert Anzeige
        finally:
            self._is_rendering = False           # Setzt Flag zurück

    def _on_cursor_moved(self):                  # Reagiert auf Cursor-Bewegung
        """Called whenever cursor moves for any reason."""
        if self._mode == "edit" and not self._is_rendering:  # Nur im Edit-Modus
            self._update_cursor_link_state()      # Prüft Link-Status

    def _update_cursor_link_state(self):         
        """Update the cursor-on-link state and return if state changed."""
        self.render_text()
        
        if self._is_handling_cursor or self._is_rendering:
            return False
            
        try:
            self._is_handling_cursor = True
            cursor_pos = self.textCursor().position()
            
            old_link_start = self._active_link_start
            
            # Alle Status zurücksetzen
            self._is_cursor_on_link = False
            self._active_link_url = None
            self._active_link_start = None  # Wird nur gesetzt wenn neuer Link gefunden wird
            
            # Link-Erkennung
            intervals = self._find_link_intervals(self.document().toPlainText())
            link_found = False
            for start, end, link_text, url in intervals:
                if start <= cursor_pos <= end:
                    self._is_cursor_on_link = True
                    self._active_link_url = url
                    self._active_link_start = start
                    link_found = True
                    self.logging.debug(f"Found active link at {start}: [{link_text}]({url})")
                    break
                    
            if not link_found:
                self.logging.debug("No link found at cursor position, all states reset")
        
        finally:
            self._is_handling_cursor = False

    def keyPressEvent(self, event):
        """Handle key press events including keyboard shortcuts."""
        # Handle standard shortcuts
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.copy()
            return
            
        if self._mode == "edit":
            if event.key() == Qt.Key.Key_X and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.cut()
                return
                
            if event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.paste()
                return

        if not self._mode == "edit":
            super().keyPressEvent(event)
            return
        
        # Get current cursor info first
        cursor = self.textCursor()
        html_pos = cursor.position()
        md_pos = self._map_cursor_to_markdown(html_pos)
        
        # Handle arrow key navigation to prevent going before bullet point
        if event.key() == Qt.Key.Key_Left or event.key() == Qt.Key.Key_Backspace:
            # Don't allow cursor to move before position 2 (after bullet point)
            if cursor.position() <= 2 and not cursor.hasSelection():
                return
                
        # Handle Home key to place cursor after bullet
        if event.key() == Qt.Key.Key_Home:
            # Move cursor after bullet and space (position 2)
            cursor.setPosition(2)
            self.setTextCursor(cursor)
            return
        
        # Prevent backspace if it would delete the bullet point
        if event.key() == Qt.Key.Key_Backspace:
            # Check if we have a selection
            if cursor.hasSelection():
                # Get the start and end positions of the selection in markdown
                html_start = min(cursor.position(), cursor.anchor())
                html_end = max(cursor.position(), cursor.anchor())
                md_start = self._map_cursor_to_markdown(html_start)
                md_end = self._map_cursor_to_markdown(html_end)
                
                # Only allow if it doesn't delete the bullet point
                if html_start <= 1 and '•' in self._markdown_text[:md_end]:
                    return  # Prevent deletion that would affect bullet point
                
                # Delete the selected text
                self._markdown_text = self._markdown_text[:md_start] + self._markdown_text[md_end:]
                new_pos = html_start  # Position cursor at the start of where the selection was
                
                # Render and handle the rest of the event
                old_link_start = self._active_link_start
                self.render_text()
                cursor = self.textCursor()
                cursor.setPosition(new_pos)
                self.setTextCursor(cursor)
                self.ensureCursorVisible()
                
                # Check bullet point and placeholder
                if not self._markdown_text.startswith('•'):
                    self._markdown_text = '• ' + self._markdown_text.lstrip()
                    self.render_text()
                    if new_pos < 2:
                        cursor = self.textCursor()
                        cursor.setPosition(2)
                        self.setTextCursor(cursor)
                
                self._check_and_restore_placeholder()
                return
            
            # Check if we're at the beginning or would delete the bullet (non-selection case)
            elif md_pos <= 2:  # "• " is 2 chars
                return  # Prevent deletion of bullet point

        # Let normal arrow key navigation work for other cases
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            # For right arrow key, just proceed normally
            if event.key() == Qt.Key.Key_Right:
                super().keyPressEvent(event)
                return
                
            # For left/up/down keys, make sure we don't end up before position 2
            current_pos = cursor.position()
            super().keyPressEvent(event)
            new_pos = self.textCursor().position()
            
            # If we moved before position 2, force it to 2
            if new_pos < 2:
                cursor = self.textCursor()
                cursor.setPosition(2)
                self.setTextCursor(cursor)
            return
                
        # Link-Status vor der Änderung speichern
        old_link_start = self._active_link_start

        # Handle text changes
        if event.key() == Qt.Key.Key_Space:
            self._markdown_text = self._markdown_text[:md_pos] + ' ' + self._markdown_text[md_pos:]
            new_pos = html_pos + 1
        elif event.key() == Qt.Key.Key_Backspace and md_pos > 0:
            # Don't delete the bullet point
            if md_pos > 2:  # "• " is 2 chars
                self._markdown_text = self._markdown_text[:md_pos-1] + self._markdown_text[md_pos:]
                new_pos = html_pos - 1
            else:
                return  # Do nothing if it would delete the bullet
        elif event.key() == Qt.Key.Key_Delete and md_pos < len(self._markdown_text):
            self._markdown_text = self._markdown_text[:md_pos] + self._markdown_text[md_pos+1:]
            new_pos = html_pos
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Check if there's a selection
            if cursor.hasSelection():
                # Get the start and end positions of the selection in markdown
                html_start = min(cursor.position(), cursor.anchor())
                html_end = max(cursor.position(), cursor.anchor())
                md_start = self._map_cursor_to_markdown(html_start)
                md_end = self._map_cursor_to_markdown(html_end)
                
                # Delete the selected text and insert a newline
                self._markdown_text = self._markdown_text[:md_start] + '\n' + self._markdown_text[md_end:]
                new_pos = html_start + 1  # Position cursor after the newline
            else:
                # No selection, insert newline at cursor position as before
                self._markdown_text = self._markdown_text[:md_pos] + '\n' + self._markdown_text[md_pos:]
                new_pos = html_pos + 1
        elif event.text():
            self._markdown_text = self._markdown_text[:md_pos] + event.text() + self._markdown_text[md_pos:]
            new_pos = html_pos + len(event.text())
        else:
            super().keyPressEvent(event)
            return

        # Link an gleicher Startposition im neuen Text finden
        if old_link_start is not None:
            links = self._find_link_intervals(self._markdown_text)
            for start, end, link_text, url in links:
                if start == old_link_start:
                    self._active_link_start = start
                    self._is_cursor_on_link = True  # Link bleibt aktiv
                    self._active_link_url = url     # URL des gefundenen Links
                    break
        
        # Text rendern und Cursor setzen
        self.render_text()

        # Directly set cursor position and ensure visibility
        cursor = self.textCursor()
        cursor.setPosition(new_pos)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        
        # Check if we need to restore the bullet point
        if not self._markdown_text.startswith('•'):
            self._markdown_text = '• ' + self._markdown_text.lstrip()
            self.render_text()
            # Adjust cursor position if needed
            if new_pos < 2:
                cursor = self.textCursor()
                cursor.setPosition(2)
                self.setTextCursor(cursor)
        
        # NEW: Check if content is empty and restore placeholder after edit
        self._check_and_restore_placeholder()

    def _check_and_restore_placeholder(self):
        """Check if content is empty (or just bullet) and restore placeholder if needed."""
        # Skip if already a placeholder or not in edit mode
        if self.property("is_placeholder") or self.get_mode() != "edit":
            return
            
        # Check for empty or whitespace-only content (except bullet)
        content = self._markdown_text.strip()
        if content == '•' or content == '• ' or len(content.replace('•', '').strip()) == 0:
            # Check if we have a placeholder text saved
            if hasattr(self, "_placeholder_text") and self._placeholder_text:
                self.blockSignals(True)
                self._markdown_text = f"• <i style='color: gray;'>{self._placeholder_text}</i>"
                self.setProperty("is_placeholder", True)
                self.render_text()
                self.blockSignals(False)
                self.logging.debug(f"Restored placeholder after edit: {self._placeholder_text}")

    def setHtml(self, html):
        """Override setHtml to check for placeholder restoration after external changes."""
        super().setHtml(html)
        # Check if we should restore placeholder after the HTML is set
        self._check_and_restore_placeholder()

    def _find_link_intervals(self, text):
        """Findet alle Markdown-Links im Text und ihre Bestandteile
        
        Returns:
            list: Liste von Tuples (start, end, link_text, url)
        """
        intervals = []
        for match in re.finditer(self.markdown_link_regex, text):
            # Überspringe leere Links
            if match.group(0) == '[]':
                continue
                
            # Link analysieren
            link_text = url = None
            for i in range(2, 14, 3):
                if match.group(i) and match.group(i + 1):
                    link_text = match.group(i)
                    url = match.group(i + 1)
                    intervals.append((match.start(), match.end(), link_text, url))
                    break
                    
        return intervals

    def _find_hypertext_intervals(self):
        """Findet alle HTML-Links im aktuellen Dokument
        
        Returns:
            list: Liste von Tuples (start, end, link_text, url)
        """
        intervals = []
        cursor = self.textCursor()
        
        # Durchsuche das gesamte Dokument
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        while not cursor.atEnd():
            format = cursor.charFormat()
            url = format.anchorHref()
            
            if url:
                # Selektiere den kompletten Link
                start = cursor.position()
                while format.anchorHref() == url and not cursor.atEnd():
                    cursor.movePosition(QTextCursor.MoveOperation.Right)
                    format = cursor.charFormat()
                end = cursor.position()
                
                # Hole den Link-Text
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                link_text = cursor.selectedText()
                
                intervals.append((start, end, link_text, url))
            else:
                cursor.movePosition(QTextCursor.MoveOperation.Right)
                
        return intervals

    def _process_link_matches(self, markdown_text, cursor_position, active_link=None):
        """Verarbeitet Links durch direkten Vergleich der Listen"""
        result = markdown_text
        
        # 1. Sammle alle Links in sortierte Listen
        rendered_links = []
        rendered_links.extend(self._find_link_intervals(self.document().toPlainText()))
        rendered_links.extend(self._find_hypertext_intervals())
        rendered_links.sort(key=lambda x: x[0])  # Sortiere nach Start-Position
        
        markdown_links = self._find_link_intervals(markdown_text)
        markdown_links.sort(key=lambda x: x[0])
        
        # 2. Finde den aktiven Link durch Cursor-Position
        active_index = None
        for i, (start, end, text, url) in enumerate(reversed(rendered_links)):
            if start <= cursor_position <= end:
                active_index = i
                break
                
        # 3. Verarbeite alle Links
        for i, (start, end, link_text, url) in enumerate(reversed(markdown_links)):
            # Link ist aktiv wenn sein Index dem gefundenen entspricht
            should_escape = (self._mode == "edit" and 
                           active_index is not None and 
                           i == len(markdown_links) - 1 - active_index)
            
            if should_escape:
                self.logging.debug(f"Escaping active link: [{link_text}]({url})")
                replacement = self._create_escaped_markdown_link(link_text, url)
            else:
                replacement = self._create_html_link(link_text, url)
                
            result = result[:start] + replacement + result[end:]
            
        return result

    def _confirm_hypertext_at_position(self, position):
        """Findet und analysiert einen HTML-Link an der gegebenen Cursor-Position
        
        Args:
            position: Die zu prüfende Cursor-Position
            
        Returns:
            tuple: (is_link, link_text, url) - Ob ein Link gefunden wurde, 
                  der angezeigte Text und die URL des Links
        """
        cursor = self.textCursor()
        cursor.setPosition(position)
        
        # Hole das Textformat an der Position
        format = cursor.charFormat()
        url = format.anchorHref()
        
        if url:
            # Selektiere den Link-Text
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            link_text = cursor.selectedText()
            self.logging.debug(f"Found hypertext link: {link_text} -> {url}")
            return True, link_text, url
            
        return False, None, None

    def _create_html_link(self, link_text, url):
        """Erstellt einen HTML-Link"""
        return f'<a href="{url}">{link_text}</a>'

    def _create_escaped_markdown_link(self, link_text, url):
        """Erstellt einen escaped Markdown-Link"""
        return f"\\[{link_text}\\]({url})"

    def _convert_wiki_links(self, text):
        """Konvertiert [[Wiki-Style]] Links zu normalen Links"""
        return re.sub(r'\[\[([^\]]+)\]\]', lambda m: f'[{m.group(1)}](NONE)', text)

    def _convert_square_brackets(self, text):
        """Konvertiert [Text] zu [Text](NONE)"""
        pattern = r'(?<![\[\(\{])\[([^\]]+)\](?![\]\)\}])(?=[^\(])'
        return re.sub(pattern, lambda m: f'[{m.group(1)}](NONE)', text)

    def markdown_to_html(self, markdown, active_link=None):
        """Convert markdown to html with dynamic link rendering."""
        cursor_position = self.textCursor().position()
        self.logging.debug(f"Converting markdown at cursor position: {cursor_position}")
        self.logging.debug(f"Using active link: {active_link}")

        try:
            processed_text = self._convert_wiki_links(markdown)
            processed_text = self._convert_square_brackets(processed_text)
            # Übergebe aktiven Link an process_link_matches
            processed_text = self._process_link_matches(processed_text, cursor_position, active_link)
            
            # Generate HTML with markdown2
            html = markdown2.markdown(processed_text, extras=['fenced-code-blocks', 'nofollow'])
            
            # Wrap in a div that preserves whitespace
            html = f'<div style="white-space: pre-wrap;">{html}</div>'
            
            return html
        except Exception as e:
            self.logging.error(f"Error in markdown conversion: {e}")
            return f"<p>Error in markdown conversion: {str(e)}</p>"

    def _map_cursor_to_markdown(self, html_position):
        """Mappt HTML Position zu Markdown durch direkten Buchstabenvergleich"""
        rendered_text = self.document().toPlainText()
        html_links = self._find_hypertext_intervals()
        md_pos = 0
        html_pos = 0
        
        while html_pos < html_position and md_pos < len(self._markdown_text):
            # Aktuelles Zeichen in beiden Texten
            md_char = self._markdown_text[md_pos]
            html_char = rendered_text[html_pos] if html_pos < len(rendered_text) else None
            
            # Prüfe ob wir in einem HTML-Link sind
            in_html_link = any(start <= html_pos < end for start, end, _, _ in html_links)
            
            # Zeichen stimmen überein
            if md_char == html_char:
                md_pos += 1
                html_pos += 1
                continue
                
            # Zeichen stimmen nicht überein - wahrscheinlich ein Link
            if md_char == '[':
                # Finde Link-Ende
                link_end = self._markdown_text.find('](', md_pos)
                url_end = self._markdown_text.find(')', link_end) if link_end != -1 else -1
                
                if link_end != -1 and url_end != -1:
                    link_text = self._markdown_text[md_pos + 1:link_end]
                    
                    if in_html_link:
                        # HTML-Link: Überspringe Link-Syntax und URL
                        md_pos = url_end + 1
                    else:
                        # Plaintext-Link: Zähle alles mit
                        md_pos += 1
                    continue
                    
            # Kein Link oder ungültiger Link - überspringe Zeichen
            md_pos += 1
            
        return md_pos

    def mousePressEvent(self, event):
        """Handle mouse press events to detect link clicks and prevent cursor before bullet point."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Get cursor at click position
            cursor = self.cursorForPosition(event.pos())
            
            # If in edit mode, prevent positioning cursor before bullet point
            if self._mode == "edit":
                # If cursor would be positioned before position 2, move it to position 2
                if (cursor.position() < 2):
                    cursor.setPosition(2)
                    self.setTextCursor(cursor)
                    self.ensureCursorVisible()
                    return
            
            # Get link info at position for regular link handling
            format = cursor.charFormat()
            url = format.anchorHref()
            
            if url:
                self.link_clicked.emit(url)
                return
                    
        super().mousePressEvent(event)
        
        # After mouse press, ensure cursor isn't before position 2
        if self._mode == "edit" and self.textCursor().position() < 2:
            cursor = self.textCursor()
            cursor.setPosition(2)
            self.setTextCursor(cursor)

    def contextMenuEvent(self, event):
        """Create custom context menu with copy/paste options."""
        # Get current selection state before changing anything
        current_cursor = self.textCursor()
        has_selection = current_cursor.hasSelection()
        selection_text = current_cursor.selectedText() if has_selection else ""
        
        # Save selection start/end for later restoration
        self._selection_start = current_cursor.selectionStart() if has_selection else -1
        self._selection_end = current_cursor.selectionEnd() if has_selection else -1
        
        # Store right-click position without changing selection
        self._context_menu_position = self.cursorForPosition(event.pos()).position()
        self.logging.debug(f"Context menu opened at position: {self._context_menu_position}")
        
        menu = QMenu(self)
        
        # Create standard actions
        cut_action = QAction("Cut", self)
        copy_action = QAction("Copy", self)
        paste_action = QAction("Paste", self)
        select_all_action = QAction("Select All", self)
        
        # Configure actions
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        
        # Create custom handlers that work with the selection
        def do_copy():
            # Copy the captured selection_text, not current selection
            if has_selection and selection_text:
                clipboard = QGuiApplication.clipboard()
                clipboard.setText(selection_text)
                self.logging.debug(f"Copy action: copied text: {selection_text}")
        
        def do_cut():
            if has_selection and self._mode == "edit":
                # First copy the text
                clipboard = QGuiApplication.clipboard()
                clipboard.setText(selection_text)
                
                # Now delete the selected text
                self.cut()  
        
        # Connect custom handlers
        copy_action.triggered.connect(do_copy)
        cut_action.triggered.connect(do_cut)
        paste_action.triggered.connect(self.paste_at_context_menu)
        select_all_action.triggered.connect(self.selectAll)
        
        # Enable/disable actions based on context
        clipboard = QGuiApplication.clipboard()
        
        cut_action.setEnabled(has_selection and self._mode == "edit")
        copy_action.setEnabled(has_selection)
        paste_action.setEnabled(clipboard.mimeData().hasText() and self._mode == "edit")
        
        # Add actions to menu
        menu.addAction(copy_action)
        
        if self._mode == "edit":
            menu.addAction(cut_action)
            menu.addAction(paste_action)
            
        menu.addSeparator()
        menu.addAction(select_all_action)
        
        # Show menu at cursor position
        menu.exec(event.globalPos())
        
        # Restore selection after menu closes if we had one
        if has_selection and self._selection_start >= 0 and self._selection_end >= 0:
            restore_cursor = self.textCursor()
            restore_cursor.setPosition(self._selection_start) 
            restore_cursor.setPosition(self._selection_end, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(restore_cursor)
    
    def paste_at_context_menu(self):
        """Paste text at the context menu position."""
        if self._mode != "edit":
            return
            
        # Get clipboard content
        clipboard = QGuiApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasText() and self._context_menu_position is not None:
            # Get text and use context menu position
            paste_text = mime_data.text()
            
            # First move cursor to context menu position
            cursor = self.textCursor()
            cursor.setPosition(self._context_menu_position)
            self.setTextCursor(cursor)
            
            # Now get the markdown position
            html_pos = self._context_menu_position
            md_pos = self._map_cursor_to_markdown(html_pos)
            
            # Insert clipboard text
            self._markdown_text = self._markdown_text[:md_pos] + paste_text + self._markdown_text[md_pos:]
            
            # Render updated text
            self.render_text()
            
            # Position cursor after pasted text
            new_html_pos = self._find_html_position_for_md(md_pos + len(paste_text))
            new_cursor = self.textCursor()
            new_cursor.setPosition(new_html_pos)
            self.setTextCursor(new_cursor)
            
            # Check if we need to restore bullet point
            if not self._markdown_text.startswith('•'):
                self._markdown_text = '• ' + self._markdown_text.lstrip()
                self.render_text()
                # Adjust cursor if needed
                if html_pos < 2:
                    cursor = self.textCursor()
                    cursor.setPosition(2)
                    self.setTextCursor(cursor)
            
            # Reset context menu position
            self._context_menu_position = None
        else:
            # Fall back to normal paste if no context position
            self.paste()
    
    def paste(self):
        """Paste text from clipboard at current position."""
        if self._mode != "edit":
            return
            
        # Get clipboard content
        clipboard = QGuiApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if mime_data.hasText():
            # Get text and current cursor position
            paste_text = mime_data.text()
            cursor = self.textCursor()
            html_pos = cursor.position()
            md_pos = self._map_cursor_to_markdown(html_pos)
            
            # Handle selection by removing selected text first
            if cursor.hasSelection():
                html_start = min(cursor.position(), cursor.anchor())
                html_end = max(cursor.position(), cursor.anchor())
                md_start = self._map_cursor_to_markdown(html_start)
                md_end = self._map_cursor_to_markdown(html_end)
                
                # Remove selected text
                self._markdown_text = self._markdown_text[:md_start] + self._markdown_text[md_end:]
                md_pos = md_start
            
            # Insert clipboard text
            self._markdown_text = self._markdown_text[:md_pos] + paste_text + self._markdown_text[md_pos:]
            
            # Render updated text
            self.render_text()
            
            # Position cursor after pasted text
            new_html_pos = self._find_html_position_for_md(md_pos + len(paste_text))
            new_cursor = self.textCursor()
            new_cursor.setPosition(new_html_pos)
            self.setTextCursor(new_cursor)
            
            # Check if we need to restore bullet point
            if not self._markdown_text.startswith('•'):
                self._markdown_text = '• ' + self._markdown_text.lstrip()
                self.render_text()
                # Adjust cursor if needed
                if html_pos < 2:
                    cursor = self.textCursor()
                    cursor.setPosition(2)
                    self.setTextCursor(cursor)

    def _find_html_position_for_md(self, md_position):
        """Find the HTML position corresponding to a Markdown position."""
        # Try to map the markdown position to a reasonable HTML position
        rendered_text = self.document().toPlainText()
        md_text = self._markdown_text
        
        # Simple case: exact lengths match
        if len(md_text) == len(rendered_text):
            return min(md_position, len(rendered_text))
        
        # Use ratio-based approximation for complex cases
        html_length = len(rendered_text)
        md_length = len(md_text)
        
        if md_length == 0:
            return 0
            
        # Calculate position based on ratio of lengths
        ratio = html_length / md_length
        approx_pos = int(md_position * ratio)
        return min(approx_pos, html_length)

# Hilfsfunktionen außerhalb der Klasse
def process_link(parent, url):                   # Verarbeitet Link-Klicks
    """Process clicked link based on URL."""
    logging.info(f"Processing link: {url}")
    if url == OPEN_FILE_ACTION:                  # Öffnet Datei-Dialog
        open_file_dialog(parent)                 # Zeigt Dialog
    else:
        display_link_clicked_message(parent, url)  # Zeigt Link-Info

def open_file_dialog(parent):                    # Zeigt Datei-Dialog
    """Open file dialog."""
    logging.info("Opening file dialog.")
    file_path, _ = QFileDialog.getOpenFileName(parent, "Open File", "")  # Öffnet Dialog
    if file_path:                               # Wenn Datei gewählt
        logging.info(f"File selected: {file_path}")
        QMessageBox.information(parent, "File Selected", f"Selected file: {file_path}")  # Zeigt Info
    else:
        logging.info("File selection cancelled.")

def display_link_clicked_message(parent, url):   # Zeigt Link-Info
    """Display message box with link URL."""
    logging.info(f"Displaying link clicked message for: {url}")
    QMessageBox.information(parent, "Link Clicked", f"Clicked link: {url}")  # Zeigt Dialog
