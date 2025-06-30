"""
Backend Communication Module
==========================
Provides server-side communication functionality for handling frontend requests.
"""

import uuid
import logging
import json
from typing import Any, Dict, Callable, Optional
from dataclasses import dataclass
import base64
from flask import Blueprint, Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BackendCommunication')

@dataclass
class TicketType:
    """Ticket data structure for compatibility with existing code."""
    uuid: str
    sender: str
    receiver: str
    content: Any
    response_ticket: Optional[str] = None  # This stores the original ticket's UUID

class BackendCommunication:
    """Backend communication handler for processing frontend requests."""
    
    def __init__(self):
        """Initialize the backend communication module."""
        self._operation_handlers = {}
        self._api_blueprint = None
        logger.info("Backend communication module initialized")
    
    def register_operation(self, operation_name: str, handler_function: Callable):
        """
        Register a handler function for a specific API operation.
        
        Args:
            operation_name: Name of the operation
            handler_function: Function to handle the operation
        """
        self._operation_handlers[operation_name] = handler_function
        logger.info(f"Registered handler for operation: {operation_name}")
    
    def get_operation_handler(self, operation_name: str) -> Optional[Callable]:
        """
        Get the handler function for an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Handler function or None if not found
        """
        return self._operation_handlers.get(operation_name)
    
    def list_operations(self) -> list:
        """
        Get a list of all registered operations.
        
        Returns:
            List of operation names
        """
        return list(self._operation_handlers.keys())
    
    def create_response_ticket(self, request_ticket: TicketType, content: Any) -> TicketType:
        """
        Create a response ticket for a request.
        
        Args:
            request_ticket: Original request ticket
            content: Response content
            
        Returns:
            Response ticket
        """
        return TicketType(
            uuid=str(uuid.uuid4()),
            sender="Backend",
            receiver=request_ticket.sender,
            content=content,
            response_ticket=request_ticket.uuid
        )
    
    def create_api_blueprint(self, url_prefix: str = '/api') -> Blueprint:
        """
        Create a Flask blueprint with API endpoints.
        
        Args:
            url_prefix: URL prefix for all routes
            
        Returns:
            Flask Blueprint
        """
        if self._api_blueprint is not None:
            return self._api_blueprint
            
        bp = Blueprint('api', __name__, url_prefix=url_prefix)
        
        # Health check endpoint
        @bp.route('/health', methods=['GET'])
        def health_check():
            return jsonify({'status': 'ok', 'service': 'backend'}), 200
        
        # Main request handling endpoint
        @bp.route('/request', methods=['POST'])
        def handle_request():
            try:
                # Parse request data
                if not request.is_json:
                    logger.warning("Request content-type is not application/json")
                    return jsonify(self.create_error_response("Invalid request format: not JSON")), 400
                
                data = request.get_json()
                
                # Extract request fields
                ticket_id = data.get('ticket_id', 'unknown')
                operation = data.get('operation')
                params = data.get('params', {})
                sender = data.get('sender', 'unknown')
                
                # Log the request
                logger.info(f"Received API request: {operation} from {sender} (ticket: {ticket_id})")
                
                # Validate required fields
                if not operation:
                    return jsonify(self.create_error_response("Missing required field: operation")), 400
                
                # Find handler for the operation
                handler = self._operation_handlers.get(operation)
                if not handler:
                    logger.warning(f"No handler registered for operation: {operation}")
                    return jsonify(self.create_error_response(f"Unknown operation: {operation}")), 404
                
                # Execute the handler
                try:
                    result = handler(params)
                    logger.debug(f"Operation '{operation}' completed successfully")
                    return jsonify(self.create_success_response(result))
                except Exception as e:
                    logger.error(f"Error processing operation {operation}: {e}", exc_info=True)
                    return jsonify(self.create_error_response(f"Error processing request: {str(e)}")), 500
                
            except Exception as e:
                logger.error(f"Unhandled API request error: {e}", exc_info=True)
                return jsonify(self.create_error_response(f"Server error: {str(e)}")), 500
        
        self._api_blueprint = bp
        return bp
    
    def create_success_response(self, content: Any = None) -> Dict:
        """
        Create a standardized success response.
        
        Args:
            content: Response content
            
        Returns:
            Response dictionary
        """
        return {"success": True, "content": content}
    
    def create_error_response(self, error: str) -> Dict:
        """
        Create a standardized error response.
        
        Args:
            error: Error message
            
        Returns:
            Response dictionary
        """
        return {"success": False, "error": error}
    
    def _encode_binary_data(self, content: Any) -> Any:
        """
        Encode binary data for JSON transmission.
        
        Args:
            content: Content to encode
            
        Returns:
            Encoded content
        """
        if isinstance(content, bytes):
            # Encode binary data for JSON
            return {
                "_binary": True,
                "data": base64.b64encode(content).decode('ascii')
            }
        elif isinstance(content, dict):
            # Process dictionary values recursively
            result = {}
            for key, value in content.items():
                result[key] = self._encode_binary_data(value)
            return result
        elif isinstance(content, list):
            # Process list items recursively
            return [self._encode_binary_data(item) for item in content]
        else:
            # Return other types unchanged
            return content

def setup_backend_communication(app: Flask) -> BackendCommunication:
    """
    Set up backend communication with a Flask application.
    
    Args:
        app: Flask application
        
    Returns:
        Configured BackendCommunication instance
    """
    comm = BackendCommunication()
    app.register_blueprint(comm.create_api_blueprint())
    
    # Register basic system operations
    comm.register_operation("system_info", lambda _: {
        "status": "ok",
        "version": "1.0.0",
        "operations": comm.list_operations()
    })
    
    logger.info("Backend communication set up with Flask application")
    return comm
