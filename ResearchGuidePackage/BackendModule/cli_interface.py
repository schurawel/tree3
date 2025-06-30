import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from ResearchGuidePackage.shared.communication import NamedPipeCommunication, TicketType
from ResearchGuidePackage.BackendModule.backend_operations import ResearchService

logger = logging.getLogger('CLI')
communication = NamedPipeCommunication()

# Initialize the service directly for local operation handling
service = ResearchService()

async def get_operations() -> Dict[str, Any]:
    """Get all available operations directly from the service"""
    try:
        # Call list_operations directly on the service
        response = await service.list_operations()
        
        # Extract operations from the response
        if isinstance(response, dict) and "result" in response:
            operations = response["result"]
            if isinstance(operations, dict):
                return operations
        
        logger.error("Failed to get operations list")
        return {}
    except Exception as e:
        logger.error(f"Error getting operations: {e}")
        return {}

async def send_operation_request(operation_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send operation request using the request_and_get_response method"""
    try:
        # Use the built-in request_and_get_response method
        params = params or {}
        success, response_content, error_message = await communication.request_and_get_response(
            operation=operation_name,
            params=params,
            sender="CLI",
            receiver="Backend",
            channel_to="to_backend",
            channel_from="to_frontend",
            timeout=10
        )
        
        if success:
            return response_content
        else:
            logger.error(f"Error executing {operation_name}: {error_message}")
            return {"error": error_message or "Unknown error occurred"}
            
    except Exception as e:
        logger.exception(f"Exception in send_operation_request: {e}")
        return {"error": str(e)}

async def print_async(text: str):
    """Print text asynchronously to avoid blocking the event loop"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, print, text)

async def input_async(prompt: str = "") -> str:
    """Get user input asynchronously to avoid blocking the event loop"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

async def manual_test():
    """Backend Test Mode - Send Tickets (fully asynchronous)"""
    await print_async("\n=== ResearchGuide Backend Test CLI ===")
    
    # Get operations only once at startup
    await print_async("\nFetching available operations...")
    operations = await get_operations()
    op_menu = {}
    
    # Initialize with default operation if needed
    if not operations or not isinstance(operations, dict) or len(operations) == 0:
        await print_async("No operations available or invalid response. Using defaults...")
        operations = {
            "list_operations": {
                "name": "List Available Operations",
                "operation": "list_operations",
                "input": "Press Enter to continue",
                "params": [],
                "types": []
            }
        }
    
    # Create initial menu
    for i, (op_name, op_info) in enumerate(sorted(operations.items()), 1):
        op_menu[str(i)] = {
            "name": op_info.get("name", "Unknown Operation"),
            "operation": op_name,
            "input": op_info.get("input", ""),
            "params": op_info.get("params", []),
            "types": op_info.get("types", [])
        }
    
    # Show initial operations menu
    await print_async("\nAvailable Operations:")
    for num, op_data in op_menu.items():
        await print_async(f"{num}) {op_data['name']}")
    await print_async("r) Refresh operations")
    await print_async("q) Quit")
    
    while True:
        try:
            # Get user selection asynchronously
            choice = await input_async("\nSelect operation > ")
            
            if choice.lower() == 'q':
                await print_async("Exiting...")
                break
                
            if choice.lower() == 'r':
                # Only refresh operations when 'r' is pressed
                await print_async("\nRefreshing available operations...")
                operations = await get_operations()
                op_menu = {}
                
                if not operations or not isinstance(operations, dict) or len(operations) == 0:
                    await print_async("No operations available. Using defaults...")
                    operations = {
                        "list_operations": {
                            "name": "List Available Operations",
                            "operation": "list_operations",
                            "input": "Press Enter to continue",
                            "params": [],
                            "types": []
                        }
                    }
                
                # Recreate menu
                for i, (op_name, op_info) in enumerate(sorted(operations.items()), 1):
                    op_menu[str(i)] = {
                        "name": op_info.get("name", "Unknown Operation"),
                        "operation": op_name,
                        "input": op_info.get("input", ""),
                        "params": op_info.get("params", []),
                        "types": op_info.get("types", [])
                    }
                
                # Show refreshed operations menu
                await print_async("\nAvailable Operations:")
                for num, op_data in op_menu.items():
                    await print_async(f"{num}) {op_data['name']}")
                await print_async("r) Refresh operations")
                await print_async("q) Quit")
                continue
                
            if choice not in op_menu:
                await print_async("Invalid selection!")
                await asyncio.sleep(0.5)
                continue
            
            # Get selected operation
            selected = op_menu[choice]
            operation_name = selected["operation"]
            params = {}
            
            # Check if operation needs parameters
            if selected["params"]:
                await print_async(f"\n{selected['input']}")
                user_input = await input_async("> ")
                user_input = user_input.strip()
                
                # Parse user input
                if user_input:
                    input_values = user_input.split()
                    for i, (param_name, param_type) in enumerate(zip(selected["params"], selected["types"])):
                        if i < len(input_values):
                            try:
                                # Convert value based on type
                                if param_type == "int":
                                    params[param_name] = int(input_values[i])
                                elif param_type == "float":
                                    params[param_name] = float(input_values[i])
                                elif param_type == "bool":
                                    params[param_name] = input_values[i].lower() in ("true", "yes", "1")
                                else:  # Default to string
                                    params[param_name] = input_values[i]
                            except ValueError:
                                await print_async(f"Error: Could not convert '{input_values[i]}' to {param_type}")
            
            # Send request and display result
            await print_async(" ")
            response = await send_operation_request(operation_name, params)
            
            # Process and display response
            if "error" in response:
                await print_async("\n--- Error ---")
                await print_async(f"Error: {response['error']}")
                await print_async("-------------")
            else:
                await print_async("\n--- Response ---")
                if "result" in response:
                    await print_async(f"Result: {response['result']}")
                    
                    # Show additional fields
                    for key, value in response.items():
                        if key != "result" and not key.startswith("_"):
                            if key == "graph_data" and isinstance(value, str) and len(value) > 100:
                                await print_async(f"{key}: <binary data, length: {len(value)}>")
                            else:
                                await print_async(f"{key}: {value}")
                else:
                    await print_async(str(response))
                    
                await print_async("---------------")
                
            # Remind user of available options after each operation
            await print_async("\nSelect operation number, 'r' to refresh operations list, or 'q' to quit")
            
        except Exception as e:
            await print_async(f"Error: {str(e)}")
            logger.exception("Error in manual_test")
            await asyncio.sleep(1)
