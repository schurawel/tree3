"""
Backend Operations
==================

This module defines the ResearchService class, which handles various
operations related to graph manipulation and calculations.

Extending Functionality:
------------------------
To add a new operation:
1.  Create a new async method within the ResearchService class.
2.  The method should accept relevant parameters with type hints.
3.  The method MUST return a dictionary with the following keys:
    *   "name": User-friendly name of the operation (string).
    *   "input": Input instructions for the CLI (string).
    *   "params": List of parameter names (list of strings).
    *   "types": List of parameter types (list of type objects).
    *   "operation": Unique operation identifier (string, same as method name).
    *   "result": The result of the operation (can be any type).
4.  Ensure that the method handles cases where parameters are None
    (for metadata retrieval).

Example:
--------
async def new_operation(self, param1: str = None, param2: int = None) -> dict:
    \"\"\"Description of the new operation\"\"\"
    return {
        "name": "New Operation Name",
        "input": "Enter param1 and param2 (space separated)",
        "params": ["param1", "param2"],
        "types": [str, int],
        "operation": "new_operation",
        "result": ...  # Calculate result here
    }

Note:
-----
-   Use parameters starting with an underscore (_), if they are not to be sent to the frontend.
-   The 'operation' key in the returned dictionary must match the method name.
"""
import logging
import networkx as nx
import uuid
import inspect
import sys
import os
import pickle
import base64
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from ResearchGuidePackage.BackendModule.graph_manager import GraphManager
from ResearchGuidePackage.BackendModule.node_types import NodeTypeRegistry

logger = logging.getLogger('BackendOperations')

