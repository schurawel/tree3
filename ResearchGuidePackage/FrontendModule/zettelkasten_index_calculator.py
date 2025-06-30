"""
Zettelkasten Index Calculator
============================
Calculates Luhmann-style indices for nodes in a NetworkX graph using
an optimization approach that finds the best hierarchical structure.
"""
import networkx as nx
import logging
from typing import Dict, Set, List, Tuple, Any
import heapq
import random  # Add import for randomness

logger = logging.getLogger('ZettelkastenIndexCalculator')

class ZettelkastenIndexCalculator:
    """
    Calculates Luhmann-style indices for nodes in a graph by finding
    an optimal hierarchical structure.
    """
    
    def __init__(self, randomness_factor=0.3):
        """
        Initialize the calculator with configurable randomness.
        
        Args:
            randomness_factor: Float between 0.0 (completely deterministic) and 
                            1.0 (high randomness) that determines how much random
                            variation to add to parent-child relationships
        """
        self.randomness_factor = max(0.0, min(1.0, randomness_factor))  # Clamp between 0 and 1
    
    def calculate_indices(self, graph):
        """
        Calculate Luhmann-style indices for all nodes in the graph.
        
        Args:
            graph: NetworkX graph
            
        Returns:
            dict: Dictionary mapping node IDs to their index data
        """
        if not graph or not graph.nodes:
            return {}
        
        # Step 1: Calculate node scores to determine importance
        node_scores = self._calculate_node_scores(graph)
        
        # Step 2: Find optimal tree structure
        hierarchy = self._build_optimal_hierarchy(graph, node_scores)
        
        # Step 3: Assign Luhmann indices based on the hierarchy
        indices = self._assign_indices(hierarchy, graph)
        
        return indices
    
    def _calculate_node_scores(self, graph) -> Dict:
        """
        Calculate scores for each node to determine its importance in the hierarchy.
        Higher score means the node is more likely to be near the top of the hierarchy.
        
        This combines multiple factors:
        - Centrality measures
        - Node type importance
        - Explicit 'root' attribute
        - Connection count
        """
        scores = {}
        
        # Calculate various node metrics
        if len(graph) > 0:  # Only if graph has nodes
            # Degree centrality - nodes with more connections are important
            degree_cent = nx.degree_centrality(graph)
            
            # Betweenness centrality - nodes that bridge communities are important
            # Use a try-except block to handle missing modules/functions
            btw_cent = {}
            try:
                if len(graph) > 1000:
                    # For large graphs, calculate betweenness centrality with sampling
                    # k=100 means use 100 random nodes as sources for shortest paths
                    btw_cent = nx.betweenness_centrality(graph, k=100, normalized=True)
                else:
                    # For smaller graphs, calculate exact betweenness centrality
                    btw_cent = nx.betweenness_centrality(graph)
            except Exception as e:
                logger.warning(f"Could not calculate betweenness centrality: {e}. Using degree only.")
                # Set all nodes to 0.0 for betweenness if calculation fails
                btw_cent = {node: 0.0 for node in graph.nodes}
        else:
            degree_cent = {}
            btw_cent = {}
        
        # Combine metrics with node attributes
        for node in graph.nodes:
            node_data = graph.nodes[node]
            base_score = 0.0
            
            # Start with centrality measures (normalized between 0-1)
            base_score += degree_cent.get(node, 0) * 0.7  # 70% weight to degree centrality (increased weight)
            base_score += btw_cent.get(node, 0) * 0.2     # 20% weight to betweenness (reduced weight)
            
            # Add bonus for explicit root nodes
            if node_data.get('root', False):
                base_score += 1.0  # Strong boost for explicitly marked roots
            
            # Add bonus for node types (e.g., concepts are more important than documents)
            node_type = node_data.get('node_type', 'document')
            type_bonus = {
                'concept': 0.3,
                'heading': 0.2,
                'document': 0.1
            }.get(node_type, 0.1)
            base_score += type_bonus
            
            # Check for creation date - older nodes might be more foundational
            if 'creation_date' in node_data:
                try:
                    # This is a simplistic approach - could be refined based on actual date formatting
                    date_str = str(node_data['creation_date'])
                    if date_str:  # Simple check for non-empty date
                        base_score += 0.05  # Small bonus for nodes with dates (likely more established)
                except:
                    pass
                    
            # Store the final score
            scores[node] = base_score
            
        return scores
    
    def _build_optimal_hierarchy(self, graph, node_scores) -> Dict:
        """
        Build an optimal hierarchical structure based on node scores and graph topology.
        Includes randomness to create more diverse hierarchies.
        
        Returns a dictionary mapping each node to its parent in the hierarchy.
        Root nodes map to None.
        """
        # Start with all nodes disconnected
        hierarchy = {node: None for node in graph.nodes}
        
        # Sort nodes by score (highest first)
        sorted_nodes = sorted(node_scores.keys(), key=lambda n: node_scores[n], reverse=True)
        
        # Determine how many root nodes to use, with some randomness
        base_max_roots = min(5, max(1, len(sorted_nodes) // 10))  # Base calculation: max 5 roots or 10% of nodes
        max_roots = base_max_roots
        if self.randomness_factor > 0:
            # Add some random variation to the number of roots
            variation = int(base_max_roots * self.randomness_factor)
            if variation > 0:
                max_roots = random.randint(max(1, base_max_roots - variation), 
                                         base_max_roots + variation)
        
        # Take the top scoring nodes as roots
        roots = sorted_nodes[:max_roots]
        
        # Create a set of assigned nodes (initially just the roots)
        assigned = set(roots)
        
        # Create a priority queue of (score, node, parent) tuples
        # Higher score = higher priority
        queue = []
        
        # Add all potential parent-child relationships to the queue with randomness
        for root in roots:
            for neighbor in graph.neighbors(root):
                if neighbor not in assigned:
                    # Calculate connection strength
                    edge_data = graph.get_edge_data(root, neighbor)
                    edge_weight = edge_data.get('weight', 1.0) if edge_data else 1.0
                    
                    # Check edge type - prioritize explicit parent-child relationships
                    edge_type = edge_data.get('edge_type', '') if edge_data else ''
                    type_bonus = 10.0 if edge_type in ['child', 'parent'] else 0.0
                    
                    # Base score is parent's score plus edge weight and type bonus
                    base_score = node_scores[root] + edge_weight + type_bonus
                    
                    # Add randomness factor
                    if self.randomness_factor > 0:
                        # The maximum jitter is proportional to the base_score and randomness_factor
                        max_jitter = base_score * self.randomness_factor
                        random_jitter = random.uniform(-max_jitter, max_jitter)
                        connection_score = base_score + random_jitter
                    else:
                        connection_score = base_score
                    
                    heapq.heappush(queue, (-connection_score, neighbor, root))  # Negative for max-heap
        
        # Process the queue until all nodes are assigned
        while queue and len(assigned) < len(graph.nodes):
            neg_score, node, parent = heapq.heappop(queue)
            
            # Skip if the node is already assigned
            if node in assigned:
                continue
                
            # Assign this node to its parent
            hierarchy[node] = parent
            assigned.add(node)
            
            # Add all unassigned neighbors of this node to the queue with randomness
            for neighbor in graph.neighbors(node):
                if neighbor not in assigned:
                    edge_data = graph.get_edge_data(node, neighbor)
                    edge_weight = edge_data.get('weight', 1.0) if edge_data else 1.0
                    
                    # Check edge type - prioritize explicit parent-child relationships
                    edge_type = edge_data.get('edge_type', '') if edge_data else ''
                    type_bonus = 10.0 if edge_type in ['child', 'parent'] else 0.0
                    
                    # Base score
                    base_score = node_scores[node] + edge_weight + type_bonus
                    
                    # Add randomness factor
                    if self.randomness_factor > 0:
                        max_jitter = base_score * self.randomness_factor
                        random_jitter = random.uniform(-max_jitter, max_jitter)
                        connection_score = base_score + random_jitter
                    else:
                        connection_score = base_score
                    
                    heapq.heappush(queue, (-connection_score, neighbor, node))
                    
        # Handle orphaned nodes with randomness in assignment
        orphaned = [node for node in graph.nodes if node not in assigned]
        if orphaned and self.randomness_factor > 0:
            # With some probability based on randomness_factor, assign to random parents
            # rather than making them all roots
            for node in orphaned:
                if random.random() < self.randomness_factor and assigned:
                    # Assign to a random existing node as parent
                    possible_parents = list(assigned)
                    # Avoid creating cycles - don't assign to descendants
                    safe_parents = [p for p in possible_parents if p not in self._get_descendants(node, graph)]
                    if safe_parents:
                        random_parent = random.choice(safe_parents)
                        hierarchy[node] = random_parent
                    else:
                        hierarchy[node] = None  # No safe parent found, make it a root
                else:
                    hierarchy[node] = None  # Make it a root node
                assigned.add(node)
        else:
            # Traditional handling without randomness
            for node in orphaned:
                hierarchy[node] = None  # No parent = root node
                assigned.add(node)
                
        # Verify no cycles exist in the hierarchy and fix any issues
        self._verify_no_cycles(hierarchy)
        
        return hierarchy
        
    def _get_descendants(self, node, graph):
        """
        Helper method to get all descendants of a node in the graph.
        Used to prevent cycles when randomly assigning parents.
        """
        descendants = set()
        to_process = [node]
        
        while to_process:
            current = to_process.pop(0)
            for child in graph.successors(current):
                if child not in descendants:
                    descendants.add(child)
                    to_process.append(child)
                    
        return descendants

    def _verify_no_cycles(self, hierarchy):
        """
        Verify there are no cycles in the hierarchy and fix any that are found.
        """
        for node, parent in hierarchy.items():
            # Check for cycles in the parent chain
            visited = set()
            current = parent
            
            while current is not None:
                if current in visited:
                    # Found a cycle - break it by making the current node a root
                    hierarchy[current] = None
                    break
                
                visited.add(current)
                current = hierarchy.get(current)
    
    def _assign_indices(self, hierarchy, graph) -> Dict:
        """
        Assign Luhmann indices based on the hierarchy.
        
        Args:
            hierarchy: Dictionary mapping each node to its parent
            graph: Original NetworkX graph for node attributes
            
        Returns:
            Dictionary mapping node IDs to their index data
        """
        # Find root nodes (nodes with no parent)
        roots = [node for node, parent in hierarchy.items() if parent is None]
        
        # Sort roots by their original name or other attributes
        roots.sort(key=lambda n: (
            graph.nodes[n].get('name', ''),
            graph.nodes[n].get('creation_date', '')
        ))
        
        result = {}
        
        # Create node_to_children mapping for efficient child lookup
        node_to_children = {}
        for node, parent in hierarchy.items():
            if parent not in node_to_children:
                node_to_children[parent] = []
            if parent is not None:  # Only add actual parent-child relationships
                node_to_children[parent].append(node)
        
        # Sort children for each parent based on node attributes
        for parent, children in node_to_children.items():
            if parent is not None:  # Skip None parent (collection of roots)
                # Look for explicit edge order attributes first
                ordered_children = []
                unordered_children = []
                
                for child in children:
                    # Get edge data between parent and child
                    edge_data = graph.get_edge_data(parent, child)
                    if edge_data and 'order' in edge_data:
                        # We have an explicit order
                        order = float(edge_data['order'])
                        ordered_children.append((order, child))
                    else:
                        unordered_children.append(child)
                
                # Sort the explicitly ordered children
                ordered_children.sort()  # Sort by the order attribute
                
                # Sort the remaining children by name/date
                unordered_children.sort(key=lambda n: (
                    graph.nodes[n].get('name', ''),
                    graph.nodes[n].get('creation_date', '')
                ))
                
                # Replace the children list with the properly ordered one
                node_to_children[parent] = [child for _, child in ordered_children] + unordered_children
        
        # Process roots and then do breadth-first traversal for each root's subtree
        for i, root in enumerate(roots):
            root_index = str(i + 1)  # 1-based indexing for roots
            
            # Store root's data
            result[root] = {
                'index': root_index,
                'is_root': True,
                'children': node_to_children.get(root, []),
                'level': 0
            }
            
            # Process all descendants with depth-first to ensure proper parent-child ordering
            stack = [(root, root_index)]
            visited = set([root])
            
            while stack:
                parent, parent_index = stack.pop()  # Depth-first
                children = node_to_children.get(parent, [])
                
                # For each child in this parent's children
                for j, child in enumerate(children):
                    if child in visited:  # Skip if already visited (handle potential cycles)
                        continue
                        
                    # Calculate Luhmann index
                    child_index = f"{parent_index}.{j + 1}"
                    level = parent_index.count('.') + 1
                    
                    # Add child to result
                    result[child] = {
                        'index': child_index,
                        'is_root': False,
                        'children': node_to_children.get(child, []),
                        'level': level
                    }
                    
                    # Mark as visited and add to stack for processing its children
                    visited.add(child)
                    stack.append((child, child_index))  # Add to start for depth-first
        
        return result
