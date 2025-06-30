"""
Frontend Client API Module
=========================
Provides simplified client-side API functionality for the frontend.
"""

import requests
import logging
import yaml
import os
import uuid
from typing import Any, Dict, Optional, Tuple
import asyncio

# Configure logging
logger = logging.getLogger('FrontendClient')

class APIClient:
    """Client for making API requests to the backend server."""
    
    def __init__(self, base_url=None):
        """
        Initialize the API client with backend server URL.
        
        Args:
            base_url: URL to connect to backend, or None to load from config
        """
        # Get backend URL from config if not provided
        if base_url is None:
            config = self._load_config()
            host = config.get('backend', {}).get('host', 'localhost')
            port = config.get('backend', {}).get('port', 5000)
            base_url = f"http://{host}:{port}"
            
        self.base_url = base_url
        logger.info(f"API Client initialized with server URL: {self.base_url}")
    
    def _load_config(self) -> Dict:
        """Load network configuration from YAML file."""
        try:
            # Find the config file path
            module_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(os.path.dirname(module_dir), 'config', 'network_config.yaml')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
                    logger.info(f"Loaded network config from {config_file}")
                    return config
            else:
                logger.warning(f"Config file not found: {config_file}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    def send_request(
        self, 
        operation: str, 
        params: dict, 
        sender: str = "Frontend",
        receiver: str = "Backend",
        timeout: int = 10
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Send a request to the backend server and get response.
        
        Args:
            operation: Operation name to execute
            params: Dictionary of parameters for the operation
            sender: Name of the sending component
            receiver: Name of the receiving component
            timeout: Timeout in seconds
            
        Returns:
            tuple: (success, response_content, error_message)
        """
        request_id = str(uuid.uuid4())
        
        try:
            # Create request payload
            payload = {
                "ticket_id": request_id,
                "sender": sender,
                "receiver": receiver,
                "operation": operation,
                "params": params
            }
            
            # Send the request
            logger.debug(f"Sending API request: {operation} (ID: {request_id})")
            response = requests.post(
                f"{self.base_url}/api/request",
                json=payload,
                timeout=timeout
            )
            
            # Process the response
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("success", False):
                    content = response_data.get("content")
                    return True, content, None
                    
                error_msg = response_data.get("error", "Unknown error")
                logger.warning(f"API request failed: {error_msg}")
                return False, None, error_msg
                
            error_msg = f"HTTP error: {response.status_code}"
            logger.warning(f"API request failed: {error_msg}")
            return False, None, error_msg
            
        except requests.Timeout:
            logger.warning(f"API request timed out after {timeout}s")
            return False, None, f"Request timed out (timeout: {timeout}s)"
            
        except requests.ConnectionError:
            logger.error("Connection to backend lost")
            return False, None, "Connection to backend lost"
            
        except Exception as e:
            logger.error(f"Error in API request: {e}")
            return False, None, str(e)
    
    async def async_send_request(
        self, 
        operation: str, 
        params: dict, 
        sender: str = "Frontend",
        receiver: str = "Backend",
        timeout: int = 10
    ) -> Tuple[bool, Any, Optional[str]]:
        """Async version of send_request."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.send_request(operation, params, sender, receiver, timeout)
        )
        

    # Add compatibility methods for code that still uses old API
    async def request_and_get_response(
        self,
        operation: str,
        params: dict,
        sender: str = "Frontend",
        receiver: str = "Backend",
        timeout: int = 10
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Legacy method for compatibility with existing code.
        
        Args:
            operation: Operation name to execute
            params: Dictionary of parameters for the operation
            sender: Name of the sending component
            receiver: Name of the receiving component
            timeout: Timeout in seconds
            
        Returns:
            tuple: (success, response_content, error_message)
        """
        logger.debug(f"Using compat method request_and_get_response for {operation}")
        return await self.async_send_request(operation, params, sender, receiver, timeout)
        
    # Compatibility methods for older code
    def join_channel(self, channel):
        """
        Compatibility method - does nothing in API mode.
        
        Args:
            channel: Channel name (not used)
        """
        logger.debug(f"join_channel called with {channel} - not needed in API mode")
        return True
        
    def create_channel(self, channel):
        """
        Compatibility method - does nothing in API mode.
        
        Args:
            channel: Channel name (not used)
        """
        logger.debug(f"create_channel called with {channel} - not needed in API mode")
        return f"api://{channel}"
        
    def get_response(self, ticket, channel, timeout=None):
        """
        Compatibility method - not used in API mode.
        
        Args:
            ticket: Ticket object 
            channel: Channel name
            timeout: Timeout in seconds
            
        Returns:
            None as responses are handled in send_request
        """
        logger.debug(f"get_response called - not needed in API mode")
        return None
        
    def flush_channel(self, channel, timeout=1.0):
        """
        Compatibility method - does nothing in API mode.
        
        Args:
            channel: Channel name
            timeout: Timeout in seconds
        """
        logger.debug(f"flush_channel called - not needed in API mode")
        return True
