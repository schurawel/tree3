"""
ResearchGuide Backend Server
===========================
Standalone script to run the backend server.

This module serves as the main entry point for the ResearchGuide backend server.
It loads configuration, initializes the ResearchService, sets up the API server,
and registers all available operations.

Usage:
------
python backend.py [--config CONFIG_PATH] [--debug]

Author:
-------
Jason A. Schurawel
"""

import logging
import sys
import os
import argparse
import yaml
import inspect
from waitress import serve
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="ResearchGuide Backend Server")
    parser.add_argument("--config", type=str, help="Path to network config file")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--port", type=int, help="Override port from config file")
    return parser.parse_args()

def load_config(config_path=None):
    """
    Load network configuration from YAML.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Dict with configuration
    """
    # Default config
    config = {
        'backend': {
            'host': '0.0.0.0',
            'port': 5000
        }
    }
    
    try:
        # Find config file
        if not config_path:
            # Get project root
            project_root = os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            ))
            config_path = os.path.join(project_root, 'ResearchGuidePackage', 'config', 'network_config.yaml')
        
        # Load config if exists
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config and 'backend' in yaml_config:
                    config.update(yaml_config)
                    logger.info(f"Loaded network config from {config_path}")
                    logger.info(f"Backend port from config: {config['backend']['port']}")
                else:
                    logger.warning("Config file exists but contains no backend configuration")
        else:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            
    except Exception as e:
        logger.error(f"Error loading config: {e}")
    
    return config

def main():
    """Run the backend server."""
    args = parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Add project root to path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(project_root))
    
    # Load network config
    config = load_config(args.config)
    backend_config = config.get('backend', {})
    
    # Get host and port - command line args override config file
    host = backend_config.get('host', '0.0.0.0')
    port = args.port if args.port is not None else backend_config.get('port', 5030)  # Default to 5030
    
    # Log the port we'll be using
    logger.info(f"Using backend port: {port}")
    
    # Determine the actual host for connections (localhost if binding to all interfaces)
    connection_host = "localhost" if host == "0.0.0.0" else host
    
    logger.info(f"Backend will be available at: http://{connection_host}:{port}")
    
    try:
        # Import backend modules
        from ResearchGuidePackage.BackendModule.backend_manager import create_app
        from ResearchGuidePackage.BackendModule.server import setup_api_server
        from ResearchGuidePackage.BackendModule.backend_operations import ResearchService
        
        # Initialize the ResearchService first
        service = ResearchService()
        logger.info("ResearchService initialized")
        
        # Initialize Flask app
        app = create_app()
        logger.info("Flask application created")
        
        # Initialize the API server
        api_server = setup_api_server(app)
        logger.info("API server initialized")
        
        # Register all operation methods from ResearchService with the API server
        registered_count = 0
        for name, method in inspect.getmembers(service, predicate=inspect.iscoroutinefunction):
            # Skip internal methods (starting with _) and placeholder methods
            if name.startswith("_") or name == "get_available_operations":
                continue
                
            # Create a wrapper function to handle async operations
            def create_operation_handler(method_name):
                async def handler(params):
                    try:
                        # Call the method with unpacked parameters
                        return await getattr(service, method_name)(**params)
                    except TypeError as e:
                        # Log parameter mismatch errors more helpfully
                        logger.error(f"Parameter mismatch for operation '{method_name}': {e}")
                        return {"error": f"Invalid parameters for '{method_name}': {str(e)}"}
                    except Exception as e:
                        logger.error(f"Error in operation '{method_name}': {str(e)}", exc_info=True)
                        return {"error": f"Operation error: {str(e)}"}
                
                # Create a synchronous wrapper around the async handler
                def sync_handler(params):
                    # Run the async handler in a new event loop
                    loop = asyncio.new_event_loop()
                    try:
                        return loop.run_until_complete(handler(params))
                    finally:
                        loop.close()
                        
                return sync_handler
            
            # Register the operation handler
            api_server.register_operation(name, create_operation_handler(name))
            registered_count += 1
            
        logger.info(f"Registered {registered_count} operations from ResearchService")
        
        # Start the server
        logger.info(f"Starting backend server on {host}:{port}")
        serve(app, host=host, port=port)
        
    except ImportError as e:
        logger.error(f"Error importing backend modules: {e}")
        return 1
    except Exception as e:
        logger.error(f"Backend error: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Backend server stopped by user")
        sys.exit(0)
