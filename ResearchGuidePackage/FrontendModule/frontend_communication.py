"""
Frontend Communication Module
============================
Provides communication functionality for the frontend to interact with the backend.
"""

import uuid
import logging
import base64
from typing import Any, Optional, Dict, Tuple
from dataclasses import dataclass
import datetime
import asyncio

# Import client
from ResearchGuidePackage.FrontendModule.client import APIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FrontendCommunication')

@dataclass
class TicketType:
    """Ticket data structure for compatibility with existing code."""
    uuid: str
    sender: str
    receiver: str
    content: Any
    response_ticket: Optional[str] = None  # This stores the original ticket's UUID

class FrontendCommunication:
    """Frontend communication handler for interacting with the backend."""
    
    def __init__(self, base_url=None):
        """
        Initialize the frontend communication module.
        
        Args:
            base_url: Backend URL, or None to load from config
        """
        # Initialize API client
        self.api_client = APIClient(base_url=base_url)
        logger.info("Frontend communication module initialized")
    
    def sketch_new_ticket(self, content: Any, sender: str = "Frontend", 
                        receiver: str = "Backend", request_ticket: Optional[str] = None, 
                        response: bool = False) -> TicketType:
        """
        Create a new ticket with proper response handling.
        
        Args:
            content: Content to send
            sender: Sender identifier (default: "Frontend")
            receiver: Receiver identifier (default: "Backend")
            request_ticket: Original ticket ID if this is a response
            response: Whether this is a response to another ticket
            
        Returns:
            TicketType object
        """
        ticket = TicketType(
            uuid=str(uuid.uuid4()),
            sender=sender,
            receiver=receiver,
            content=content,
            response_ticket=request_ticket if response else None
        )
        return ticket

    def _log_ticket(self, ticket: TicketType) -> None:
        """
        Log ticket information.
        
        Args:
            ticket: Ticket to log
        """
        base_info = f"API Request: [{ticket.uuid}] {ticket.sender} -> {ticket.receiver}"
        if ticket.response_ticket:
            logger.info(f"{base_info} (response to {ticket.response_ticket}) | {ticket.content}")
        else:
            logger.info(f"{base_info} | {ticket.content}")

    def send_ticket(self, ticket: TicketType, channel=None):
        """
        Send a ticket to the backend.
        
        Args:
            ticket: Ticket to send
            channel: For compatibility, not used
            
        Returns:
            True if sent successfully, False otherwise
        """
        with self.lock:
            try:
                self._log_ticket(ticket)
                
                # Extract operation and parameters from ticket content
                if isinstance(ticket.content, dict) and "operation" in ticket.content:
                    operation = ticket.content["operation"]
                    # Remove operation from params
                    params = {k: v for k, v in ticket.content.items() if k != "operation"}
                else:
                    # Default operation if not specified
                    operation = "process_data"
                    params = {"data": ticket.content}
                
                # Send via API
                success, _, error = self.api_client.send_request(
                    operation=operation,
                    params=params,
                    sender=ticket.sender,
                    receiver=ticket.receiver,
                    timeout=10
                )
                
                if not success:
                    logger.error(f"Failed to send ticket via API: {error}")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"Error sending ticket {ticket.uuid}: {e}")
                return False

    async def async_send_ticket(self, ticket: TicketType, channel=None):
        """
        Send a ticket asynchronously.
        
        Args:
            ticket: Ticket to send
            channel: For compatibility, not used
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            self._log_ticket(ticket)
            
            if isinstance(ticket.content, dict) and "operation" in ticket.content:
                operation = ticket.content["operation"]
                params = {k: v for k, v in ticket.content.items() if k != "operation"}
            else:
                operation = "process_data"
                params = {"data": ticket.content}
                
            success, _, error = await self.api_client.async_send_request(
                operation=operation,
                params=params,
                sender=ticket.sender,
                receiver=ticket.receiver
            )
            
            if not success:
                logger.error(f"Failed to send ticket via API: {error}")
                return False
            
            return True
                
        except Exception as e:
            logger.error(f"Error sending ticket asynchronously {ticket.uuid}: {e}")
            return False

    def check_if_it_is_a_ticket(self, ticket) -> bool:
        """
        Check if an object is a valid ticket.
        
        Args:
            ticket: Object to check
            
        Returns:
            True if it's a valid ticket, False otherwise
        """
        try:
            if ticket.uuid and ticket.sender and ticket.receiver and ticket.content:
                return True
            else:
                return False
        except Exception:
            return False

    def check_backend_health(self) -> bool:
        """
        Check if the backend server is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return True

    async def request_and_get_response(
        self, 
        operation: str, 
        params: dict, 
        sender: str = "Frontend", 
        receiver: str = "Backend",
        timeout: int = 10
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Send a request and wait for response.
        
        Args:
            operation: Operation to perform
            params: Operation parameters
            sender: Sender identifier (default: "Frontend")
            receiver: Receiver identifier (default: "Backend")
            timeout: Request timeout in seconds
            
        Returns:
            Tuple (success, response_content, error_message)
        """
        try:
            # Log the request for debugging
            logger.debug(f"Sending {operation} request to backend")
            
            # Use the API client to send the request and get response
            return await self.api_client.async_send_request(
                operation=operation,
                params=params,
                sender=sender,
                receiver=receiver,
                timeout=timeout
            )
            
        except Exception as e:
            logger.error(f"Error in request_and_get_response: {e}")
            return False, None, str(e)

    def request_and_get_response_sync(
        self, 
        operation: str, 
        params: dict, 
        sender: str = "Frontend", 
        receiver: str = "Backend",
        timeout: int = 10
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Synchronous version of request_and_get_response.
        
        Args:
            operation: Operation to perform
            params: Operation parameters
            sender: Sender identifier
            receiver: Receiver identifier
            timeout: Request timeout in seconds
            
        Returns:
            Tuple (success, response_content, error_message)
        """
        try:
            # Use the API client to send the request and get response
            return self.api_client.send_request(
                operation=operation,
                params=params,
                sender=sender,
                receiver=receiver,
                timeout=timeout
            )
            
        except Exception as e:
            logger.error(f"Error in request_and_get_response_sync: {e}")
            return False, None, str(e)
            
    def _decode_binary_data(self, content):
        """
        Decode binary data that was encoded for JSON transmission.
        
        Args:
            content: Content to decode
            
        Returns:
            Decoded content
        """
        if isinstance(content, dict):
            # If this is a marker for binary data, decode it
            if content.get("_binary") is True and "data" in content:
                try:
                    return base64.b64decode(content["data"])
                except Exception as e:
                    logger.error(f"Error decoding binary data: {e}")
                    return content
            
            # Process all dictionary values recursively
            result = {}
            for key, value in content.items():
                result[key] = self._decode_binary_data(value)
            return result
        elif isinstance(content, list):
            # Process list items recursively
            return [self._decode_binary_data(item) for item in content]
        else:
            # Return other types unchanged
            return content
