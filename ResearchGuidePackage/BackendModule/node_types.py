from typing import Dict, List, Any, Optional, Union
import logging
import json
import os
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Path to node types configuration file
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    
DEFAULT_CONFIG_PATH = os.path.join(project_root, 'ResearchGuidePackage', 'BackendModule', 'resources', 'node_types.json')

@dataclass
class ParameterDefinition:
    """Definition of a parameter for a node type."""
    name: str
    type: str  # 'string', 'int', 'float', 'bool', 'date', 'file', 'color', etc.
    display_name: str = None
    description: str = ""
    default_value: Any = None
    required: bool = False
    options: List[str] = field(default_factory=list)  # For parameters with fixed options
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    ui_element: str = "text"  # Default UI element for this parameter
    
    def __post_init__(self):
        if self.display_name is None:
            self.display_name = self.name.replace('_', ' ').title()
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ParameterDefinition':
        """Create from dictionary representation."""
        return cls(**data)

@dataclass
class NodeTypeDefinition:
    """Definition of a node type."""
    id: str  # Unique identifier for this node type
    name: str  # Display name
    description: str = ""
    icon: str = ""  # Path or identifier for an icon
    color: str = "skyblue"  # Default color for this node type
    parameters: List[ParameterDefinition] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "parameters": [p.to_dict() for p in self.parameters]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NodeTypeDefinition':
        """Create from dictionary representation."""
        params_data = data.pop("parameters", [])
        node_type = cls(**data)
        node_type.parameters = [ParameterDefinition.from_dict(p) for p in params_data]
        return node_type


class NodeTypeRegistry:
    """Registry for node types."""
    _instance = None
    
    def __new__(cls, config_path=None):
        if cls._instance is None:
            cls._instance = super(NodeTypeRegistry, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self, config_path=None):
        if self.initialized:
            return
            
        self.node_types: Dict[str, NodeTypeDefinition] = {}
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.load_from_config()
        self.initialized = True
    
    def load_from_config(self):
        """Load node types from configuration file."""
        try:
            if os.path.exists(self.config_path):
                logger.info(f"Loading node types from config: {self.config_path}")
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Clear existing node types
                self.node_types = {}
                
                # Register node types from config
                for type_id, type_data in config_data.items():
                    params = []
                    for param_data in type_data.get('parameters', []):
                        params.append(ParameterDefinition(**param_data))
                    
                    node_type = NodeTypeDefinition(
                        id=type_id,
                        name=type_data.get('name', type_id),
                        description=type_data.get('description', ''),
                        icon=type_data.get('icon', ''),
                        color=type_data.get('color', 'skyblue'),
                        parameters=params
                    )
                    
                    self.register_type(node_type)
                
                logger.info(f"Loaded {len(self.node_types)} node types from config")
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                self._initialize_default_types()
        except Exception as e:
            logger.error(f"Error loading node types from config: {e}")
            self._initialize_default_types()
    
    def _initialize_default_types(self):
        """Initialize with default types if config file is not available."""
        logger.info("Using default node types")
        # Basic Document node
        document = NodeTypeDefinition(
            id="document", 
            name="Document",
            description="A document node representing a file",
            color="lightblue",
            parameters=[
                ParameterDefinition(name="name", type="string", required=True),
                ParameterDefinition(name="content", type="text", required=False),
                ParameterDefinition(name="file_path", type="file", required=False),
                ParameterDefinition(name="tags", type="string", required=False),
                ParameterDefinition(name="date_created", type="date", required=False)
            ]
        )
        
        # Person node
        person = NodeTypeDefinition(
            id="person",
            name="Person",
            description="A node representing a person",
            color="lightgreen",
            parameters=[
                ParameterDefinition(name="name", type="string", required=True),
                ParameterDefinition(name="role", type="string", required=False),
                ParameterDefinition(name="email", type="string", required=False),
                ParameterDefinition(name="organization", type="string", required=False)
            ]
        )
        
        # Concept node
        concept = NodeTypeDefinition(
            id="concept",
            name="Concept",
            description="A node representing a concept or idea",
            color="lightyellow",
            parameters=[
                ParameterDefinition(name="name", type="string", required=True),
                ParameterDefinition(name="description", type="text", required=False),
                ParameterDefinition(name="category", type="string", required=False)
            ]
        )
        
        # Task node
        task = NodeTypeDefinition(
            id="task",
            name="Task",
            description="A task or todo item",
            color="salmon",
            parameters=[
                ParameterDefinition(name="name", type="string", required=True),
                ParameterDefinition(name="status", type="string", required=False, 
                                   options=["Not Started", "In Progress", "Completed"]),
                ParameterDefinition(name="due_date", type="date", required=False),
                ParameterDefinition(name="priority", type="int", required=False, min_value=1, max_value=5)
            ]
        )
        
        # Add the default types to the registry
        for node_type in [document, person, concept, task]:
            self.register_type(node_type)
    
    def register_type(self, node_type: NodeTypeDefinition):
        """Register a new node type."""
        self.node_types[node_type.id] = node_type
        logger.info(f"Registered node type: {node_type.name} ({node_type.id})")
    
    def get_type(self, type_id: str) -> Optional[NodeTypeDefinition]:
        """Get a node type by its ID."""
        return self.node_types.get(type_id)
    
    def get_all_types(self) -> List[NodeTypeDefinition]:
        """Get all registered node types."""
        return list(self.node_types.values())
    
    def get_all_types_as_dict(self) -> dict:
        """Get all registered node types as a dictionary."""
        return {
            node_type.id: node_type.to_dict() 
            for node_type in self.node_types.values()
        }
    
    def to_dict(self) -> dict:
        """Convert registry to dictionary for serialization."""
        return {tid: nt.to_dict() for tid, nt in self.node_types.items()}
    
    def save_to_file(self, file_path: str = None):
        """Save the registry to a JSON file."""
        save_path = file_path or self.config_path
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info(f"Node type registry saved to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving node type registry: {e}")
            return False
