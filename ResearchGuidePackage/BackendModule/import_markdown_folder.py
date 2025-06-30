import os
import networkx as nx
import re
import uuid
import logging
from datetime import datetime
import ResearchGuidePackage.BackendModule.graph_manager
#Diese Funktion ist dafür da, um Markdown Ordner-Strukturen, die mit Obsidian erstellt wurden, zu importieren und in ein Netzwerkx-Graphenobjekt umzuwandeln.

logger = logging.getLogger(__name__)  # Get a logger instance

def extract_title_from_markdown(file_path):
    """Extract the title from a Markdown file (first heading)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#'):
                    return line.lstrip('# ').strip()
        return os.path.splitext(os.path.basename(file_path))[0]  # Default to filename if no heading
    except Exception as e:
        logger.error(f"Error extracting title from {file_path}: {e}")
        return os.path.splitext(os.path.basename(file_path))[0]

def parse_obsidian_links(file_path):
    """Parse Obsidian-style links from a Markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            return links
    except Exception as e:
        logger.error(f"Error parsing links from {file_path}: {e}")
        return []

def normalize_obsidian_link(folder_path, link):
    """Normalize Obsidian link to a relative file path."""
    # Construct the absolute path first
    absolute_path = os.path.join(folder_path, link + ".md")
    # Then, make it relative to the folder path
    relative_path = os.path.relpath(absolute_path, folder_path)
    return relative_path

def extract_text_blocks(file_path):
    """Extract text blocks from a markdown file."""
    blocks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split content into lines
        lines = content.split('\n')
        current_block = None
        level = 0
        
        for line in lines:
            line = line.rstrip()
            
            # Skip empty lines
            if not line:
                if current_block:
                    blocks.append(current_block)
                    current_block = None
                continue
            
            # Check for headings
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                if current_block:
                    blocks.append(current_block)
                
                heading_level = len(heading_match.group(1))
                current_block = {
                    "content": heading_match.group(2).strip(),
                    "type": "Heading",
                    "level": heading_level - 1  # Convert h1-h6 to level 0-5
                }
                blocks.append(current_block)
                current_block = None
                continue
            
            # Check for bullet points
            bullet_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', line)
            if bullet_match:
                if current_block:
                    blocks.append(current_block)
                
                indent = len(bullet_match.group(1))
                bullet_level = indent // 2  # Estimate level based on indentation
                current_block = {
                    "content": bullet_match.group(3).strip(),
                    "type": "Bullet",
                    "level": bullet_level
                }
                blocks.append(current_block)
                current_block = None
                continue
            
            # Handle regular paragraph text
            if not current_block:
                current_block = {
                    "content": line,
                    "type": "Paragraph",
                    "level": 0
                }
            else:
                # Append to existing paragraph
                current_block["content"] += " " + line
        
        # Add the last block if there is one
        if current_block:
            blocks.append(current_block)
            
    except Exception as e:
        logger.error(f"Error extracting text blocks from {file_path}: {e}")
    
    return blocks

def path_to_namespace(path, root_folder, additional_part=None):
    """Convert a file path to namespace notation with proper quoting for ALL elements."""
    try:
        # For files, use their directory path instead of the file itself
        if os.path.isfile(path):
            path = os.path.dirname(path)
            
        # If path is empty after converting to directory, return None or just additional_part
        if not path or path == root_folder:
            if additional_part:
                return quote_name_if_needed(additional_part)
            return None
            
        # Get relative path from root folder
        rel_path = os.path.relpath(path, root_folder)
        
        # If the path is the same as the root folder, return None or just additional_part
        if rel_path == '.' or rel_path == './':
            if additional_part:
                return quote_name_if_needed(additional_part)
            return None
            
        # Normalize path separators to forward slashes
        norm_path = os.path.normpath(rel_path).replace('\\', '/')
        
        # Split path by separators and filter out empty parts
        parts = [p for p in norm_path.split('/') if p]
        
        # Process each part - replace commas and quote parts that contain spaces or dots
        quoted_parts = []
        for part in parts:
            # First replace commas with underscores to avoid namespace parsing issues
            part = part.replace(',', '_')
            # Add to quoted_parts with proper quoting
            quoted_parts.append(quote_name_if_needed(part))
        
        # Add additional part if provided
        if additional_part:
            quoted_parts.append(quote_name_if_needed(additional_part))
            
        # Join parts with dots to create namespace
        if quoted_parts:
            return '.'.join(quoted_parts)
        return None
    except Exception as e:
        logger.error(f"Error converting path to namespace: {e}")
        return None

