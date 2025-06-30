import logging
import os
import asyncio
from PyQt6 import QtWidgets, QtCore
from ResearchGuidePackage.FrontendModule.client import APIClient
import base64

communication = APIClient()

logger = logging.getLogger(__name__)

class FileManager:
    """Manages file operations and file-related UI elements."""
    
    def __init__(self, parent):
        """Initialize FileManager."""
        self.parent = parent
        self.file_updates = None
        self.file_info_label = None
    
    def create_file_info_field(self):
        """Create a label to display file information."""
        self.file_info_label = QtWidgets.QLabel("No file selected", self.parent)
        return self.file_info_label
    
    async def process_upload(self, node_id, file_path):
        """Process file upload by sending a ticket to the backend."""
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return False, "File does not exist"

            logger.info(f"Uploading file {file_path} for node {node_id}")
            
            # Send upload request to backend
            success, content, error = await communication.request_and_get_response(
                operation="upload_node_file",
                params={
                    "node_id": node_id,
                    "file_path": file_path
                },
                sender="Frontend",
                timeout=60  # Longer timeout for large files
            )
            
            if success and content and content.get("result"):
                logger.info(f"File upload successful: {os.path.basename(file_path)}")
                return True, content
            else:
                error_msg = error or "Unknown error during upload"
                logger.error(f"Upload failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.exception(f"Exception during file upload: {e}")
            return False, str(e)
    
    async def process_download(self, node_id, save_path):
        """Process file download by sending a ticket to the backend."""
        try:    
            logger.info(f"Requesting file for node {node_id}")
            
            # Request file content from backend
            success, content, error = await communication.request_and_get_response(
                operation="get_node_file",
                params={"node_id": str(node_id)},
                sender="Frontend",
                timeout=30  # Longer timeout for large files
            )
            
            if success and content and "file_content" in content:
                # Write the file content to the save path
                logger.info(f"Received file data ({len(content['file_content'])} bytes), saving to {save_path}")
                
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                    
                    with open(save_path, 'wb') as f:
                        f.write(content["file_content"])
                    
                    logger.info(f"File successfully saved to {save_path}")
                    return True, {"file_path": save_path, "size": len(content["file_content"])}
                except Exception as write_error:
                    logger.error(f"Error writing file: {write_error}")
                    return False, f"Error writing file: {write_error}"
            else:
                error_msg = error or "Failed to get file from backend"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            logger.exception(f"Exception during file download: {e}")
            return False, str(e)
    
    def set_file_update(self, action, file_path, node_id=None, save_path=None):
        """Set file update information to be processed during form submission."""
        update_info = {'action': action}
        
        if action in ['upload', 'replace']:
            update_info['file_path'] = file_path
            update_info['node_id'] = node_id
        elif action == 'download':
            update_info['save_path'] = save_path
            update_info['node_id'] = node_id
            update_info['original_path'] = file_path
            
        self.file_updates = update_info
        return True

    def upload_file(self, node_id=None):
        """Handle uploading a file for a node."""
        try:
            # Show file dialog
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self.parent, "Select File to Upload", "", "All Files (*)"
            )
            
            if file_path:
                # Store file information for later reference
                self.set_file_update('upload', file_path, node_id)
                
                # Update UI
                if self.file_info_label:
                    self.file_info_label.setText(f"Selected for upload: {os.path.basename(file_path)}")
                
                logger.info(f"File selected for upload: {file_path}")
                
                # Immediately send upload request to backend
                if node_id:
                    # Create a task to handle the upload
                    asyncio.create_task(self._process_upload_async(node_id, file_path))
                return True
            return False
        except Exception as e:
            logger.error(f"Error selecting file: {e}")
            QtWidgets.QMessageBox.critical(self.parent, "Error", f"Error selecting file: {e}")
            return False

    def replace_file(self, node_id):
        """Handle replacing a file for a node."""
        try:
            # Show file dialog
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self.parent, "Select File to Replace With", "", "All Files (*)"
            )
            
            if file_path:
                # Store file information for later reference
                self.set_file_update('replace', file_path, node_id)
                
                # Update UI
                if self.file_info_label:
                    self.file_info_label.setText(f"Selected for replacement: {os.path.basename(file_path)}")
                
                logger.info(f"File selected for replacement: {file_path}")
                
                # Immediately send replace request to backend (same as upload)
                if node_id:
                    # Create a task to handle the upload
                    asyncio.create_task(self._process_upload_async(node_id, file_path))
                return True
            return False
        except Exception as e:
            logger.error(f"Error selecting replacement file: {e}")
            QtWidgets.QMessageBox.critical(self.parent, "Error", f"Error selecting replacement file: {e}")
            return False

    async def _process_upload_async(self, node_id, file_path):
        """Process file upload asynchronously."""
        try:
            # Show progress dialog
            progress = QtWidgets.QProgressDialog(
                f"Uploading {os.path.basename(file_path)}...", 
                "Cancel", 0, 100, 
                QtWidgets.QApplication.activeWindow() or self.parent
            )
            progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
            progress.setValue(10)
            
            # Process the upload
            success, result = await self.process_upload(node_id, file_path)
            progress.setValue(80)
            
            # Handle result
            if success:
                progress.setValue(100)
                QtWidgets.QMessageBox.information(
                    QtWidgets.QApplication.activeWindow() or self.parent,
                    "Upload Complete",
                    f"File {os.path.basename(file_path)} uploaded successfully."
                )
                logger.info(f"Upload successful for node {node_id}")
            else:
                error_msg = result or "Unknown error"
                QtWidgets.QMessageBox.critical(
                    QtWidgets.QApplication.activeWindow() or self.parent,
                    "Upload Failed",
                    f"Error uploading file: {error_msg}"
                )
                logger.error(f"Upload failed for node {node_id}: {error_msg}")
            
            # Close progress dialog
            progress.close()
            
        except Exception as e:
            logger.exception(f"Error in _process_upload_async: {e}")
            QtWidgets.QMessageBox.critical(
                QtWidgets.QApplication.activeWindow() or self.parent,
                "Upload Error",
                f"Error processing upload: {e}"
            )

    def download_file(self, node_id, original_file_path):
        """Start a simple download process with no complexity."""
        # Just create the task - no tracking, no callbacks
        asyncio.create_task(self._download_file_async(node_id, original_file_path))
        logger.info(f"Started download task for node {node_id}")

    async def _download_file_async(self, node_id, original_file_path):
        """Self-contained download process."""
        try:
            # Get suggested filename from original path
            suggested_name = os.path.basename(original_file_path) if original_file_path else f"node_{node_id}.file" 
            
            # Show save dialog
            save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                QtWidgets.QApplication.activeWindow() or self.parent,
                "Save File As", 
                suggested_name, 
                "All Files (*)"
            )
            
            if not save_path:
                logger.info("Download canceled by user")
                return
                
            # Get file from backend
            from ResearchGuidePackage.FrontendModule.client import APIClient
            comm = APIClient()
            
            logger.info(f"Requesting file content for node {node_id}")
            success, content, error = await comm.request_and_get_response(
                operation="get_node_file",
                params={"node_id": str(node_id)},
                sender="Frontend",
                timeout=60
            )
            
            if not success or not content or not content.get("result"):
                error_msg = error or content.get("error") or "Unknown error"
                logger.error(f"Download failed: {error_msg}")
                QtWidgets.QMessageBox.critical(
                    QtWidgets.QApplication.activeWindow() or self.parent,
                    "Download Failed", 
                    f"Unable to download file: {error_msg}"
                )
                return
                
            if "file_content" not in content:
                logger.error("No file content in response")
                QtWidgets.QMessageBox.critical(
                    QtWidgets.QApplication.activeWindow() or self.parent,
                    "Download Failed", 
                    "Response missing file content"
                )
                return
                
            # Decode base64 content
            file_bytes = base64.b64decode(content["file_content"])
            logger.info(f"Decoded file content: {len(file_bytes)} bytes")
                
            # Save file
            try:
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(file_bytes)
                    
                # Show success message
                QtWidgets.QMessageBox.information(
                    QtWidgets.QApplication.activeWindow() or self.parent,
                    "Download Complete", 
                    f"File saved to {save_path}"
                )
            except Exception as save_error:
                logger.error(f"Error saving file: {save_error}")
                QtWidgets.QMessageBox.critical(
                    QtWidgets.QApplication.activeWindow() or self.parent,
                    "Save Error", 
                    f"Error saving file: {save_error}"
                )
                
        except Exception as e:
            logger.exception(f"Error during download: {e}")
            QtWidgets.QMessageBox.critical(
                QtWidgets.QApplication.activeWindow() or self.parent,
                "Download Error", 
                str(e)
            )

    def get_file_updates(self):
        """Get the current file updates."""
        return self.file_updates
        
    def has_file_updates(self):
        """Check if there are any file updates pending."""
        return self.file_updates is not None and 'action' in self.file_updates
