import logging
from ResearchGuidePackage.BackendModule.sqlite_handler import SQLiteHandler
import networkx as nx
import pickle
import io
import tempfile
import os
import uuid

logger = logging.getLogger(__name__)

class GraphFileManager:
    def __init__(self):
        """Initializes the GraphFileManager with a database path."""
        logger.debug(f"GraphFileManager initialized")
        self.path = None

    def set_path(self, path):
        """Sets the database path."""
        self.path = path

    def get_path(self):
        """Returns the database path."""
        return self.path
    
    def initialize_database(self):
        """Initializes the database: creates tables if they don't exist."""
        self.db_handler = SQLiteHandler()
        self.db_handler.set_db_path(self.get_path())
        
        # Check if tables exist, create them if not
        if not self.db_handler.table_exists("nodes"):
            self.create_table(
                "nodes",
                ["node_id TEXT PRIMARY KEY", "name TEXT", "color TEXT", "size INTEGER", "label TEXT", "file_path TEXT", "file_type TEXT", "content BLOB"]
            )
        
        if not self.db_handler.table_exists("metadata"):
            self.create_table("metadata", ["graph_data BLOB"])
        
        logger.info(f"Database initialized at: {self.db_handler.db_path}")

    def execute_query(self, query, data=None):
        """Executes a SQL query and handles connection management."""
        try:
            self.db_handler.connect()
            cursor = self.db_handler.cursor
            if data:
                cursor.execute(query, data)
            else:
                cursor.execute(query)
            self.db_handler.conn.commit()
            if query.lower().startswith("select"):
                result = cursor.fetchall()
            else:
                result = None
            return result
        except Exception as e:
            logger.error(f"Error executing query: {query}. Error: {e}")
            raise
        finally:
            self.db_handler.close()

    def create_table(self, table_name, columns):
        """Creates a table in the database."""
        columns_str = ", ".join(columns)
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        self.execute_query(query)
        logger.info(f"Table created: {table_name}")

    def insert_node(self, table_name, node_id, file_path, file_type, content):
        """Inserts node data into the database."""
        data = {
            "node_id": str(node_id),
            "file_path": file_path,
            "file_type": file_type,
            "content": content
        }
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data.values()])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.execute_query(query, tuple(data.values()))
        logger.debug(f"Data inserted into {table_name}: {data}")

    def file_exists(self, file_path):
        """Checks if a file exists in the database."""
        query = "SELECT 1 FROM nodes WHERE file_path = ?"
        result = self.execute_query(query, (file_path,))
        return result is not None and len(result) > 0

    def download_file(self, file_path, destination):
        """Downloads a file from the database."""
        query = "SELECT content FROM nodes WHERE file_path = ?"
        result = self.execute_query(query, (file_path,))
        if result:
            with open(destination, 'wb') as file:
                file.write(result[0][0])  # Assuming content is the first element in the row
            logger.info(f"File downloaded to: {destination}")
        else:
            logger.warning(f"File not found in database: {file_path}")

    def upload_graph_to_database(self, graph):
        """Uploads the graph to the database using pickle."""
        # Serialize the graph using pickle
        pickled_graph = pickle.dumps(graph)

        # Check if a graph already exists in the database
        query = "SELECT COUNT(*) FROM metadata"
        result = self.execute_query(query)
        count = result[0][0] if result else 0

        if count > 0:
            query = "UPDATE metadata SET graph_data = ?"
        else:
            query = "INSERT INTO metadata (graph_data) VALUES (?)"

        self.execute_query(query, (pickled_graph,))
        logger.info("Graph saved to database using pickle.")

    def download_graph_from_database(self):
        """Downloads the graph from the database and returns it as a networkx graph."""
        query = "SELECT graph_data FROM metadata"
        result = self.execute_query(query)
        if result:
            pickled_graph = result[0][0]
            # Deserialize the graph using pickle
            graph = pickle.loads(pickled_graph)
            logger.info("Graph loaded from database using pickle.")
            print(graph)
            return graph
        else:
            logger.info("No graph data found in the database.")
            return None

    def delete_node_data(self, table_name, node_id):
        """Deletes node data from the database."""
        condition = f"node_id = ?"
        query = f"DELETE FROM {table_name} WHERE {condition}"
        self.execute_query(query, (node_id,))
        logger.debug(f"Data deleted from {table_name} with node_id: {node_id}")