def create_folder_node_if_not_exists(graph_manager, folder_path, root_folder):
    # Get the parent directory path instead of the folder itself
    parent_directory = os.path.dirname(folder_path)
    folder_namespace = path_to_namespace(parent_directory, root_folder)
    
    # Check if folder node already exists with this namespace
    for n in list(graph_manager.get_graph().nodes()):
        d = graph_manager.get_node_by_uuid(n)
        if d and d.get("namespaces") == folder_namespace and d.get("node_type") == "page":
            logger.debug(f"Folder node already exists: {n} for namespace: {folder_namespace}")
            return n
    
    # Create folder node if it doesn't exist - use proper node type and styling
    folder_name = os.path.basename(folder_path)
    folder_node_id = graph_manager.create_node(
        name=folder_name,  # Quote if needed
        color='#4BA3C3',  # Page/folder color from newer implementation
        size=35,          # Larger size for folders/pages
        node_type="page",  # Folders use page node type
        title=folder_name, # Title parameter for page
        tags="folder",     # Tags parameter for page
        namespaces=folder_namespace  # Store namespace instead of file_path
    )
    logger.info(f"Added folder node: {folder_node_id} for namespace: {folder_namespace}")
    return folder_node_id

def create_text_block_nodes(graph_manager, page_node_id, file_path, file_namespace):
    """Creates text block nodes from a markdown file and links them to the parent page node."""
    try:
        # Extract blocks from the markdown file
        blocks = extract_text_blocks(file_path)
        logger.debug(f"Found {len(blocks)} text blocks in {file_path}")
        
        # Get the parent page node information
        graph = graph_manager.get_graph()
        page_node_data = graph.nodes[page_node_id]
        page_title = page_node_data.get('title') or page_node_data.get('name', '')
        
        # Create text block namespace as a CHILD of the parent page's namespace
        text_block_namespace = None

        if file_namespace:
            # Create child namespace by appending the page_title to the existing namespace
            quoted_title = quote_name_if_needed(page_title)
            text_block_namespace = f"{file_namespace}.{quoted_title}"
        elif page_title:
            # If no parent namespace, just use the page title
            text_block_namespace = quote_name_if_needed(page_title)
        
        logger.info(f"Setting text blocks namespace to: {text_block_namespace} (child of page)")
        
        # Create nodes for each text block
        for position, block in enumerate(blocks):
            block_content = block.get("content", "")
            block_type = block.get("type", "Paragraph")
            block_level = block.get("level", 0)
            
            # Create a short name for better identification
            # Special handling for headings with same name as page
            if block_type == "Heading" and block_content.strip() == page_title.strip():
                # Prepend "Heading: " to differentiate from page name
                short_name = f"Heading: {block_content}"
                logger.info(f"Renamed heading that matches page title: '{block_content}'")
            else:
                # Regular naming for other blocks
                short_name = block_content[:20] + "..." if len(block_content) > 20 else block_content
            
            # Create a text block node with CHILD namespace
            block_node_id = graph_manager.create_node(
                name=short_name,  # Use modified name for headings that match page title
                color='#95D9C3',  # Text block color
                size=20,          # Smaller size for text blocks
                node_type="text_block",  # Explicitly set node type
                content=block_content,   # Content parameter
                level=block_level,       # Level parameter 
                type=block_type,         # Type parameter
                namespaces=text_block_namespace  # Use child namespace
            )
            
            # Connect to parent page with position information
            graph_manager.add_edge(page_node_id, block_node_id, position, "contains")
            logger.debug(f"Created text block node {block_node_id} of type {block_type}")
        
        return len(blocks)
    except Exception as e:
        logger.error(f"Error creating text block nodes for {file_path}: {e}")
        return 0

