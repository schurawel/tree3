import logging
import asyncio

logger = logging.getLogger(__name__)

class NodeTypesManager:
    """Manages node types and their parameters."""
    
    def __init__(self, parent=None):
        """Initialize NodeTypesManager."""
        self.parent = parent
        self.node_types = {}
        self.parameters_cache = {}  # Cache for node type parameters
        self.loaded_from_backend = False

    async def get_node_types(self):
        """Get node types from the backend."""
        # Always try to fetch from backend
        await self.fetch_node_types()
        return self.node_types
    
    async def get_node_parameters(self, type_id):
        """Get parameters for a node type from backend."""
        try:
            # Check cache first
            if type_id in self.parameters_cache:
                logger.info(f"Using cached parameters for node type {type_id}")
                return self.parameters_cache[type_id]
            
            # Fetch from backend
            logger.info(f"Fetching parameters for node type {type_id} from backend")
            parameters = await self.fetch_node_type_parameters(type_id)
            
            if parameters:
                # Cache the parameters
                self.parameters_cache[type_id] = parameters
                return parameters
            else:
                logger.warning(f"No parameters found for node type {type_id}")
                return []
        except Exception as e:
            logger.error(f"Error getting node type parameters: {e}")
            return []

    async def get_default_color(self, type_id):
        """Get color for a node type from backend."""
        # Get the type data from backend
        node_types = await self.get_node_types()
        return node_types.get(type_id, {}).get("color", "skyblue")

    async def fetch_node_types(self):
        """Fetch node types from the backend."""
        try:
            if not self.parent or not hasattr(self.parent, 'communication'):
                logger.warning("Cannot get node types: parent or communication not available")
                return False
                
            success, content, error = await self.parent.communication.request_and_get_response(
                operation="get_node_types",
                params={},
                sender="Frontend"
            )
            
            if success and content:
                # Check if content is a dictionary with the expected structure
                if isinstance(content, dict):
                    # The node types might be in a 'result' field
                    node_types = content.get('result', content)
                    
                    # Make sure node_types is actually a dictionary
                    if isinstance(node_types, dict):
                        self.node_types = node_types
                        self.loaded_from_backend = True
                        logger.info(f"Successfully loaded {len(node_types)} node types from backend")
                        return True
                    else:
                        logger.error(f"Node types data is not a dictionary: {type(node_types)}")
                else:
                    logger.error(f"Content is not a dictionary: {type(content)}")
            else:
                logger.error(f"Error fetching node types: {error}")
            return False
        except Exception as e:
            logger.error(f"Exception in fetch_node_types: {e}", exc_info=True)
            return False
    
    async def fetch_node_type_parameters(self, type_id):
        """Fetch parameters for a specific node type from backend."""
        try:
            if not self.parent or not hasattr(self.parent, 'communication'):
                logger.warning("Cannot get node type parameters: parent or communication not available")
                return None
                
            success, content, error = await self.parent.communication.request_and_get_response(
                operation="get_node_type_parameters",
                params={"type_id": type_id},
                sender="Frontend"
            )
            
            if success and content:
                result = content.get('result', content)
                if "parameters" in result:
                    logger.info(f"Got {len(result['parameters'])} parameters for node type {type_id}")
                    return result["parameters"]
                else:
                    logger.warning(f"No parameters found in response for node type {type_id}")
            else:
                logger.error(f"Error fetching node type parameters: {error}")
            return None
        except Exception as e:
            logger.error(f"Exception in fetch_node_type_parameters: {e}")
            return None
            
    def clear_cache(self):
        """Clear cached data to force fresh data from backend."""
        self.node_types = {}
        self.parameters_cache = {}
        self.loaded_from_backend = False