class ResearchService:
    def __init__(self):
        self.graph_manager = GraphManager()
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    
        self.db_registry_path = os.path.join(self.project_root, 'ResearchGuidePackage', 'BackendModule', 'resources', 'database_registry.json')

    async def list_operations(self, only_metadata: bool = False) -> dict:
        """List all available operations"""
        operations = {}
        for name, method in inspect.getmembers(self, predicate=inspect.iscoroutinefunction):
            if name.startswith("__") or name == "list_operations":
                continue
            try:
                metadata = await method(only_metadata=True)
                operations[name] = {
                    "name": metadata.get("name") or metadata.get("_name", "Unnamed Operation"),
                    "operation": metadata["operation"],
                    "input": metadata.get("input") or metadata.get("_input", ""),
                    "params": metadata.get("params") or metadata.get("_params", []),
                    "types": [t.__name__ if isinstance(t, type) else str(t) for t in metadata.get("types") or metadata.get("_types", [])]
                }
            except Exception as e:
                logger.error(f"Error getting metadata for {name}: {e}")
                continue
        return {
            "name": "List Available Operations",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "list_operations",
            "result": operations
        }

    async def checksum(self, number: int = None, only_metadata: bool = False) -> dict:
        """Calculate checksum"""
        metadata = {
            "_name": "Calculate Checksum",
            "_input": "Enter a number",
            "_params": ["number"],
            "_types": ["int"],
            "operation": "checksum"
        }
        if only_metadata:
            return metadata
        return {"result": sum(int(digit) for digit in str(number)) if number is not None else None}
    
    async def multiply(self, a: float = None, b: float = None, only_metadata: bool = False) -> dict:
        """Multiply two numbers"""
        metadata = {
            "name": "Multiply Numbers",
            "input": "Enter two numbers (space separated)",
            "params": ["a", "b"],
            "types": ["float", "float"],
            "operation": "multiply"
        }
        if only_metadata:
            return metadata
        return {"result": a * b if (a is not None and b is not None) else None}
    
    async def concatenate(self, str1: str = None, str2: str = None, only_metadata: bool = False) -> dict:
        """Concatenate two strings"""
        metadata = {
            "name": "Concatenate Strings",
            "input": "Enter two words (space separated)",
            "params": ["str1", "str2"],
            "types": ["str", "str"],
            "operation": "concatenate"
        }
        if only_metadata:
            return metadata
        return {"result": f"{str1} {str2}" if (str1 is not None and str2 is not None) else None}
    
    async def power(self, base: float = None, exponent: float = None, only_metadata: bool = False) -> dict:
        """Calculate power of a number"""
        metadata = {
            "name": "Calculate Power",
            "input": "Enter base and exponent (space separated)",
            "params": ["base", "exponent"],
            "types": ["float", "float"],  # Changed from [float, float] to ["float", "float"]
            "operation": "power"
        }
        if only_metadata:
            return metadata
        return {"result": base ** exponent if (base is not None and exponent is not None) else None}

    async def create_node(self, name: str = None, color: str = None, size: int = None, 
                    node_type: str = None, update_page: bool = True, only_metadata: bool = False, **kwargs) -> dict:
        """Create a new node using a specific node type"""
        metadata = {
            "name": "Create new node",
            "input": "Enter node name and type",
            "params": ["name", "node_type", "update_page"],  # Simplified required params
            "types": ["str", "str", "bool"],
            "operation": "create_node"
        }
        if only_metadata:
            return metadata

        try:
            if name is not None:
                # Get node type registry
                registry = NodeTypeRegistry()
                
                # Use default if node_type not provided
                node_type_id = node_type or "document"
                
                # Get node type definition
                type_def = registry.get_type(node_type_id)
                if not type_def:
                    logger.warning(f"Unknown node type: {node_type_id}, using default")
                    type_def = registry.get_type("document")  # Fallback to document type
                    node_type_id = "document"
                
                # Use type definition properties as defaults if not provided
                node_color = color if color is not None else type_def.color
                node_size = size if size is not None else type_def.default_size
                
                # Create the node with the selected type
                node_id = self.graph_manager.create_node(
                    name=name,
                    color=node_color,
                    size=node_size,
                    node_type=node_type_id
                )
                
                # Apply default parameter values from the node type
                for param in type_def.parameters:
                    param_name = param.name
                    # Don't override name, color, size which we've already set
                    if param_name not in ['name', 'color', 'size']:
                        # Use value from kwargs if provided, otherwise use the default
                        if param_name in kwargs:
                            value = kwargs[param_name]
                        else:
                            value = param.default_value
                            
                        # Only set if we actually have a value
                        if value is not None:
                            self.graph_manager.graph.nodes[node_id][param_name] = value
                
                # Apply any additional attributes from kwargs
                for key, value in kwargs.items():
                    if key not in ['name', 'color', 'size', 'node_type', 'update_page']:
                        self.graph_manager.graph.nodes[node_id][key] = value
                
                # Mark as modified
                self.graph_manager.set_modified(True)
                
                return {
                    **metadata,
                    "result": {
                        "node_id": str(node_id),
                        "label": self.graph_manager.get_node_label(node_id),
                        "name": name,
                        "color": node_color,
                        "size": node_size,
                        "node_type": node_type_id
                    },
                    "update_page": update_page
                }
            return {**metadata, "result": None}
        except Exception as e:
            logger.exception(f"Error creating node: {e}")
            return {**metadata, "result": None, "error": str(e)}

    async def delete_node(self, node_id: str = None, update_page: bool = True, only_metadata: bool = False) -> dict:
        """Delete a node by its ID"""
        metadata = {
            "name": "Delete node",
            "input": "Enter node ID to delete",
            "params": ["node_id", "update_page"],
            "types": ["str", "bool"],
            "operation": "delete_node"
        }
        if only_metadata:
            return metadata
        if node_id is not None:
            self.graph_manager.delete_node(uuid.UUID(node_id))
            return {
                "result": True,
                "update_page": update_page
            }
        return {"result": None}

    async def add_edge(self, source_id: str = None, target_id: str = None, weight: float = 1.0, edge_type: str = "default", update_page: bool = True, only_metadata: bool = False) -> dict:
        """Add an edge between two nodes"""
        metadata = {
            "name": "Add edge",
            "input": "Enter source_id target_id weight (space separated)",
            "params": ["source_id", "target_id", "weight", "update_page"],
            "types": ["str", "str", "float", "bool"],
            "operation": "add_edge"
        }
        if only_metadata:
            return metadata
        if source_id is not None and target_id is not None:
            self.graph_manager.add_edge(uuid.UUID(source_id), uuid.UUID(target_id), weight, edge_type)
            return {
                "result": True,
                "update_page": update_page
            }
        return {"result": None}

    async def delete_edge(self, source_id: str = None, target_id: str = None, update_page: bool = True, only_metadata: bool = False) -> dict:
        """Delete an edge between two nodes"""
        metadata = {
            "name": "Delete edge",
            "input": "Enter source_id target_id",
            "params": ["source_id", "target_id", "update_page"],
            "types": ["str", "str", "bool"],
            "operation": "delete_edge"
        }
        if only_metadata:
            return metadata
        if source_id is not None and target_id is not None:
            self.graph_manager.delete_edge(uuid.UUID(source_id), uuid.UUID(target_id))
            return {
                "result": True,
                "update_page": update_page
            }
        return {"result": None}

    async def get_nodes(self, only_metadata: bool = False) -> dict:
        """Get all nodes in the graph"""
        metadata = {
            "name": "Get all nodes",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "get_nodes"
        }
        if only_metadata:
            return metadata

        nodes = self.graph_manager.get_nodes()
        return {**metadata,
            "result": {
                "nodes": [
                    {
                        "id": str(node),
                        "label": self.graph_manager.get_node_label(node),
                        **self.graph_manager.get_node_by_uuid(node)
                    }
                    for node in nodes
                ]
            }
        }

    async def save_graph(self, file_path: str = None, only_metadata: bool = False) -> dict:
        """Save the current graph"""
        metadata = {
            "name": "Save graph",
            "input": "Enter file path (or press Enter for last used path)",
            "params": ["file_path"],
            "types": ["str"],
            "operation": "save_graph"
        }
        if only_metadata:
            return metadata
        if file_path is not None:
            self.graph_manager.save_graph(file_path)
            return {"result": True}
        return {"result": None}

    async def load_graph(self, file_path: str = None, only_metadata: bool = False) -> dict:
        """Load a graph from file"""
        metadata =  {
            "name": "Load graph",
            "input": "Enter file path to load",
            "params": ["file_path"],
            "types": ["str"],
            "operation": "load_graph"
        }
        if only_metadata:
            return metadata
        if file_path is not None:
            try:
                # Load the graph
                self.graph_manager.load_graph(file_path)
                
                # Mark this file as last opened in registry
                await self._mark_last_opened_database(file_path)
                
                # Serialize the loaded graph
                pickled_graph = base64.b64encode(pickle.dumps(self.graph_manager.graph)).decode('utf-8')
                return {
                    "result": True,
                    "update_page": True,
                    "graph_data": pickled_graph
                }
            except Exception as e:
                logger.error(f"Error loading graph: {e}")
                return {"result": False, "error": f"Error loading graph: {str(e)}"}
        return {"result": None}

    async def _mark_last_opened_database(self, file_path: str) -> None:
        """Mark a database as the last opened in the registry"""
        try:
            # Ensure the file exists
            if not os.path.exists(file_path):
                logger.warning(f"Cannot mark non-existent file as last opened: {file_path}")
                return
                
            # Load registry
            if os.path.exists(self.db_registry_path):
                with open(self.db_registry_path, 'r') as f:
                    registry = json.load(f)
            else:
                registry = {"databases": []}
                
            # Add file to registry if not already there
            databases = registry.get("databases", [])
            if file_path in databases:
                # Move to front of list
                databases.remove(file_path)
            databases.insert(0, file_path)
            
            # Add last_opened field
            registry["databases"] = databases
            registry["last_opened"] = file_path
            
            # Save registry
            with open(self.db_registry_path, 'w') as f:
                json.dump(registry, f, indent=2)
                
            logger.info(f"Marked database as last opened: {file_path}")
        except Exception as e:
            logger.error(f"Error marking database as last opened: {e}")

    async def get_last_saved_file_path(self, only_metadata: bool = False) -> dict:
        """Get the last saved file path from registry"""
        metadata = {
            "name": "Get Last Saved File Path",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "get_last_saved_file_path"
        }
        if only_metadata:
            return metadata
        
        try:
            file_path = None
            
            # Try to get path from registry first
            if os.path.exists(self.db_registry_path):
                with open(self.db_registry_path, 'r') as f:
                    registry = json.load(f)
                
                # First check for specifically marked last_opened
                if "last_opened" in registry and registry["last_opened"]:
                    last_opened = registry["last_opened"]
                    if os.path.exists(last_opened):
                        file_path = last_opened
                        logger.info(f"Using last_opened database from registry: {file_path}")
            
            # If no valid path from registry last_opened field, check graph manager
            if not file_path:            
                file_path = self.graph_manager.get_last_saved_file()
                if file_path and os.path.exists(file_path):
                    logger.info(f"Using last saved file path from graph manager: {file_path}")
            
            # If still no valid path, try first database in registry list
            if not file_path or not os.path.exists(file_path):
                if os.path.exists(self.db_registry_path):
                    with open(self.db_registry_path, 'r') as f:
                        registry = json.load(f)
                    
                    # Find first existing database in registry
                    for db_path in registry.get("databases", []):
                        if db_path and os.path.exists(db_path):
                            file_path = db_path
                            logger.info(f"Using first available database from registry: {file_path}")
                            break
            
            # Explicitly log what we're returning to help with debugging
            if file_path:
                logger.info(f"Returning file path: {file_path}")
            else:
                logger.warning("No valid file path found to return")
                
            return {
                "result": True,
                "file_path": file_path
            }
        except Exception as e:
            logger.error(f"Error getting last saved file path: {e}")
            return {
                "result": False,
                "error": str(e),
                "file_path": None  # Always include file_path even on error
            }

    async def set_last_saved_file_path(self, file_path: str = None, only_metadata: bool = False) -> dict:
        """Set the last saved file path and update registry"""
        metadata = {
            "name": "Set Last Saved File Path",
            "input": "Enter file path",
            "params": ["file_path"],
            "types": ["str"],
            "operation": "set_last_saved_file_path"
        }
        if only_metadata:
            return metadata
        
        try:    
            if file_path is not None:
                # Update in graph manager
                self.graph_manager.set_last_saved_file_log(file_path)
                
                # Also update in database registry (move to front of list)
                await self._mark_last_opened_database(file_path)
                
                return {"result": True}
            return {"result": False, "error": "No file path provided"}
        except Exception as e:
            logger.error(f"Error setting last saved file path: {e}")
            return {"result": False, "error": str(e)}

    async def load_last_graph(self, only_metadata: bool = False) -> dict:
        """Load the last saved graph from registry"""
        metadata = {
            "name": "Load last graph",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "load_last_graph"
        }
        if only_metadata:
            return metadata
        
        try:
            # Try to get the path to the last opened database from registry
            file_path = None
            
            if os.path.exists(self.db_registry_path):
                try:
                    with open(self.db_registry_path, 'r') as f:
                        registry = json.load(f)
                    
                    # First check if we have a specifically marked last_opened database
                    if "last_opened" in registry and registry["last_opened"]:
                        last_opened = registry["last_opened"]
                        if os.path.exists(last_opened):
                            file_path = last_opened
                            logger.info(f"Loading last opened database from registry: {file_path}")
                        else:
                            logger.warning(f"Last opened database no longer exists: {last_opened}")
                    
                    # If no valid last_opened, use first database in list
                    if not file_path:
                        for db_path in registry.get("databases", []):
                            if os.path.exists(db_path):
                                file_path = db_path
                                logger.info(f"Loading first available database from registry: {file_path}")
                                break
                except Exception as e:
                    logger.error(f"Error reading registry file: {e}")
            
            # If we still don't have a valid file, check graph manager path
            if not file_path:
                file_path = self.graph_manager.get_last_saved_file()
                if file_path and os.path.exists(file_path):
                    logger.info(f"Loading last saved file from graph manager: {file_path}")
            
            if not file_path or not os.path.exists(file_path):
                logger.warning("No valid database found to load")
                return {**metadata, "result": False, "error": "No valid database found to load"}
            
            # Load the database        
            logger.info(f"Loading graph from file: {file_path}")
            self.graph_manager.load_graph(file_path)
            graph = self.graph_manager.get_graph()
            
            # Verify the loaded graph
            if graph and isinstance(graph, nx.Graph):
                node_count = len(graph.nodes)
                edge_count = len(graph.edges)
                logger.info(f"Loaded graph with {node_count} nodes and {edge_count} edges")
                
                # Mark this as last opened in registry
                await self._mark_last_opened_database(file_path)
                
                # Serialize the loaded graph
                pickled_graph = base64.b64encode(pickle.dumps(graph)).decode('utf-8')
                
                return {
                    **metadata,
                    "result": True,
                    "update_page": True,
                    "graph_data": pickled_graph,
                    "file_path": file_path,
                    "was_last_opened": True  # Indicate this was loaded from last opened
                }
            else:
                logger.warning(f"Loaded graph is not valid: {type(graph)}")
                return {**metadata, "result": False, "error": "Failed to load valid graph"}
                
        except Exception as e:
            logger.exception(f"Error in load_last_graph: {e}")
            return {**metadata, "result": False, "error": str(e)}

    async def load_graph_from_gml(self, file_path: str = None, only_metadata: bool = False) -> dict:
        """Load a graph from a GML file"""
        metadata = {
            "name": "Load GML Graph",
            "input": "Enter GML file path to load",
            "params": ["file_path"],
            "types": ["str"],
            "operation": "load_graph_from_gml"
        }
        if only_metadata:
            return metadata
            
        try:
            if file_path is not None:
                self.graph_manager.load_graph_from_gml(file_path)
                # Ensure UUIDs are converted back to UUID objects
                for node in self.graph_manager.graph.nodes(data=True):
                    if 'uuid' in node[1]:
                        node[1]['uuid'] = uuid.UUID(node[1]['uuid'])
                
                # Serialize the loaded graph
                pickled_graph = base64.b64encode(pickle.dumps(self.graph_manager.graph)).decode('utf-8')
                return {
                    "result": True,
                    "graph_data": pickled_graph
                }
            return {"result": None}
        except Exception as e:
            logger.error(f"Error loading GML file: {e}")
            return {"result": False, "error": str(e)}
            
    async def export_graph_to_gml(self, file_path: str = None, only_metadata: bool = False) -> dict:
        """Export the graph to a GML file"""
        metadata = {
            "name": "Export Graph to GML",
            "input": "Enter file path for export",
            "params": ["file_path"],
            "types": ["str"],
            "operation": "export_graph_to_gml"
        }
        if only_metadata:
            return metadata
            
        try:
            if file_path is not None:
                # Convert UUIDs to strings and ensure all node attributes are strings
                graph = self.graph_manager.get_graph()
                graph_copy = nx.relabel_nodes(graph, lambda x: str(x))
                for node in graph_copy.nodes:
                    for attr in graph_copy.nodes[node]:
                        graph_copy.nodes[node][attr] = str(graph_copy.nodes[node][attr])
                for edge in graph_copy.edges:
                    for attr in graph_copy.edges[edge]:
                        graph_copy.edges[edge][attr] = str(graph_copy.edges[edge][attr])
                nx.write_gml(graph_copy, file_path)
                return {"result": True, "file_path": file_path}
            return {"result": False, "error": "No file path provided"}
        except Exception as e:
            logger.error(f"Error exporting graph to GML: {e}")
            return {"result": False, "error": str(e)}
            
    async def import_markdown_folder(self, folder_path: str = None, db_file_path: str = None, only_metadata: bool = False) -> dict:
        """Import a markdown folder structure into a graph database"""
        metadata = {
            "name": "Import Markdown Folder",
            "input": "Enter folder path and database file path",
            "params": ["folder_path", "db_file_path"],
            "types": ["str", "str"],
            "operation": "import_markdown_folder"
        }
        if only_metadata:
            return metadata
            
        try:
            if folder_path is not None and db_file_path is not None:
                from ResearchGuidePackage.BackendModule.import_markdown_folder import import_markdown_folder_structure
                import_markdown_folder_structure(folder_path, db_file_path)
                return {"result": True, "db_file_path": db_file_path}
            return {"result": False, "error": "Missing required parameters"}
        except Exception as e:
            logger.error(f"Error importing markdown folder: {e}")
            return {"result": False, "error": str(e)}

    async def edit_node(self, node_id: str = None, name: str = None, color: str = None, size: int = None, 
                      attributes: dict = None, update_page: bool = True, only_metadata: bool = False) -> dict:
        """Edit a node's attributes"""
        metadata = {
            "name": "Edit Node",
            "input": "Enter node ID and attributes to update",
            "params": ["node_id", "name", "color", "size", "attributes", "update_page"],
            "types": ["str", "str", "str", "int", "dict", "bool"],
            "operation": "edit_node"
        }
        if only_metadata:
            return metadata
            
        try:
            if node_id is not None:
                node_uuid = uuid.UUID(node_id)
                # Verify node exists
                if node_uuid not in self.graph_manager.graph.nodes:
                    return {**metadata, "result": False, "error": f"Node {node_id} does not exist"}
                
                # Get the current node data for logging purposes
                current_node_data = dict(self.graph_manager.graph.nodes[node_uuid])
                logger.info(f"Before update, node {node_id} had attributes: {current_node_data}")
                
                # Create a dictionary of attributes to update
                updates = {}
                if name is not None and name.strip() != "":
                    updates['name'] = name
                if color is not None:
                    updates['color'] = color
                if size is not None:
                    updates['size'] = size
                
                # Add any additional attributes from the attributes dictionary
                if attributes is not None:
                    # Filter out empty string values as they likely mean "don't change"
                    for key, value in attributes.items():
                        if value != "" or isinstance(value, (bool, int, float, list, dict)):
                            # Normalize attribute names:
                            # 1. Remove trailing colons which come from form labels
                            normalized_key = key.rstrip(':')
                            # 2. Convert to lowercase (title -> title, Title: -> title)
                            normalized_key = normalized_key.lower()
                            updates[normalized_key] = value
                
                logger.info(f"Updating node {node_id} with attributes: {updates}")
                
                # Apply all updates to the node
                for key, value in updates.items():
                    self.graph_manager.graph.nodes[node_uuid][key] = value
                
                # Log the node data after update for debugging
                updated_node_data = dict(self.graph_manager.graph.nodes[node_uuid])
                logger.info(f"After update, node {node_id} has attributes: {updated_node_data}")
                
                # Mark as modified
                self.graph_manager.set_modified(True)
                
                # Serialize the updated graph to return to the frontend
                pickled_graph = base64.b64encode(pickle.dumps(self.graph_manager.graph)).decode('utf-8')
                
                return {
                    **metadata,
                    "result": True,
                    "update_page": update_page,
                    "graph_data": pickled_graph
                }
            return {**metadata, "result": False, "error": "Missing node_id"}
        except Exception as e:
            logger.error(f"Error editing node: {e}", exc_info=True)
            return {**metadata, "result": False, "error": str(e)}

    async def get_node_file(self, node_id: str = None, check_only: bool = False, only_metadata: bool = False) -> dict:
        """Get file content for a node from the database"""
        metadata = {
            "name": "Get Node File",
            "input": "Enter node ID",
            "params": ["node_id"],
            "types": ["str"],
            "operation": "get_node_file"
        }
        if only_metadata:
            return metadata
            
        try:
            # Log the operation
            logger.info(f"Getting file for node: {node_id}")
            
            if node_id is not None:
                # Convert string to UUID
                node_uuid = uuid.UUID(node_id)
                
                # Check if node exists
                if node_uuid not in self.graph_manager.graph.nodes:
                    logger.error(f"Node {node_id} not found in graph")
                    return {"result": False, "error": f"Node {node_id} does not exist"}
                    
                # Get node data
                node_data = self.graph_manager.graph.nodes[node_uuid]
                file_path = node_data.get('file_path')
                
                if not file_path:
                    logger.error(f"No file path for node {node_id}")
                    return {"result": False, "error": "No file associated with this node"}
                    
                # First get the actual table schema to determine column names
                self.graph_manager.graph_file_manager.db_handler.connect()
                cursor = self.graph_manager.graph_file_manager.db_handler.cursor
                
                # Get table info to find the correct column name
                try:
                    cursor.execute("PRAGMA table_info(nodes)")
                    columns = cursor.fetchall()
                    column_names = [column[1] for column in columns]
                    logger.info(f"Available columns in nodes table: {column_names}")
                    
                    # Find content column - could be 'file_content', 'content', 'data', etc.
                    content_column = None
                    for possible_name in ['file_content', 'content', 'data', 'blob_data', 'file_data']:
                        if possible_name in column_names:
                            content_column = possible_name
                            break
                    
                    if not content_column:
                        # Fall back to reading from filesystem
                        logger.warning("No content column found in nodes table, falling back to filesystem")
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                    else:
                        # Query using the correct column name
                        cursor.execute(f"SELECT {content_column} FROM nodes WHERE node_id=?", (str(node_uuid),))
                        result = cursor.fetchone()
                        
                        if result and result[0]:
                            file_content = result[0]
                            logger.info(f"Retrieved file content from database: {len(file_content)} bytes")
                        else:
                            # Fall back to filesystem
                            logger.warning(f"No content found in database, falling back to filesystem")
                            with open(file_path, 'rb') as f:
                                file_content = f.read()
                                
                except Exception as db_error:
                    logger.error(f"Database error: {db_error}")
                    # Fall back to filesystem
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                finally:
                    self.graph_manager.graph_file_manager.db_handler.close()
                    
                if file_content:
                    # Encode as base64 for transmission
                    file_content_b64 = base64.b64encode(file_content).decode('utf-8')
                    
                    return {
                        "result": True,
                        "file_content": file_content_b64,
                        "file_name": os.path.basename(file_path),
                        "size": len(file_content),
                        "encoding": "base64"
                    }
                else:
                    logger.error(f"No file content found for node {node_id}")
                    return {"result": False, "error": f"No file content found for node {node_id} with path {file_path}"}
                        
            else:
                return {"result": False, "error": "Missing node_id parameter"}
        except Exception as e:
            logger.exception(f"Error in get_node_file: {e}")
            return {"result": False, "error": str(e)}

    async def upload_node_file(self, node_id: str = None, file_path: str = None, only_metadata: bool = False) -> dict:
        """Upload a file and associate it with a node"""
        metadata = {
            "name": "Upload Node File",
            "input": "Enter node ID and file path",
            "params": ["node_id", "file_path"],
            "types": ["str", "str"],
            "operation": "upload_node_file"
        }
        if only_metadata:
            return metadata
            
        try:
            if not node_id or not file_path:
                return {**metadata, "result": False, "error": "Missing required parameters"}
            
            # Convert string ID to UUID
            node_uuid = uuid.UUID(node_id)
            
            # Check if node exists
            if node_uuid not in self.graph_manager.graph.nodes:
                return {**metadata, "result": False, "error": f"Node {node_id} does not exist"}
                
            # Verify file exists
            if not os.path.exists(file_path):
                return {**metadata, "result": False, "error": f"File {file_path} does not exist"}
            
            # Read file content
            try:
                with open(file_path, 'rb') as file:
                    file_content = file.read()
            except Exception as e:
                logger.error(f"Error reading file: {e}")
                return {**metadata, "result": False, "error": f"Error reading file: {e}"}
                
            # Get file type from extension
            _, file_ext = os.path.splitext(file_path)
            file_type = file_ext[1:] if file_ext else "unknown"
            
            # Store file in the database and update node
            try:
                # Update node attributes
                self.graph_manager.graph.nodes[node_uuid]['file_path'] = file_path
                self.graph_manager.graph.nodes[node_uuid]['file_type'] = file_type
                
                # Store file content - FIXED: directly call with correct number of arguments
                table_name = "node_files"
                self.graph_manager.insert_node_data(table_name, str(node_uuid), file_path, file_content)
                
                # Mark graph as modified
                self.graph_manager.set_modified(True)
                
                # Serialize updated graph for response
                pickled_graph = base64.b64encode(pickle.dumps(self.graph_manager.graph)).decode('utf-8')
                
                return {
                    **metadata,
                    "result": True,
                    "graph_data": pickled_graph
                }
                
            except Exception as e:
                logger.error(f"Error storing file: {e}")
                return {**metadata, "result": False, "error": f"Error storing file: {e}"}
                
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {**metadata, "result": False, "error": str(e)}

    async def get_node_types(self, only_metadata: bool = False) -> dict:
        """Get all available node types"""
        metadata = {
            "name": "Get Node Types",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "get_node_types"
        }
        if only_metadata:
            return metadata
        
        try:
            # Limit execution time for safety
            registry = NodeTypeRegistry()
            types_dict = registry.get_all_types_as_dict()
            
            return {
                **metadata,
                "result": types_dict
            }
        except Exception as e:
            logger.error(f"Error getting node types: {e}")
            # Return empty result rather than failing
            return {
                **metadata,
                "result": {"document": {"name": "Document", "color": "skyblue"}}
            }

    async def get_node_type_parameters(self, type_id: str = None, only_metadata: bool = False) -> dict:
        """Get parameters for a specific node type"""
        metadata = {
            "name": "Get Node Type Parameters",
            "input": "Enter node type ID",
            "params": ["type_id"],
            "types": ["str"],
            "operation": "get_node_type_parameters"
        }
        if only_metadata:
            return metadata
            
        if not type_id:
            return {**metadata, "result": None, "error": "No type ID provided"}
            
        registry = NodeTypeRegistry()
        node_type = registry.get_type(type_id)
        
        if not node_type:
            return {**metadata, "result": None, "error": f"Node type '{type_id}' not found"}
            
        return {
            **metadata,
            "result": {
                "id": node_type.id,
                "name": node_type.name,
                "parameters": [p.to_dict() for p in node_type.parameters],
                "color": node_type.color
            }
        }

    async def check_file_exists(self, node_id: str = None, only_metadata: bool = False) -> dict:
        """Check if a file exists for a node in the database"""
        metadata = {
            "name": "Check File Exists",
            "input": "Enter node ID",
            "params": ["node_id"],
            "types": ["str"],
            "operation": "check_file_exists"
        }
        if only_metadata:
            return metadata
            
        try:
            if node_id is None:
                return {**metadata, "result": False, "error": "Missing node_id"}
                
            # Convert string to UUID
            node_uuid = uuid.UUID(node_id)
            
            # Check if node exists
            if node_uuid not in self.graph_manager.graph.nodes:
                return {**metadata, "result": False, "error": "Node does not exist"}
                
            # Get node data
            node_data = self.graph_manager.graph.nodes[node_uuid]
            file_path = node_data.get('file_path')
            
            if not file_path:
                return {**metadata, "file_exists": False}
                
            # Only check if the file exists in the database
            table_name = "node_files"
            file_exists = self.graph_manager.check_file_exists(table_name, str(node_uuid))
            
            return {
                **metadata,
                "file_exists": file_exists,
                "file_path": file_path
            }
            
        except Exception as e:
            logger.error(f"Error in check_file_exists: {e}")
            return {**metadata, "file_exists": False, "error": str(e)}

    async def get_node(self, node_id: str = None, only_metadata: bool = False) -> dict:
        """Get detailed information about a specific node including connected edges"""
        metadata = {
            "name": "Get node details",
            "input": "Enter node ID",
            "params": ["node_id"],
            "types": ["str"],
            "operation": "get_node"
        }
        if only_metadata:
            return metadata

        try:
            if node_id is None:
                return {**metadata, "result": None, "error": "Missing node_id parameter"}
            
            # Convert string ID to UUID
            node_uuid = uuid.UUID(node_id)
            
            # Check if node exists
            if node_uuid not in self.graph_manager.graph.nodes:
                return {**metadata, "result": None, "error": f"Node {node_id} does not exist"}
            
            # Get node data
            node_data = dict(self.graph_manager.graph.nodes[node_uuid])
            
            # Initialize edge lists
            incoming_edges = []
            outgoing_edges = []
            
            # Get all edges connected to this node
            for u, v, edge_data in self.graph_manager.graph.edges(data=True):
                edge_dict = dict(edge_data)  # Convert edge data to dict
                
                if u == node_uuid:
                    # This is an outgoing edge
                    target_label = self.graph_manager.get_node_label(v)
                    outgoing_edges.append({
                        "target_id": str(v),
                        "target_label": target_label,
                        "edge_data": edge_dict
                    })
                
                if v == node_uuid:
                    # This is an incoming edge
                    source_label = self.graph_manager.get_node_label(u)
                    incoming_edges.append({
                        "source_id": str(u),
                        "source_label": source_label,
                        "edge_data": edge_dict
                    })
            logger.info(f"Node {node_id} has {len(incoming_edges)} incoming edges and {len(outgoing_edges)} outgoing edges")
            # Construct the result
            result = {
                "id": str(node_uuid),
                "label": self.graph_manager.get_node_label(node_uuid),
                **node_data,  # Include node attributes directly
                "incoming_edges": incoming_edges,
                "outgoing_edges": outgoing_edges
            }
            
            return {**metadata, "result": result}
        
        except Exception as e:
            logger.exception(f"Error in get_node: {e}")
            return {**metadata, "result": None, "error": str(e)}

    async def list_available_databases(self, only_metadata: bool = False) -> dict:
        """Get all available database files"""
        metadata = {
            "name": "List Available Databases",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "list_available_databases"
        }
        if only_metadata:
            return metadata
        
        try:
            # Load existing databases or create empty list
            if os.path.exists(self.db_registry_path):
                with open(self.db_registry_path, 'r') as f:
                    registry = json.load(f)
            else:
                registry = {"databases": []}
                
            # Filter out non-existent files
            existing_dbs = []
            for db_path in registry.get("databases", []):
                if isinstance(db_path, str) and os.path.exists(db_path):
                    existing_dbs.append(db_path)
            
            # Add current file if exists and not in list
            current_path = self.graph_manager.get_last_saved_file()
            if current_path and os.path.exists(current_path) and current_path not in existing_dbs:
                existing_dbs.insert(0, current_path)
                
            # Update registry with cleaned list
            registry["databases"] = existing_dbs
            
            # Save the updated registry
            with open(self.db_registry_path, 'w') as f:
                json.dump(registry, f, indent=2)
                
            return {
                "result": True,
                "databases": existing_dbs
            }
            
        except Exception as e:
            logger.error(f"Error listing available databases: {e}", exc_info=True)
            return {
                "result": False,
                "error": str(e)
            }

    async def add_database_to_list(self, file_path: str = None, only_metadata: bool = False) -> dict:
        """Add database to available databases list"""
        metadata = {
            "name": "Add Database to List",
            "input": "Enter database file path",
            "params": ["file_path"],
            "types": ["str"],
            "operation": "add_database_to_list"
        }
        if only_metadata:
            return metadata
            
        try:
            if not file_path:
                return {"result": False, "error": "No file path provided"}
                
            if not os.path.exists(file_path):
                return {"result": False, "error": f"File does not exist: {file_path}"}
            
            
            
            if os.path.exists(self.db_registry_path):
                with open(self.db_registry_path, 'r') as f:
                    registry = json.load(f)
            else:
                registry = {"databases": []}
                
            databases = registry.get("databases", [])
            
            if file_path in databases:
                databases.remove(file_path)
            databases.insert(0, file_path)
            registry["databases"] = databases
            
            with open(self.db_registry_path, 'w') as f:
                json.dump(registry, f, indent=2)
                
            return {
                "result": True,
                "file_path": file_path
            }
            
        except Exception as e:
            logger.error(f"Error adding database to list: {e}", exc_info=True)
            return {
                "result": False,
                "error": str(e)
            }
    
    async def remove_database_from_list(self, file_path: str = None, only_metadata: bool = False) -> dict:
        """Remove database from available databases list"""
        metadata = {
            "name": "Remove Database from List",
            "input": "Enter database file path to remove",
            "params": ["file_path"],
            "types": ["str"],
            "operation": "remove_database_from_list"
        }
        if only_metadata:
            return metadata
            
        try:
            if not file_path:
                return {"result": False, "error": "No file path provided"}

            with open(self.db_registry_path, 'r') as f:
                registry = json.load(f)
                
            databases = registry.get("databases", [])
            
            if file_path in databases:
                databases.remove(file_path)
                registry["databases"] = databases
                with open(self.db_registry_path, 'w') as f:
                    json.dump(registry, f, indent=2)
                return {
                    "result": True,
                    "file_path": file_path
                }
            else:
                return {
                    "result": False,
                    "error": f"File path not found in registry: {file_path}"
                }
            
        except Exception as e:
            logger.error(f"Error removing database from list: {e}", exc_info=True)
            return {
                "result": False,
                "error": str(e)
            }

    async def get_available_operations(self, only_metadata: bool = False) -> dict:
        """List all available operations in the system"""
        metadata = {
            "name": "Get Available Operations",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "get_available_operations"
        }
        if only_metadata:
            return metadata
            
        # Collect all available operations
        operations = {}
        for name, method in inspect.getmembers(self, predicate=inspect.iscoroutinefunction):
            if name.startswith("_") or name == "get_available_operations":
                continue
                
            operations[name] = name
            
        return {
            "result": operations
        }

    async def get_graph_modified_status(self, only_metadata: bool = False) -> dict:
        """Check if graph has unsaved changes"""
        metadata = {
            "name": "Check Graph Modified Status",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "get_graph_modified_status"
        }
        if only_metadata:
            return metadata
        return {
            "result": self.graph_manager.check_if_modified()
        }
        
    async def get_graph(self, only_metadata: bool = False) -> dict:
        """Get the current graph"""
        metadata = {
            "name": "Get current graph",
            "input": "Press Enter to continue",
            "params": [],
            "types": [],
            "operation": "get_graph"
        }
        if only_metadata:
            return metadata

        try:
            # Get the graph from the graph manager
            graph = self.graph_manager.get_graph()
            
            # Serialize the graph as pickled data encoded in base64
            pickled_graph = base64.b64encode(pickle.dumps(graph)).decode('utf-8')
            
            # Return the result
            return {
                **metadata,
                "result": True,
                "graph_data": pickled_graph,
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges)
            }
        except Exception as e:
            logger.error(f"Error getting graph: {e}", exc_info=True)
            return {
                **metadata, 
                "result": False, 
                "error": f"Error retrieving graph: {str(e)}"
            }