def create_nodes_and_edges(graph_manager, folder_path):
    """Creates edges connecting file nodes to their parent folder nodes using graph_manager."""
    try:
        # Verify folder exists
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            error_msg = f"Folder path does not exist or is not a directory: {folder_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Traverse the folder structure and create nodes for each folder
        for root, dirs, files in os.walk(folder_path):
            logger.info(f"Processing folder: {root}")
            
            # Skip creating a node for the root folder itself
            if root == folder_path:
                parent_folder_node_id = None
                logger.info("Skipping node creation for root folder")
            else:
                parent_folder_node_id = create_folder_node_if_not_exists(graph_manager, root, folder_path)

            # Create nodes for files
            for name in files:
                try:
                    file_path = os.path.join(root, name)
                    # Store relative file paths instead of absolute paths
                    rel_file_path = os.path.relpath(file_path, folder_path)
                    file_ext = os.path.splitext(name)[1]
                    
                    if file_ext.lower() == ".md":
                        # For .md files, explicitly determine the namespace of their containing directory.
                        md_containing_directory = os.path.dirname(file_path)
                        page_container_namespace = path_to_namespace(md_containing_directory, folder_path)
                        
                        title = extract_title_from_markdown(file_path)
                        
                        # Page node gets the namespace of its containing directory.
                        page_node_id = graph_manager.create_node(
                            name=title,
                            color='#4BA3C3',
                            size=35,
                            node_type="page",
                            title=title,
                            tags="markdown",
                            namespaces=page_container_namespace 
                        )
                        
                        # Calculate the text block namespace
                        quoted_title = quote_name_if_needed(title)
                        file_child_namespace = f"{page_container_namespace}.{quoted_title}" if page_container_namespace else quoted_title

                        # PROPERLY CREATE FILE NODE WITH CONTENT
                        # Read file content
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        
                        file_name_only = os.path.basename(file_path)
                        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d')

                        # Create file node
                        file_node_id = graph_manager.create_node(
                            name=file_name_only,
                            color='#CE8147',
                            size=25,
                            node_type='file',
                            file_path=rel_file_path,  # Use RELATIVE path
                            file_type=file_ext,
                            last_modified=mod_time,
                            namespaces=file_child_namespace
                        )

                        # INSERT FILE CONTENT INTO DATABASE
                        graph_manager.insert_node_data(
                            str(file_node_id),  # Convert UUID to string
                            rel_file_path,  # Use RELATIVE path
                            file_ext,
                            file_content
                        )

                        # Keep the has_source relationship
                        graph_manager.add_edge(page_node_id, file_node_id, 1, "has_source")
                        
                        # The folder contains the page
                        if parent_folder_node_id is not None:
                            graph_manager.add_edge(parent_folder_node_id, page_node_id, 1, "contains")
                        
                        block_count = create_text_block_nodes(graph_manager, page_node_id, file_path, page_container_namespace)
                        logger.info(f"Created {block_count} text block nodes for {file_path} under page {page_node_id}")
                    else:
                        # For non-markdown files, also upload content to database
                        item_dir = os.path.dirname(file_path)
                        item_namespace = path_to_namespace(item_dir, folder_path)
                        
                        # Read file content
                        try:
                            with open(file_path, 'rb') as f:
                                file_content = f.read()
                                
                            file_name_only = os.path.basename(file_path)
                            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d')
                            
                            # USE CREATE_FILE_NODE DIRECTLY IF THE FILE HAS CONTENT
                            # This properly creates the node and stores content in DB
                            other_file_node_id = graph_manager.create_node(
                                name=file_name_only,
                                color='#CE8147',
                                size=25,
                                node_type='file',
                                file_path=rel_file_path,  # Use RELATIVE path
                                file_type=file_ext,
                                last_modified=mod_time,
                                namespaces=item_namespace 
                            )
                            
                            # INSERT FILE CONTENT INTO DATABASE
                            graph_manager.insert_node_data(
                                str(other_file_node_id),  # Convert UUID to string
                                rel_file_path,  # Use RELATIVE path
                                file_ext,
                                file_content
                            )
                            
                            if parent_folder_node_id is not None:
                                graph_manager.add_edge(parent_folder_node_id, other_file_node_id, 1, "contains")
                            logger.info(f"Added file node with content: {other_file_node_id} for {file_path}")
                        except Exception as e:
                            logger.error(f"Error reading file {file_path}: {e}")
                            # Continue with next file if one fails
                            continue
                        
                except Exception as e:
                    logger.error(f"Error processing file {name}: {e}")
                    continue

            # Create edges for subfolders
            for name in dirs:
                try:
                    subfolder_path = os.path.join(root, name)
                    subfolder_node_id = create_folder_node_if_not_exists(graph_manager, subfolder_path, folder_path)
                    if parent_folder_node_id is not None and not graph_manager.get_graph().has_edge(parent_folder_node_id, subfolder_node_id):
                        graph_manager.add_edge(parent_folder_node_id, subfolder_node_id, 1, "contains")
                        logger.info(f"Added edge from folder node: {parent_folder_node_id} to subfolder node: {subfolder_node_id}")
                except Exception as e:
                    logger.error(f"Error processing subfolder {name}: {e}")
                    continue

        logger.info("Added folder nodes and edges to the graph.")
        
    except Exception as e:
        logger.error(f"Error creating nodes and edges: {e}")
        raise

