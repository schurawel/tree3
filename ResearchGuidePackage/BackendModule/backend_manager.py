"""
ResearchGuide Backend
=========================

Features:
---------
- The Base for the ResearchGuide application.
- This module exposes an API server that processes requests from the frontend.

Usage:
------
Run the application using the following command:
    python /home/client1/Documents/researchguide/ResearchGuideModule/backend/backend_manager.py
The backend server will start and listen for API requests from the frontend.

Author:
-------
Jason A. Schurawel

"""
import logging
import sys
import os
from flask import Flask, request, jsonify
import asyncio
import inspect

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from ResearchGuidePackage.BackendModule.server import APIServer
from ResearchGuidePackage.BackendModule.backend_operations import ResearchService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Backend')

# Create a global instance of ResearchService
research_service = ResearchService()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({"status": "healthy"})
    
    @app.route('/api/request', methods=['POST'])
    def handle_request():
        """Process requests from the frontend (synchronous wrapper)."""
        try:
            data = request.json
            
            # Log incoming request
            logger.info(f"Received API request: {data.get('operation')}")
            
            # Extract request data
            operation = data.get('operation')
            params = data.get('params', {})
            
            # Check if the operation exists in ResearchService
            if not hasattr(research_service, operation) or not inspect.iscoroutinefunction(getattr(research_service, operation)):
                logger.error(f"Unknown operation: {operation}")
                return jsonify(APIServer.create_response(False, error=f"Unknown operation: {operation}"))
            
            # Get the method to call
            method = getattr(research_service, operation)
            
            # Process the request asynchronously
            loop = asyncio.new_event_loop()
            try:
                response_content = loop.run_until_complete(method(**params))
                return jsonify(APIServer.create_response(True, response_content))
            except Exception as e:
                logger.error(f"Error executing operation {operation}: {e}", exc_info=True)
                return jsonify(APIServer.create_response(False, error=f"Error: {str(e)}"))
            finally:
                loop.close()
            
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            return jsonify(APIServer.create_response(False, error=str(e)))
    
    return app

def main():
    """Run the backend server directly (development mode)."""
    from waitress import serve
    
    app = create_app()
    logger.info("Starting backend server in development mode on port 5000")
    serve(app, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()
