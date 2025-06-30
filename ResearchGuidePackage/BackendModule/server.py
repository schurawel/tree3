"""
Backend Server API Module
========================
Provides server-side API request handling functionality for the backend.
"""

import logging
import json
from typing import Any, Dict, Callable, Optional
from flask import Flask, request, jsonify, Blueprint

# Configure logging
logger = logging.getLogger('BackendServer')

class APIServer:
    """Server-side API handler for processing incoming requests."""
    
    def __init__(self):
        """Initialize the API server."""
        self._operation_handlers = {}
        self._api_blueprint = None
    
    def register_operation(self, operation_name: str, handler: Callable):
        """
        Register a handler function for a specific API operation.
        
        Args:
            operation_name: Name of the operation
            handler: Function to handle the operation
        """
        self._operation_handlers[operation_name] = handler
        logger.info(f"Registered handler for operation: {operation_name}")
    
    def create_blueprint(self, url_prefix: str = '/api') -> Blueprint:
        """
        Create a Flask blueprint with all API endpoints.
        
        Args:
            url_prefix: URL prefix for all API routes
            
        Returns:
            Flask Blueprint with API routes
        """
        if self._api_blueprint is not None:
            return self._api_blueprint
            
        bp = Blueprint('api', __name__, url_prefix=url_prefix)
        
        # Health check endpoint
        @bp.route('/health', methods=['GET'])
        def health_check():
            return jsonify({'status': 'ok', 'service': 'backend'}), 200
        
        # Main API request endpoint
        @bp.route('/request', methods=['POST'])
        def handle_request():
            try:
                # Parse request data
                if not request.is_json:
                    logger.warning("Request content-type is not application/json")
                    return jsonify(self.create_error_response("Invalid request format: not JSON")), 400
                
                data = request.get_json()
                logger.debug(f"Received API request: {json.dumps(data)[:200]}")
                
                # Extract request fields
                ticket_id = data.get('ticket_id', 'unknown')
                operation = data.get('operation')
                params = data.get('params', {})
                sender = data.get('sender', 'unknown')
                
                # Validate required fields
                if not operation:
                    return jsonify(self.create_error_response("Missing required field: operation")), 400
                
                # Handle the operation
                handler = self._operation_handlers.get(operation)
                if not handler:
                    logger.warning(f"No handler registered for operation: {operation}")
                    return jsonify(self.create_error_response(f"Unknown operation: {operation}")), 404
                
                # Execute the handler
                try:
                    logger.info(f"Processing operation '{operation}' from {sender} (ticket: {ticket_id})")
                    result = handler(params)
                    return jsonify(self.create_success_response(result))
                except Exception as e:
                    logger.error(f"Error processing operation {operation}: {e}", exc_info=True)
                    return jsonify(self.create_error_response(f"Error processing request: {str(e)}")), 500
                
            except Exception as e:
                logger.error(f"Unhandled API server error: {e}", exc_info=True)
                return jsonify(self.create_error_response(f"Server error: {str(e)}")), 500
        
        self._api_blueprint = bp
        return bp
    
    @staticmethod
    def create_success_response(content: Any = None) -> Dict:
        """Create a standardized success response."""
        return {"success": True, "content": content}
    
    @staticmethod
    def create_error_response(error: str) -> Dict:
        """Create a standardized error response."""
        return {"success": False, "error": error}
    
    @staticmethod
    def create_response(success: bool, content: Any = None, error: str = None) -> Dict:
        """
        Create a standardized response combining success and error handling.
        
        Args:
            success: Whether the operation was successful
            content: Response content (for successful operations)
            error: Error message (for failed operations)
            
        Returns:
            Standardized response dictionary
        """
        if success:
            return APIServer.create_success_response(content)
        else:
            return APIServer.create_error_response(error)

def setup_api_server(app: Flask) -> APIServer:
    """
    Set up the API server with a Flask application.
    
    Args:
        app: Flask application instance
        
    Returns:
        Configured APIServer instance
    """
    server = APIServer()
    app.register_blueprint(server.create_blueprint())
    
    logger.info("API server initialized")
    return server