def create_edges_from_links(graph_manager, folder_path):
    """Create edges in the graph based on Obsidian links in Markdown files."""
    try:
        graph = graph_manager.get_graph()
        
        # Use a temporary mapping between file paths and node IDs for processing links
        # This won't be stored in the graph, just used temporarily
        temp_path_to_node = {}
        
        # Build a mapping of namespaces to nodes
        namespace_to_nodes = {}
        
        # Collect all nodes with namespaces attributes
        for node_id, data in graph.nodes(data=True):
            namespace = data.get("namespaces")
            if namespace:
                if namespace not in namespace_to_nodes:
                    namespace_to_nodes[namespace] = []
                namespace_to_nodes[namespace].append(node_id)
        
        # Process each markdown file in the folder structure to find links
        for root, _, files in os.walk(folder_path):
            for name in files:
                if name.lower().endswith('.md'):
                    file_path = os.path.join(root, name)
                    # Use the DIRECTORY of the file instead of the file itself
                    file_dir = os.path.dirname(file_path)
                    file_namespace = path_to_namespace(file_dir, folder_path)
                    
                    # Find nodes with matching namespace
                    matching_nodes = namespace_to_nodes.get(file_namespace, [])
                    if not matching_nodes:
                        continue
                    
                    # Find the page node among matching nodes
                    page_node_id = None
                    for node_id in matching_nodes:
                        if graph.nodes[node_id].get('node_type') == 'page':
                            page_node_id = node_id
                            break
                    
                    if page_node_id:
                        # Extract links from this markdown file
                        links = parse_obsidian_links(file_path)
                        logger.debug(f"Links found in {file_path}: {links}")
                        
                        # Process each link
                        for link in links:
                            # Find target nodes by name
                            target_nodes = []
                            for n, d in graph.nodes(data=True):
                                node_name = d.get("name") or d.get("title")
                                if node_name == link:
                                    target_nodes.append(n)
                                    logger.debug(f"Found target node by name: {n} with name: {node_name}")
                            
                            # Create edges to all target nodes
                            for target_node_id in target_nodes:
                                if not graph.has_edge(page_node_id, target_node_id):
                                    graph_manager.add_edge(page_node_id, target_node_id, 1, "link")
                                    logger.debug(f"Added edge from {page_node_id} to {target_node_id} based on link {link}")
                            
                            if not target_nodes:
                                logger.warning(f"Target node not found for link: {link} in file: {file_path}")
        
        logger.info("Added edges based on links in Markdown files.")
    except Exception as e:
        logger.error(f"Error creating edges from links: {e}")
        # Continue despite errors in link processing

def import_markdown_folder_structure(folder_path, db_file_path):
    """Import folder structure and convert it to a networkx graph."""
    try:
        # Log the paths for debugging
        logger.info(f"Importing markdown folder: {folder_path} to database: {db_file_path}")
        
        # Validate parameters
        if not folder_path or not os.path.exists(folder_path):
            error_msg = f"Invalid folder path: {folder_path}"
            logger.error(error_msg)
            return False, {}, error_msg
            
        if not db_file_path:
            error_msg = "Database file path not specified"
            logger.error(error_msg)
            return False, {}, error_msg
            
        # Create directories for db file if they don't exist
        db_dir = os.path.dirname(os.path.abspath(db_file_path))
        os.makedirs(db_dir, exist_ok=True)
        
        # Initialize GraphManager
        graph_manager = ResearchGuidePackage.BackendModule.graph_manager.GraphManager()
        graph_manager.load_graph(db_file_path)

        # Process nodes and edges
        create_nodes_and_edges(graph_manager, folder_path)
        create_edges_from_links(graph_manager, folder_path)
        
        # Save the graph
        graph_manager.save_graph(db_file_path)
        
        node_count = len(graph_manager.get_graph().nodes())
        edge_count = len(graph_manager.get_graph().edges())
        logger.info(f"Imported Graph with {node_count} nodes and {edge_count} edges.")
        
        return True, {
            "result": True, 
            "database_path": db_file_path, 
            "node_count": node_count, 
            "edge_count": edge_count
        }, None
    except Exception as e:
        error_msg = f"Error during import process: {e}"
        logger.error(error_msg)
        return False, {}, error_msg

def quote_name_if_needed(name):
    """Add quotes to a name if it contains spaces or dots, and replace commas with underscores."""
    # First replace commas with underscores to avoid namespace parsing issues
    name = name.replace(',', '_')
    name = name.replace('.', '_')
    
    # Check if already quoted (starts and ends with single quote)
    already_quoted = False
    if name and len(name) >= 2 and name[0] == "'" and name[-1] == "'":
        already_quoted = True
    
    # Then apply quoting if needed and not already quoted
    if ' ' in name and not already_quoted:
        return f"'{name}'"
    return name
