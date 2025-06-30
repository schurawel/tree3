"""
ResearchGuide Frontend Application
=================================
Standalone script to run the frontend with proper platform configuration.

Usage:
------
python frontend.py [--backend-url URL]

Author:
-------
Jason A. Schurawel
"""

import asyncio
import logging
import sys
import os
import argparse
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="ResearchGuide Frontend Application")
    parser.add_argument("--backend-url", type=str, default="http://localhost:5000",
                        help="URL of the backend server")
    return parser.parse_args()

async def main():
    """Run the frontend application."""
    args = parse_args()
    
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)

    # Try to read backend URL from registry
    registry_path = os.path.join(os.path.dirname(os.path.dirname(project_root)), 
                                "ResearchGuidePackage", "shared", "register.json")
    if args.backend_url == "http://localhost:5000" and os.path.exists(registry_path):  # Default URL
        try:
            with open(registry_path, 'r') as f:
                registry_data = json.loads(f.read())
                
            if "backend" in registry_data and "url" in registry_data["backend"]:
                args.backend_url = registry_data["backend"]["url"]
                logger.info(f"Using backend URL from registry: {args.backend_url}")
        except Exception as e:
            logger.warning(f"Error reading registry file: {e}")

    try:
        # Import frontend module
        from frontend_manager import Frontend
        
        # Print diagnostic info
        logger.info(f"Connecting to backend at: {args.backend_url}")
        
        # Initialize and run frontend
        frontend = Frontend(backend_url=args.backend_url)
        frontend.init()
        
        # Run frontend
        await frontend.run()
    except ImportError as e:
        logger.error(f"Error importing frontend modules: {e}")
        return 1
    except Exception as e:
        logger.error(f"Frontend error: {e}")
        return 1

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Frontend application stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
