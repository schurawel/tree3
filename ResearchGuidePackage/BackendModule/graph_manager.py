import networkx as nx
import uuid
import logging
import os  # Import the os module
import io
import pickle
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QFileDialog # Import QFileDialog
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ResearchGuidePackage.BackendModule.graph_file_manager import GraphFileManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class GraphManager:
    def __init__(self):
        """Initialize GraphManager."""
        # self.graph_file_manager = GraphFileManager(db_path) # Do not initialize here
        self.graph = nx.DiGraph()  # Changed from nx.Graph() to nx.DiGraph()
        self.node_names = {}  # UUID -> User-friendly name
        self.next_node_id = 1  # Counter for generating user-friendly IDs
        self.log_file_path = os.path.expanduser(os.path.abspath(os.path.join(os.path.dirname(__file__),"resources", "available_databases.log")))  # Updated path
        self.last_saved_file = None
        self.modified = False

        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)

        self.graph_file_manager = GraphFileManager()

        logging.info("GraphManager initialized.")

    def get_db_path(self):
        """Returns the database path."""
        return self.graph_file_manager.db_handler.db_path

    def create_node(self, name, color, size, file_path=None, file_type=None, node_type="document", **kwargs):
        """
        Create a new node with a UUID and user-friendly name.
        
        Args:
            name: Display name for the node
            color: Color for visualization
            size: Size for visualization
            file_path: Optional path to file
            file_type: Optional file type
            node_type: Type of node (document, page, file, text_block, etc.)
            **kwargs: Additional parameters specific to the node type
        """
        if self.graph is None:
            self.create_new_graph()
            
        node_id = uuid.uuid4()
        user_friendly_name = str(self.next_node_id)  # Use a simple counter
        self.next_node_id += 1

        # Basic node attributes
        node_attrs = {
            'name': name,
            'color': color,
            'size': size,
            'label': user_friendly_name,
            'file_path': file_path,
            'file_type': file_type,
            'node_type': node_type
        }
        
        # Add all additional attributes from kwargs
        for key, value in kwargs.items():
            node_attrs[key] = value
            
        # Add the node with all attributes
        self.graph.add_node(node_id, **node_attrs)
        self.node_names[node_id] = user_friendly_name
        self.set_modified(True)

        logging.info(f"Node created: UUID={node_id}, Name={name}, Type={node_type}, Label={user_friendly_name}")
        return node_id

    def add_edge(self, node1_uuid, node2_uuid, weight, edge_type):
        """Add a new edge between two nodes (UUIDs)."""
        self.graph.add_edge(node1_uuid, node2_uuid, weight=weight, type=edge_type)
        self.set_modified(True)
        logging.info(f"Edge added: Node1={node1_uuid}, Node2={node2_uuid}, Weight={weight}, Type={edge_type}")

    def get_node_name(self, node_uuid):
        """Get the user-friendly name for a node UUID."""
        return self.node_names.get(node_uuid, str(node_uuid))  # Return UUID if name not found

    def load_graph_on_startup(self):
        self.try_loading_last_opened_graph()
        if self.graph is not None:  # Check if load_last_opened_graph loaded the graph
            logging.info("Last opened graph loaded.")
        else:
            self.create_new_graph()
            logging.info("Created a new empty graph.")

    def load_graph(self, file_path):
        """Loads the graph from the database using GraphFileManager."""
        try:
            if file_path is not None:
                self.graph_file_manager.set_path(file_path)
                self.graph_file_manager.initialize_database()
                loaded_graph = self.graph_file_manager.download_graph_from_database()
                if loaded_graph is not None:
                    self.graph = loaded_graph
                    self.set_last_saved_file_log(file_path)
                    logging.info(f"Graph loaded from database: {file_path}")
            else:
                self.create_new_graph()

        except Exception as e:
            logging.error(f"Error loading graph from database: {e}")
            raise

    def save_graph(self, file_path=None):
        """Saves the current graph to the database as a blob and logs the file path."""

        # If file_path is None, use the last saved file path
        if (file_path is None):
            file_path = self.get_last_saved_file()

        # Initialize the database
        if (file_path):
            self.graph_file_manager.set_path(file_path)
            self.graph_file_manager.initialize_database()
        else:
            raise ValueError("No file path specified and no last saved file found.")

        self.graph_file_manager.upload_graph_to_database(self.get_graph())

        self.set_modified(False)
        if (file_path):
            self.log_last_file_path(file_path)
            logging.info(f"Graph saved to: {file_path}")
            self.set_last_saved_file_log(file_path)
        else:
            logging.info("Graph saved to database as blob.")
        #except Exception as e:
         #   logging.error(f"Error saving graph to database: {e}")
          #  raise

    def get_nodes(self):
        """Get a list of node UUIDs."""
        return list(self.graph.nodes())

    def get_node_label(self, node):
        """Get the label of a node."""
        return self.graph.nodes[node].get('label', str(node))

    def delete_node(self, node_id):
        """Delete a node from the graph."""
        try:
            self.graph.remove_node(node_id)
            if node_id in self.node_names:
                del self.node_names[node_id]
            self.set_modified(True)

            # Delete node properties from the database
            self.delete_node_data("nodes", node_id)

            logging.info(f"Node deleted: {node_id}")
        except Exception as e:
            logging.error(f"Error deleting node: {e}")
            raise

    def delete_node_data(self, table_name, node_id):
        """Deletes node data from the database."""
        try:
            condition = f"node_id = '{node_id}'"
            self.graph_file_manager.db_handler.delete_data(table_name, condition)
            logging.debug(f"Data deleted for node: {node_id}")
        except Exception as e:
            logging.error(f"Error deleting node data: {e}")
            raise

    def delete_edge(self, node1_uuid, node2_uuid):
        """Delete an edge from the graph."""
        try:
            self.graph.remove_edge(node1_uuid, node2_uuid)
            self.set_modified(True)
            logging.info(f"Edge deleted: ({node1_uuid}, {node2_uuid})")
        except Exception as e:
            logging.error(f"Error deleting edge: {e}")
            raise

    def create_node_with_default_name(self):
        """Create a new node with a default name."""
        name = "New Node"  # Default node name
        color = "white"  # Default color
        size = 20  # Default size
        node_id = self.create_node(name, color, size)
        logging.info(f"Node added with default name: ID={node_id}, Name={name}, Color={color}, Size={size}")
        return node_id

    def delete_node_by_uuid(self, node_uuid):
        """Delete a node from the graph by UUID."""
        try:
            self.graph.remove_node(node_uuid)
            if (node_uuid in self.node_names):
                del self.node_names[node_uuid]
            self.set_modified(True)
            logging.info(f"Node deleted: {node_uuid}")
        except Exception as e:
            logging.error(f"Error deleting node: {e}")
            raise

    def log_last_file_path(self, file_path):
        """Save the last opened file path to a log file.
        
        Also ensures the file is in the available_databases.log list.
        """
        try:
            # First ensure directory exists
            log_dir = os.path.dirname(self.log_file_path)
            os.makedirs(log_dir, exist_ok=True)
            
            # Add to available databases if not already there
            databases = self.load_available_databases()
            if file_path not in databases:
                databases.append(file_path)
                self.save_available_databases(databases)
            
            # Save as last used database (first in list)
            databases.remove(file_path)
            databases.insert(0, file_path)
            self.save_available_databases(databases)
            
            logging.info(f"Saved last opened file path: {file_path}")
        except Exception as e:
            logging.error(f"Error saving last opened file path: {e}")
    
    def load_available_databases(self):
        """Load the list of available databases from log file."""
        databases = []
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, "r") as log_file:
                    for line in log_file:
                        path = line.strip()
                        if path and os.path.exists(path):
                            databases.append(path)
            return databases
        except Exception as e:
            logging.error(f"Error loading available databases: {e}")
            return databases
    
    def save_available_databases(self, databases):
        """Save the list of available databases to log file."""
        try:
            with open(self.log_file_path, "w") as log_file:
                for path in databases:
                    log_file.write(f"{path}\n")
        except Exception as e:
            logging.error(f"Error saving available databases: {e}")

    def try_loading_last_opened_graph(self):
        """Load the last opened graph from the log file."""
        databases = self.load_available_databases()
        file_path = databases[0] if databases else None
        
        if file_path:
            try:
                self.load_graph(file_path)
                logging.info(f"Loaded graph from last opened file: {file_path}")
                # No return value here
            except Exception as e:
                logging.error(f"Error loading last opened file: {e}")

    def load_last_opened_file_path(self):
        """Load the last opened file path from available databases.
        
        Returns the first entry in the available_databases.log file.
        """
        databases = self.load_available_databases()
        return databases[0] if databases else None

    def get_last_saved_file(self):
        self.last_saved_file = self.load_last_opened_file_path()
        """Get the last saved file path."""
        return self.last_saved_file

    def check_if_modified(self):
        """Check if the graph has been modified."""
        return self.modified

    def set_modified(self, modified):
        """Set the modified state of the graph."""
        self.modified = modified
        logging.info(f"Graph modified state set to: {modified}")

    def create_new_graph(self):
        """Create a new, empty graph and clear file paths."""
        graph = nx.DiGraph()  # Changed from nx.Graph() to nx.DiGraph()
        self.graph = graph
        self.node_names = {}
        self.next_node_id = 1
        self.delete_last_saved_file_log()
        self.set_modified(False)
        return graph

    def set_last_saved_file_log(self, file_path):
        """Set the last saved file path."""
        self.last_saved_file = file_path
        logging.info(f"Last saved file path set to: {file_path}")

    def delete_last_saved_file_log(self):
        """Delete the last saved file path."""
        self.last_saved_file = None
        logging.info("Last saved file path deleted.")

    def get_node_by_uuid(self, node_uuid):
        """Get a node by its UUID."""
        try:
            return self.graph.nodes[node_uuid]
        except KeyError:
            logging.warning(f"Node with UUID {node_uuid} not found.")
            return None

    def get_node_label(self, node):
        """Get the label of a node."""
        return self.graph.nodes[node].get('label', str(node))
    
    def set_graph(self, new_graph):
        """Set the graph with a new NetworkX graph."""
        if not isinstance(new_graph, nx.DiGraph):  # Changed from nx.Graph to nx.DiGraph
            raise ValueError("Input must be a NetworkX directed graph.")
        
        self.graph = new_graph
        self.node_names = {node: data.get('label', str(node)) for node, data in new_graph.nodes(data=True)}
        self.next_node_id = max([int(label) for label in self.node_names.values() if label.isdigit()] + [0]) + 1
        self.set_modified(True)
        logging.info("Graph has been set with a new NetworkX directed graph.")

    def open_file(self, main_window, file_path):
        """Open a graph."""
        try:
            self.load_graph(file_path)
            main_window.show_graph()
            self.set_last_saved_file_log(file_path)
            main_window.update_window_title()  # Update title after opening
            logging.info(f"Graph loaded from {file_path} and plotted.")
        except Exception as e:
            logging.error(f"Error opening graph: {e}")
            raise

    def create_table(self, table_name, columns):
        """Creates a table in the database."""
        try:
            self.graph_file_manager.create_table(table_name, columns)
            logging.info(f"Table created: {table_name}")
        except Exception as e:
            logging.error(f"Error creating table: {e}")
            raise

    def insert_node_data(self, node_id, file_path, file_type, content):
        """Inserts node data into the database."""
        try:
            self.graph_file_manager.insert_node("nodes", node_id, file_path, file_type, content)
            logging.debug(f"Data inserted for node: {node_id}")
        except Exception as e:
            logging.error(f"Error inserting node data: {e}")
            raise

    def read_file_content(self, file_path):
        """Reads the content of a file from the database or filesystem."""
        try:
            # Check if file exists in database
            if hasattr(self.graph_file_manager, 'read_file_content'):
                # Use the graph_file_manager method if available
                content = self.graph_file_manager.read_file_content(file_path)
                if content is not None:
                    logging.info(f"Successfully read file content from database: {file_path}")
                    return content
            
            # Fall back to reading from filesystem
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                logging.info(f"Successfully read file content from filesystem: {file_path}")
                return content
                
            logging.warning(f"File not found in database or filesystem: {file_path}")
            return b''  # Return empty bytes instead of None
        except Exception as e:
            logging.error(f"Error reading file content: {e}")
            return b''  # Return empty bytes on error

    def file_exists(self, file_path):
        """Checks if a file exists in the database."""
        try:
            return self.graph_file_manager.file_exists(file_path)
        except Exception as e:
            logging.error(f"Error checking file existence: {e}")
            raise

    def save_graph_to_database(self):
        """Saves the current graph to the database as a blob."""
        try:
            # Serialize the graph using pickle
            graph_bytes = pickle.dumps(self.graph)

            # Check if a graph already exists in the database
            self.graph_file_manager.db_handler.connect()
            query = "SELECT COUNT(*) FROM graphs"
            cursor = self.graph_file_manager.db_handler.cursor
            cursor.execute(query)
            count = self.graph_file_manager.db_handler.cursor.fetchone()[0]
            self.graph_file_manager.db_handler.close()

            # If a graph exists, update it. Otherwise, insert a new graph.
            if count > 0:
                query = "UPDATE graphs SET graph_data = ?"
            else:
                query = "INSERT INTO graphs (graph_data) VALUES (?)"

            # Execute the appropriate query
            self.graph_file_manager.db_handler.connect()
            cursor = self.graph_file_manager.db_handler.cursor
            cursor.execute(query, (graph_bytes,))
            self.graph_file_manager.db_handler.conn.commit()
            self.graph_file_manager.db_handler.close()

            logging.info("Graph saved to database as blob.")
        except Exception as e:
            logging.error(f"Error saving graph to database: {e}")
            raise

    def load_graph_from_gml(self, file_path):
        """Loads a graph from a GML file."""
        try:
            graph = nx.read_gml(file_path)
            # Convert node labels back to UUIDs
            graph = nx.relabel_nodes(graph, lambda x: uuid.UUID(x))
            self.set_graph(graph)
            logging.info(f"Graph loaded from GML file: {file_path}")
        except Exception as e:
            logging.error(f"Error loading graph from GML file: {e}")
            raise

    def get_graph(self):
        """Returns the current graph."""
        return self.graph

    def read_file_content(self, file_path):
        """Reads the content of a file as binary data."""
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Error reading file content from {file_path}: {e}")
            return None

    def create_file_node(self, file_path, file_type):
        """Creates a node in the graph for a file and stores it in the database."""
        title = os.path.splitext(os.path.basename(file_path))[0]

        # Create the node in the graph
        node_id = self.create_node(name=title, color='green', size=1, file_path=file_path, file_type=file_type)

        # Read file content as binary data
        file_content = self.read_file_content(file_path)

        # Store node info in the database
        try:
            self.graph_file_manager.insert_node("nodes", node_id, file_path, file_type, file_content)
        except Exception as e:
            logging.error(f"Error inserting node data into database: {e}")
            raise e  # Re-raise the exception to stop the import process

        logging.debug(f"Added node: {node_id} for file: {file_path} with type: {file_type}")
        return node_id