"""
ResearchGuide Frontend
=========================

Features:
---------
- A frontend for the ResearchGuide application that allows users to interact with the application.
- Uses API calls to communicate with the backend server.

Usage:
------
Run the application using the following command:
    python /home/client1/Documents/researchguide/ResearchGuideModule/frontend/frontend_manager.py
This starts the frontend application which communicates with the backend through API calls.

Author:
-------
Jason A. Schurawel

"""
import asyncio
import logging
import qasync
from PyQt6.QtWidgets import QApplication
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ResearchGuidePackage.FrontendModule.main_window import MainWindow
from ResearchGuidePackage.FrontendModule.client import APIClient

# Initialize API client
api_client = APIClient()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Frontend')

class Frontend:
    """
    Frontend component for the ResearchGuide application.
    
    This class manages the user interface and user interactions,
    and communicates with the backend through API calls.
    """
    
    def __init__(self, backend_url=None): # Changed default to None
        """
        Initialize the Frontend component.
        """
        self.app = None
        self.loop = None
        self.main_window = None
        self.initialized = False
        self.api_client = APIClient(backend_url) 
    
    def init(self):
        """
        Initialize the frontend systems.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        self.app = QApplication.instance() or QApplication(sys.argv)
        # Create and set the event loop once
        self.loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        # Create main window with reference to frontend
        self.main_window = MainWindow()
        self.main_window.show()
        self.initialized = True
        logger.info("Frontend initialized")
        
        return True
            
    async def run(self):
        """
        Run the frontend component asynchronously.
        
        This method starts the frontend event loop and handles user interactions.
        
        Returns:
            None
        """
        logger.info("Frontend running")
        while True:
            self.app.processEvents()
            await asyncio.sleep(0.01)

    def get_loop(self):
        return self.loop
    
    async def request_backend(self, operation, params):
        """Make API request to backend and return results."""
        success, response, error = self.api_client.send_request(operation, params)
        if not success:
            logger.error(f"Backend request failed: {error}")
        return success, response, error
    
async def run_frontend():
    """Run the frontend application."""
    frontend = Frontend()
    frontend.init()
    await frontend.run()

def main():
    """Initialize and run the application."""
    try:
        asyncio.run(run_frontend())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")

if __name__ == "__main__":
    main()